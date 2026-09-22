"""Verilator simulation and static linting backend implementation."""

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
DEFAULT_VENV_DIR: Path = Path(__file__).resolve().parent.parent / ".venv" / "bin"
DEFAULT_CONDA_EDA_DIR: Path = Path("/home/ankdesh/.gemini/antigravity/scratch/conda_eda/bin")
VERILATOR_LINT_FLAGS: List[str] = ["--lint-only", "-Wall", "-Wno-fatal"]
VERILATOR_SIM_FLAGS: List[str] = [
    "--binary",
    "--timing",
    "-Wno-fatal",
    "-Wno-TIMESCALEMOD",
    "-Wno-WIDTHEXPAND",
    "-Wno-WIDTHTRUNC",
    "--top-module",
    "testbench",
]
FUNCTIONAL_PASS_PATTERN: re.Pattern = re.compile(r"your\s+design\s+passed", re.IGNORECASE)


class VerilatorSimulator(BaseSimulator):
    """Verilator backend providing sub-10ms static linting and cycle-accurate compiled simulation."""

    def __init__(self, bin_dir: Optional[Path] = None) -> None:
        """Initialize simulator and locate verilator executable.

        Args:
            bin_dir: Optional directory containing verilator or verilator-cli binary.
        """
        self._verilator_path: Optional[Path] = None
        self._locate_binary(bin_dir)

    @property
    def name(self) -> str:
        """Return simulator backend name."""
        return "verilator"

    def _locate_binary(self, custom_dir: Optional[Path]) -> None:
        """Find executable path for verilator or verilator-cli."""
        candidate_dirs: List[Path] = []

        # 1. Custom directory
        if custom_dir:
            candidate_dirs.append(Path(custom_dir).resolve())

        # 2. Environment variable override
        env_bin = os.getenv("VERILATOR_BIN")
        if env_bin:
            candidate_dirs.append(Path(env_bin).resolve())

        # 3. Local virtual environment
        if DEFAULT_VENV_DIR.is_dir():
            candidate_dirs.append(DEFAULT_VENV_DIR)

        # 4. Conda EDA directory
        if DEFAULT_CONDA_EDA_DIR.is_dir():
            candidate_dirs.append(DEFAULT_CONDA_EDA_DIR)

        # 5. PATH check
        for binary_name in ("verilator-cli", "verilator"):
            which_res = shutil.which(binary_name)
            if which_res:
                self._verilator_path = Path(which_res).resolve()
                return

        for d in candidate_dirs:
            for binary_name in ("verilator-cli", "verilator"):
                candidate = d / binary_name
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    self._verilator_path = candidate
                    return

    def check_available(self) -> bool:
        """Return True if verilator binary is available."""
        return bool(self._verilator_path and self._verilator_path.is_file())

    def _get_exec_env(self) -> dict:
        """Return execution environment with virtual environment bin prepended to PATH."""
        env = os.environ.copy()
        venv_bin_str = str(DEFAULT_VENV_DIR)
        current_path = env.get("PATH", "")
        if venv_bin_str not in current_path:
            env["PATH"] = f"{venv_bin_str}:{current_path}"
        return env

    def lint(self, rtl_path: Path, design_name: Optional[str] = None) -> SimResult:
        """Perform ultra-fast static linting using verilator --lint-only."""
        if not self.check_available():
            raise RuntimeError(
                f"Verilator binary not found. Checked PATH, {DEFAULT_VENV_DIR}, and {DEFAULT_CONDA_EDA_DIR}"
            )

        name = design_name or rtl_path.stem
        start_time = time.perf_counter()

        cmd = [str(self._verilator_path)] + VERILATOR_LINT_FLAGS + [str(rtl_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=self._get_exec_env())
        elapsed = time.perf_counter() - start_time

        output = (res.stdout + "\n" + res.stderr).strip()
        syntax_ok = (res.returncode == 0 and "%Error" not in output)

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
        """Compile and execute binary simulation using Verilator 5 timing support."""
        if not self.check_available():
            raise RuntimeError(
                f"Verilator binary not found. Checked PATH, {DEFAULT_VENV_DIR}, and {DEFAULT_CONDA_EDA_DIR}"
            )

        name = design_name or rtl_path.stem
        start_time = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="rtllm_vlt_") as tmp_dir:
            obj_dir = Path(tmp_dir) / "obj_dir"
            compile_cmd = (
                [str(self._verilator_path)]
                + VERILATOR_SIM_FLAGS
                + ["-Mdir", str(obj_dir), str(rtl_path), str(tb_path)]
            )

            comp_res = subprocess.run(
                compile_cmd,
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                env=self._get_exec_env(),
            )
            comp_output = (comp_res.stdout + "\n" + comp_res.stderr).strip()

            exe_target = obj_dir / "Vtestbench"
            if comp_res.returncode != 0 or not exe_target.is_file():
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

            # Step 2: Execute compiled binary
            run_cmd = [str(exe_target)]
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
                    env=self._get_exec_env(),
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
