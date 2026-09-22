"""Abstract adapter interface and trajectory data model for agent frameworks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent_eval.models import DesignMeta


@dataclass
class FrameworkTrajectory:
    """Standardized trajectory representation returned by any agent framework."""

    design_name: str
    category: str
    subcategory: str
    solved: bool
    solved_level: Optional[str]
    final_code: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_elapsed_sec: float = 0.0
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert framework trajectory to dictionary."""
        return {
            "design_name": self.design_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "solved": self.solved,
            "solved_level": self.solved_level,
            "final_code": self.final_code,
            "steps": self.steps,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_elapsed_sec": round(self.total_elapsed_sec, 4),
            "failure_reason": self.failure_reason,
        }


class BaseAgentAdapter(ABC):
    """Abstract interface defining the contract for any agent framework in RTLLM."""

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Return unique identifier for the agent framework."""

    @abstractmethod
    def solve(
        self,
        design: DesignMeta,
        max_rounds: int = 5,
        timeout: float = 10.0,
    ) -> FrameworkTrajectory:
        """Execute the agent framework on a single benchmark design.

        Args:
            design: Metadata of the design problem.
            max_rounds: Maximum reflection or generation attempts budget.
            timeout: Maximum execution timeout for simulation steps.

        Returns:
            FrameworkTrajectory capturing the execution outcome.
        """
