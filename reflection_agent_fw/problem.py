"""Data contract representing a single RTL design problem for reflection_agent_fw."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RTLProblem:
    """Independent definition of a single Register-Transfer Level (RTL) task.

    This class encapsulates everything needed to solve and verify a single
    hardware design problem without any coupling to external benchmark datasets.
    """

    name: str
    module_name: str
    prompt: str
    testbench_code: str
    target_filename: str = "rtl.v"
    max_reflection_rounds: int = 5
    temperature: float = 0.2

    def to_dict(self) -> Dict[str, Any]:
        """Serialize problem definition to a dictionary."""
        return {
            "name": self.name,
            "module_name": self.module_name,
            "prompt": self.prompt,
            "testbench_code": self.testbench_code,
            "target_filename": self.target_filename,
            "max_reflection_rounds": self.max_reflection_rounds,
            "temperature": self.temperature,
        }
