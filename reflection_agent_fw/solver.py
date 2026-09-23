"""Core solver engine executing stage-gated reflection for a single RTL problem."""

import logging
import time
from typing import List, Optional

from reflection_agent_fw.code_extractor import VerilogCodeExtractor
from reflection_agent_fw.instrumentation import PipelineStageTracer
from reflection_agent_fw.llm_client import OpenAICompatibleClient
from reflection_agent_fw.problem import RTLProblem
from reflection_agent_fw.prompt_builder import ReflectionPromptBuilder
from reflection_agent_fw.result import SolveResult, SolveStep
from reflection_agent_fw.tools import RTLToolEnvironment

logger = logging.getLogger(__name__)


class ReflectionAgentSolver:
    """Stage-gated reflection solver for individual Verilog RTL generation problems."""

    def __init__(
        self,
        llm_client: OpenAICompatibleClient,
        tool_env: Optional[RTLToolEnvironment] = None,
    ) -> None:
        """Initialize solver with LLM client and EDA tool environment."""
        self.llm_client = llm_client
        self.tools = tool_env or RTLToolEnvironment()

    def solve(self, problem: RTLProblem) -> SolveResult:
        """Solve a single RTL problem using bounded stage-gated reflection with instrumentation.

        Stages instrumented in each round:
        1. prompt_prep: Assembles specification or reflection context.
        2. rtl_generation: LLM code generation and RTL extraction.
        3. static_lint: Verilator static lint verification.
        4. behavioral_sim: Iverilog event-driven functional verification.
        5. reflection_decision: Evaluates pass/fail condition and next stage transition.
        """
        tracer = PipelineStageTracer(problem_name=problem.name)
        steps: List[SolveStep] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        start_time = time.time()

        max_rounds = max(1, problem.max_reflection_rounds)
        current_code = ""
        last_lint_ok = False
        last_lint_output = ""
        last_sim_ok = False
        last_sim_output = ""
        last_timed_out = False

        for step_idx in range(max_rounds):
            step_start = time.time()

            # Stage 1: Prompt Preparation
            p_prep_start = time.time()
            if step_idx == 0:
                level_name = "L0_ZERO_SHOT"
                messages = ReflectionPromptBuilder.build_l0_messages(
                    prompt=problem.prompt,
                    module_name=problem.module_name,
                )
            elif step_idx == 1 and not last_lint_ok:
                level_name = "L1_LINT"
                messages = ReflectionPromptBuilder.build_l1_lint_messages(
                    module_name=problem.module_name,
                    previous_code=current_code,
                    lint_output=last_lint_output,
                )
            elif (step_idx == 1 or step_idx == 2) and last_lint_ok and not last_sim_ok:
                level_name = "L2_SIM"
                messages = ReflectionPromptBuilder.build_l2_sim_messages(
                    module_name=problem.module_name,
                    previous_code=current_code,
                    sim_output=last_sim_output,
                    testbench_code=problem.testbench_code,
                )
            else:
                level_name = f"L{step_idx}_MULTI_TURN"
                err_type = "lint" if not last_lint_ok else "simulation"
                diag = last_lint_output if not last_lint_ok else last_sim_output
                messages = ReflectionPromptBuilder.build_iterative_repair_messages(
                    module_name=problem.module_name,
                    round_idx=step_idx + 1,
                    previous_code=current_code,
                    error_type=err_type,
                    diagnostics=diag,
                    testbench_code=problem.testbench_code if err_type == "simulation" else None,
                )

            p_prep_duration = time.time() - p_prep_start
            tracer.record_stage(
                stage_id="prompt_prep",
                stage_name="Prompt Assembly",
                step_index=step_idx,
                level=level_name,
                status="SUCCESS",
                duration_sec=p_prep_duration,
                inputs={"level": level_name, "step_index": step_idx},
                outputs={"prompt_chars": len(messages[-1]["content"])},
            )

            # Stage 2: RTL Generation & Extraction
            logger.info("Executing %s for %s (round %d/%d)...", level_name, problem.name, step_idx + 1, max_rounds)
            gen_start = time.time()
            completion, p_tokens, c_tokens = self.llm_client.complete(
                messages=messages,
                temperature=problem.temperature,
            )
            total_prompt_tokens += p_tokens
            total_completion_tokens += c_tokens

            extracted_code = VerilogCodeExtractor.extract(
                raw_text=completion,
                expected_module=problem.module_name,
            )
            current_code = extracted_code
            gen_duration = time.time() - gen_start

            tracer.record_stage(
                stage_id="rtl_generation",
                stage_name="RTL Code Generation",
                step_index=step_idx,
                level=level_name,
                status="SUCCESS" if bool(extracted_code) else "FAILURE",
                duration_sec=gen_duration,
                inputs={"model": getattr(self.llm_client, "model", "default"), "temperature": problem.temperature},
                outputs={"extracted_code": extracted_code, "completion": completion},
                metrics={"prompt_tokens": p_tokens, "completion_tokens": c_tokens},
            )
            logger.info("[PIPELINE] RTL Generation completed in %.2fs (%d prompt, %d comp tokens)", gen_duration, p_tokens, c_tokens)

            # Stage 3: Static Linting (Verilator)
            lint_start = time.time()
            lint_ok, lint_output = self.tools.lint(
                code=extracted_code,
                module_name=problem.module_name,
            )
            lint_duration = time.time() - lint_start
            last_lint_ok = lint_ok
            last_lint_output = lint_output

            tracer.record_stage(
                stage_id="static_lint",
                stage_name="Verilator Static Lint",
                step_index=step_idx,
                level=level_name,
                status="SUCCESS" if lint_ok else "FAILURE",
                duration_sec=lint_duration,
                inputs={"module_name": problem.module_name, "code_bytes": len(extracted_code.encode("utf-8"))},
                outputs={"lint_output": lint_output, "lint_ok": lint_ok},
                metrics={"lint_duration_sec": round(lint_duration, 4)},
            )
            logger.info("[PIPELINE] Verilator Lint %s in %.3fs", "PASSED" if lint_ok else "FAILED", lint_duration)

            # Stage 4: Behavioral Simulation (Icarus Verilog)
            sim_ok = False
            sim_output = ""
            timed_out = False
            if lint_ok:
                sim_start = time.time()
                sim_ok, sim_output, timed_out = self.tools.simulate(
                    code=extracted_code,
                    testbench_code=problem.testbench_code,
                    module_name=problem.module_name,
                )
                sim_duration = time.time() - sim_start
                last_sim_ok = sim_ok
                last_sim_output = sim_output
                last_timed_out = timed_out

                sim_status = "SUCCESS" if sim_ok else ("TIMEOUT" if timed_out else "FAILURE")
                tracer.record_stage(
                    stage_id="behavioral_sim",
                    stage_name="Icarus Verilog Simulation",
                    step_index=step_idx,
                    level=level_name,
                    status=sim_status,
                    duration_sec=sim_duration,
                    inputs={"module_name": problem.module_name, "has_whitebox_tb": bool(problem.testbench_code)},
                    outputs={"sim_output": sim_output, "sim_ok": sim_ok, "timed_out": timed_out},
                    metrics={"sim_duration_sec": round(sim_duration, 4)},
                )
                logger.info("[PIPELINE] Iverilog Simulation %s in %.3fs", sim_status, sim_duration)
            else:
                last_sim_ok = False
                last_sim_output = "Skipped simulation due to lint/compilation errors."
                sim_output = last_sim_output
                tracer.record_stage(
                    stage_id="behavioral_sim",
                    stage_name="Icarus Verilog Simulation",
                    step_index=step_idx,
                    level=level_name,
                    status="SKIPPED",
                    duration_sec=0.0,
                    inputs={"module_name": problem.module_name},
                    outputs={"sim_output": sim_output, "sim_ok": False, "timed_out": False},
                    error_message="Skipped simulation because static lint check failed.",
                )
                logger.info("[PIPELINE] Iverilog Simulation SKIPPED due to lint error.")

            # Stage 5: Reflection Decision
            decision_start = time.time()
            if sim_ok:
                decision = "SOLVED_EARLY_EXIT"
                decision_status = "SUCCESS"
            elif step_idx + 1 >= max_rounds:
                decision = "BUDGET_EXHAUSTED"
                decision_status = "FAILURE"
            elif not lint_ok:
                decision = "TRIGGER_L1_LINT_REFLECTION"
                decision_status = "RETRY"
            elif not sim_ok:
                decision = "TRIGGER_L2_SIM_REFLECTION" if step_idx < 2 else "TRIGGER_MULTI_TURN_REPAIR"
                decision_status = "RETRY"
            else:
                decision = "CONTINUE"
                decision_status = "RETRY"

            tracer.record_stage(
                stage_id="reflection_decision",
                stage_name="Reflection Pipeline Decision",
                step_index=step_idx,
                level=level_name,
                status=decision_status,
                duration_sec=time.time() - decision_start,
                inputs={"step_index": step_idx, "lint_ok": lint_ok, "sim_ok": sim_ok},
                outputs={"decision": decision, "next_round": step_idx + 2 if not sim_ok else None},
            )

            step_elapsed = time.time() - step_start
            stage_dicts = [e.to_dict() for e in tracer.get_step_events(step_idx)]

            solve_step = SolveStep(
                step_index=step_idx,
                level=level_name,
                prompt=messages[-1]["content"],
                completion=completion,
                extracted_code=extracted_code,
                lint_ok=lint_ok,
                lint_output=lint_output,
                sim_ok=sim_ok,
                sim_output=sim_output,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                elapsed_sec=step_elapsed,
                stages=stage_dicts,
            )
            steps.append(solve_step)

            # Early Exit upon passing functional verification
            if sim_ok:
                logger.info("Problem %s successfully SOLVED at %s!", problem.name, level_name)
                total_elapsed = time.time() - start_time
                return SolveResult(
                    problem_name=problem.name,
                    solved=True,
                    solved_level=level_name,
                    final_code=current_code,
                    steps=steps,
                    total_prompt_tokens=total_prompt_tokens,
                    total_completion_tokens=total_completion_tokens,
                    total_elapsed_sec=total_elapsed,
                    failure_reason=None,
                )

        # If budget exhausted without passing
        total_elapsed = time.time() - start_time
        failure_msg = (
            f"Exhausted maximum reflection budget ({max_rounds} rounds). "
            f"Last lint_ok={last_lint_ok}, last_sim_ok={last_sim_ok}, timed_out={last_timed_out}."
        )
        logger.warning("Problem %s FAILED: %s", problem.name, failure_msg)

        return SolveResult(
            problem_name=problem.name,
            solved=False,
            solved_level=None,
            final_code=current_code,
            steps=steps,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_elapsed_sec=total_elapsed,
            failure_reason=failure_msg,
        )
