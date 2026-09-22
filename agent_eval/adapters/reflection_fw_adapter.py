"""Adapter bridging reflection_agent_fw to the RTLLM benchmark harness."""

import logging
from pathlib import Path
from typing import Optional

from agent_eval.framework_adapter import BaseAgentAdapter, FrameworkTrajectory
from agent_eval.models import DesignMeta
from reflection_agent_fw.llm_client import OpenAICompatibleClient
from reflection_agent_fw.problem import RTLProblem
from reflection_agent_fw.solver import ReflectionAgentSolver
from reflection_agent_fw.tools import RTLToolEnvironment

logger = logging.getLogger(__name__)


class ReflectionFWAdapter(BaseAgentAdapter):
    """Adapter that executes the isolated reflection_agent_fw on RTLLM benchmark designs."""

    def __init__(
        self,
        llm_client: OpenAICompatibleClient,
        repo_root: Optional[Path] = None,
        tool_env: Optional[RTLToolEnvironment] = None,
    ) -> None:
        """Initialize adapter with LLM client, repository root, and tool environment."""
        self.llm_client = llm_client
        self.repo_root = repo_root or Path.cwd()
        self.solver = ReflectionAgentSolver(llm_client=self.llm_client, tool_env=tool_env)

    @property
    def framework_name(self) -> str:
        """Identifier for this framework."""
        return "reflection_agent_fw"

    def solve(
        self,
        design: DesignMeta,
        max_rounds: int = 5,
        timeout: float = 10.0,
    ) -> FrameworkTrajectory:
        """Translate RTLLM DesignMeta into RTLProblem and solve via ReflectionAgentSolver."""
        tb_abs_path = (self.repo_root / design.testbench_path).resolve()
        if not tb_abs_path.is_file():
            raise FileNotFoundError(f"Testbench not found for design {design.design_name} at {tb_abs_path}")

        testbench_code = tb_abs_path.read_text(encoding="utf-8")

        problem = RTLProblem(
            name=design.design_name,
            module_name=design.module_name,
            prompt=design.prompt,
            testbench_code=testbench_code,
            target_filename=design.target_filename,
            max_reflection_rounds=max_rounds,
        )

        solve_result = self.solver.solve(problem)

        return FrameworkTrajectory(
            design_name=design.design_name,
            category=design.category,
            subcategory=design.subcategory,
            solved=solve_result.solved,
            solved_level=solve_result.solved_level,
            final_code=solve_result.final_code,
            steps=[s.to_dict() for s in solve_result.steps],
            total_prompt_tokens=solve_result.total_prompt_tokens,
            total_completion_tokens=solve_result.total_completion_tokens,
            total_elapsed_sec=solve_result.total_elapsed_sec,
            failure_reason=solve_result.failure_reason,
        )
