"""Abstract base interface for hardware description language (HDL) simulators and linters."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from agent_eval.models import SimResult

# Standard simulation timeout in seconds to terminate hung testbenches or infinite loops
DEFAULT_SIMULATION_TIMEOUT_SEC: float = 10.0


class BaseSimulator(ABC):
    """Abstract interface defining operations for RTL simulation and static linting."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique human-readable identifier of the simulator."""

    @abstractmethod
    def check_available(self) -> bool:
        """Verify whether required simulator binaries are installed and accessible."""

    @abstractmethod
    def lint(self, rtl_path: Path, design_name: Optional[str] = None) -> SimResult:
        """Perform static linting and syntax validation on an RTL source file.

        Args:
            rtl_path: Path to the Verilog source code.
            design_name: Optional design name for reporting.

        Returns:
            SimResult indicating syntax validity and any diagnostic messages.
        """

    @abstractmethod
    def simulate(
        self,
        rtl_path: Path,
        tb_path: Path,
        design_name: Optional[str] = None,
        trial_name: str = "trial",
        timeout: float = DEFAULT_SIMULATION_TIMEOUT_SEC,
    ) -> SimResult:
        """Compile and execute a testbench against an RTL implementation.

        Args:
            rtl_path: Path to the generated RTL file.
            tb_path: Path to the self-checking testbench.
            design_name: Design identifier.
            trial_name: Name of current trial (e.g. 't1').
            timeout: Maximum execution timeout in seconds.

        Returns:
            SimResult containing syntax and functional pass/fail status.
        """
