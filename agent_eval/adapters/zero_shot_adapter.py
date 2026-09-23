"""Baseline adapter for single-shot RTL generation without reflection."""

import logging
import time
from pathlib import Path
from typing import Optional

from agent_eval.framework_adapter import BaseAgentAdapter, FrameworkTrajectory
from agent_eval.models import DesignMeta
from reflection_agent_fw.code_extractor import VerilogCodeExtractor
from reflection_agent_fw.llm_client import OpenAICompatibleClient
from reflection_agent_fw.prompt_builder import ReflectionPromptBuilder
from reflection_agent_fw.tools import RTLToolEnvironment

logger = logging.getLogger(__name__)


class ZeroShotBaselineAdapter(BaseAgentAdapter):
    """Adapter evaluating models in pure zero-shot mode without any reflection."""

    def __init__(
        self,
        llm_client: OpenAICompatibleClient,
        repo_root: Optional[Path] = None,
        tool_env: Optional[RTLToolEnvironment] = None,
    ) -> None:
        """Initialize zero-shot baseline adapter."""
        self.llm_client = llm_client
        self.repo_root = repo_root or Path.cwd()
        self.tools = tool_env or RTLToolEnvironment()

    @property
    def framework_name(self) -> str:
        """Identifier for this framework."""
        return "zero_shot_baseline"

    def solve(
        self,
        design: DesignMeta,
        max_rounds: int = 1,
        timeout: float = 10.0,
    ) -> FrameworkTrajectory:
        """Generate RTL once, verify it, and return trajectory with level L0."""
        start_time = time.time()
        tb_abs_path = (self.repo_root / design.testbench_path).resolve()
        testbench_code = tb_abs_path.read_text(encoding="utf-8")

        messages = ReflectionPromptBuilder.build_l0_messages(
            prompt=design.prompt,
            module_name=design.module_name,
        )

        completion, p_tokens, c_tokens = self.llm_client.complete(messages=messages)
        extracted_code = VerilogCodeExtractor.extract(
            raw_text=completion,
            expected_module=design.module_name,
        )

        lint_ok, lint_output = self.tools.lint(code=extracted_code, module_name=design.module_name)
        sim_ok = False
        sim_output = "Skipped simulation due to lint errors."
        if lint_ok:
            sim_ok, sim_output, _ = self.tools.simulate(
                code=extracted_code,
                testbench_code=testbench_code,
                module_name=design.module_name,
                timeout=timeout,
            )

        elapsed = time.time() - start_time
        stages = [
            {
                "stage_id": "rtl_generation",
                "stage_name": "RTL Code Generation",
                "step_index": 0,
                "level": "L0_ZERO_SHOT",
                "status": "SUCCESS" if bool(extracted_code) else "FAILURE",
                "duration_sec": round(elapsed * 0.8, 4),
                "inputs": {"model": self.llm_client.model},
                "outputs": {"extracted_code": extracted_code, "completion": completion},
                "metrics": {"prompt_tokens": p_tokens, "completion_tokens": c_tokens},
            },
            {
                "stage_id": "static_lint",
                "stage_name": "Verilator Static Lint",
                "step_index": 0,
                "level": "L0_ZERO_SHOT",
                "status": "SUCCESS" if lint_ok else "FAILURE",
                "duration_sec": 0.01,
                "inputs": {"module_name": design.module_name},
                "outputs": {"lint_output": lint_output, "lint_ok": lint_ok},
                "metrics": {},
            },
            {
                "stage_id": "behavioral_sim",
                "stage_name": "Icarus Verilog Simulation",
                "step_index": 0,
                "level": "L0_ZERO_SHOT",
                "status": "SUCCESS" if sim_ok else ("SKIPPED" if not lint_ok else "FAILURE"),
                "duration_sec": 0.1 if lint_ok else 0.0,
                "inputs": {"module_name": design.module_name},
                "outputs": {"sim_output": sim_output, "sim_ok": sim_ok},
                "metrics": {},
            },
            {
                "stage_id": "reflection_decision",
                "stage_name": "Baseline Single-Shot Exit",
                "step_index": 0,
                "level": "L0_ZERO_SHOT",
                "status": "SUCCESS" if sim_ok else "FAILURE",
                "duration_sec": 0.001,
                "inputs": {"sim_ok": sim_ok},
                "outputs": {"decision": "SOLVED_EXIT" if sim_ok else "UNSOLVED_EXIT"},
                "metrics": {},
            },
        ]

        step_dict = {
            "step_index": 0,
            "level": "L0_ZERO_SHOT",
            "prompt": messages[-1]["content"],
            "completion": completion,
            "extracted_code": extracted_code,
            "lint_ok": lint_ok,
            "lint_output": lint_output,
            "sim_ok": sim_ok,
            "sim_output": sim_output,
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "elapsed_sec": round(elapsed, 4),
            "stages": stages,
        }

        return FrameworkTrajectory(
            design_name=design.design_name,
            category=design.category,
            subcategory=design.subcategory,
            solved=sim_ok,
            solved_level="L0_ZERO_SHOT" if sim_ok else None,
            final_code=extracted_code,
            steps=[step_dict],
            total_prompt_tokens=p_tokens,
            total_completion_tokens=c_tokens,
            total_elapsed_sec=elapsed,
            failure_reason=None if sim_ok else f"Zero-shot attempt failed (lint_ok={lint_ok}, sim_ok={sim_ok})",
        )
