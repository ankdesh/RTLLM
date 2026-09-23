"""Data structures representing the execution trajectory and outcome of solving an RTL problem."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SolveStep:
    """Telemetry and outcome of an individual reflection attempt or generation step."""

    step_index: int
    level: str
    prompt: str
    completion: str
    extracted_code: str
    lint_ok: bool
    lint_output: str
    sim_ok: bool
    sim_output: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_sec: float = 0.0
    stages: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert solve step to serializable dictionary."""
        return {
            "step_index": self.step_index,
            "level": self.level,
            "prompt": self.prompt,
            "completion": self.completion,
            "extracted_code": self.extracted_code,
            "lint_ok": self.lint_ok,
            "lint_output": self.lint_output,
            "sim_ok": self.sim_ok,
            "sim_output": self.sim_output,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "elapsed_sec": round(self.elapsed_sec, 4),
            "stages": self.stages,
        }


@dataclass
class SolveResult:
    """Comprehensive result of attempting to solve an RTL problem across reflection steps."""

    problem_name: str
    solved: bool
    solved_level: Optional[str]
    final_code: str
    steps: List[SolveStep] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_elapsed_sec: float = 0.0
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert solve result to serializable dictionary."""
        return {
            "problem_name": self.problem_name,
            "solved": self.solved,
            "solved_level": self.solved_level,
            "final_code": self.final_code,
            "steps": [s.to_dict() for s in self.steps],
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_elapsed_sec": round(self.total_elapsed_sec, 4),
            "failure_reason": self.failure_reason,
        }
