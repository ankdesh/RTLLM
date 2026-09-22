"""Core solver engine executing stage-gated reflection for a single RTL problem."""

import logging
import time
from typing import Optional

from reflection_agent_fw.code_extractor import VerilogCodeExtractor
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
        """Initialize solver with LLM client and EDA tool environment.

        Args:
            llm_client: Configured OpenAI-compatible client.
            tool_env: Optional RTLToolEnvironment (created with defaults if omitted).
        """
        self.llm_client = llm_client
        self.tools = tool_env or RTLToolEnvironment()

    def solve(self, problem: RTLProblem) -> SolveResult:
        """Solve a single RTL problem using bounded stage-gated reflection.

        Workflow:
        1. L0 (Zero-Shot): Initial prompt -> Extract RTL -> Lint -> Sim. Early exit if passed.
        2. L1 (Lint Reflection): If lint failed, feed compiler diagnostics -> Extract RTL -> Lint -> Sim.
        3. L2 (Sim Reflection): If sim failed, feed testbench logs + full white-box testbench -> Lint -> Sim.
        4. L3-L5 (Iterative Multi-Turn): Loop until functional pass or bounded tries exhausted.

        Args:
            problem: RTLProblem instance defining the specification and testbench.

        Returns:
            SolveResult capturing the entire trajectory and final status.
        """
        steps = []
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

            # Determine level and build appropriate prompt
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

            # Query LLM
            logger.info("Executing %s for %s (round %d/%d)...", level_name, problem.name, step_idx + 1, max_rounds)
            completion, p_tokens, c_tokens = self.llm_client.complete(
                messages=messages,
                temperature=problem.temperature,
            )
            total_prompt_tokens += p_tokens
            total_completion_tokens += c_tokens

            # Extract RTL code
            extracted_code = VerilogCodeExtractor.extract(
                raw_text=completion,
                expected_module=problem.module_name,
            )
            current_code = extracted_code

            # Evaluate static linting
            lint_ok, lint_output = self.tools.lint(
                code=extracted_code,
                module_name=problem.module_name,
            )
            last_lint_ok = lint_ok
            last_lint_output = lint_output

            # Evaluate simulation if lint succeeds
            sim_ok = False
            sim_output = ""
            timed_out = False
            if lint_ok:
                sim_ok, sim_output, timed_out = self.tools.simulate(
                    code=extracted_code,
                    testbench_code=problem.testbench_code,
                    module_name=problem.module_name,
                )
                last_sim_ok = sim_ok
                last_sim_output = sim_output
                last_timed_out = timed_out
            else:
                last_sim_ok = False
                last_sim_output = "Skipped simulation due to lint/compilation errors."
                sim_output = last_sim_output

            step_elapsed = time.time() - step_start
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
            )
            steps.append(solve_step)

            # Early Exit upon passing functional verification!
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
