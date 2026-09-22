"""Icarus Verilog simulation backend implementation."""

import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional

from agent_eval.models import SimResult
from agent_eval.simulator_interface import DEFAULT_SIMULATION_TIMEOUT_SEC, BaseSimulator

logger = logging.getLogger(__name__)

# Constants and search paths
DEFAULT_CONDA_EDA_DIR: Path = Path("/home/ankdesh/.gemini/antigravity/scratch/conda_eda/bin")
IVERILOG_COMPILER_FLAGS: List[str] = ["-g2012"]
FUNCTIONAL_PASS_PATTERN: re.Pattern = re.compile(r"your\s+design\s+passed", re.IGNORECASE)


class IverilogSimulator(BaseSimulator):
    """Event-driven functional simulator backend using Icarus Verilog (iverilog & vvp)."""

    def __init__(self, bin_dir: Optional[Path] = None) -> None:
        """Initialize simulator and locate iverilog and vvp executables.

        Args:
            bin_dir: Optional directory containing iverilog and vvp binaries.
        """
        self._iverilog_path: Optional[Path] = None
        self._vvp_path: Optional[Path] = None
        self._locate_binaries(bin_dir)

    @property
    def name(self) -> str:
        """Return simulator backend name."""
        return "iverilog"

    def _locate_binaries(self, custom_dir: Optional[Path]) -> None:
        """Find executable paths for iverilog and vvp."""
        candidate_dirs: List[Path] = []

        # 1. Custom directory passed by user
        if custom_dir:
            candidate_dirs.append(Path(custom_dir).resolve())

        # 2. Environment variable override
        env_bin = os.getenv("IVERILOG_BIN")
        if env_bin:
            candidate_dirs.append(Path(env_bin).resolve())

        # 3. Known Conda EDA installation directory
        if DEFAULT_CONDA_EDA_DIR.is_dir():
            candidate_dirs.append(DEFAULT_CONDA_EDA_DIR)

        # 4. PATH lookup
        iverilog_which = shutil.which("iverilog")
        vvp_which = shutil.which("vvp")

        if iverilog_which and vvp_which:
            self._iverilog_path = Path(iverilog_which).resolve()
            self._vvp_path = Path(vvp_which).resolve()
            return

        for d in candidate_dirs:
            iv = d / "iverilog"
            vp = d / "vvp"
            if iv.is_file() and os.access(iv, os.X_OK) and vp.is_file() and os.access(vp, os.X_OK):
                self._iverilog_path = iv
                self._vvp_path = vp
                return

    def check_available(self) -> bool:
        """Return True if both iverilog and vvp are executable."""
        return bool(
            self._iverilog_path
            and self._vvp_path
            and self._iverilog_path.is_file()
            and self._vvp_path.is_file()
        )

    def lint(self, rtl_path: Path, design_name: Optional[str] = None) -> SimResult:
        """Lint RTL syntax using iverilog parser and elaborator in null-target mode."""
        if not self.check_available():
            raise RuntimeError(
                f"Icarus Verilog binaries (iverilog, vvp) not found. "
                f"Checked standard PATH and {DEFAULT_CONDA_EDA_DIR}"
            )

        name = design_name or rtl_path.stem
        start_time = time.perf_counter()

        cmd = [str(self._iverilog_path)] + IVERILOG_COMPILER_FLAGS + ["-t", "null", str(rtl_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.perf_counter() - start_time

        syntax_ok = (res.returncode == 0)
        output = (res.stdout + "\n" + res.stderr).strip()

        return SimResult(
            design_name=name,
            trial_name="lint",
            syntax_ok=syntax_ok,
            func_ok=False,
            timed_out=False,
            return_code=res.returncode,
            compile_output=output,
            sim_output="",
            elapsed_sec=elapsed,
        )

    def simulate(
        self,
        rtl_path: Path,
        tb_path: Path,
        design_name: Optional[str] = None,
        trial_name: str = "trial",
        timeout: float = DEFAULT_SIMULATION_TIMEOUT_SEC,
    ) -> SimResult:
        """Compile and simulate RTL with testbench in an isolated temporary directory."""
        if not self.check_available():
            raise RuntimeError(
                f"Icarus Verilog binaries (iverilog, vvp) not found. "
                f"Checked standard PATH and {DEFAULT_CONDA_EDA_DIR}"
            )

        name = design_name or rtl_path.stem
        start_time = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="rtllm_sim_") as tmp_dir:
            sim_exec = Path(tmp_dir) / "sim.out"

            # Step 1: Compile RTL and Testbench
            compile_cmd = (
                [str(self._iverilog_path)]
                + IVERILOG_COMPILER_FLAGS
                + ["-o", str(sim_exec), str(rtl_path), str(tb_path)]
            )

            comp_res = subprocess.run(compile_cmd, capture_output=True, text=True)
            comp_output = (comp_res.stdout + "\n" + comp_res.stderr).strip()

            if comp_res.returncode != 0 or not sim_exec.is_file():
                elapsed = time.perf_counter() - start_time
                return SimResult(
                    design_name=name,
                    trial_name=trial_name,
                    syntax_ok=False,
                    func_ok=False,
                    timed_out=False,
                    return_code=comp_res.returncode,
                    compile_output=comp_output,
                    sim_output="",
                    elapsed_sec=elapsed,
                )

            # Step 2: Execute Simulation using vvp
            run_cmd = [str(self._vvp_path), str(sim_exec)]
            timed_out = False
            sim_output = ""
            ret_code = 0

            try:
                sim_res = subprocess.run(
                    run_cmd,
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                ret_code = sim_res.returncode
                sim_output = (sim_res.stdout + "\n" + sim_res.stderr).strip()
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                ret_code = -1
                sim_output = f"Simulation timed out after {timeout} seconds.\n"
                if exc.stdout:
                    sim_output += exc.stdout.decode("utf-8", errors="replace")

            elapsed = time.perf_counter() - start_time
            func_ok = bool(not timed_out and FUNCTIONAL_PASS_PATTERN.search(sim_output))

            return SimResult(
                design_name=name,
                trial_name=trial_name,
                syntax_ok=True,
                func_ok=func_ok,
                timed_out=timed_out,
                return_code=ret_code,
                compile_output=comp_output,
                sim_output=sim_output,
                elapsed_sec=elapsed,
            )
