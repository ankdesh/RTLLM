"""Tool execution environment for static linting and behavioral simulation."""

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Search paths for EDA tools
DEFAULT_CONDA_EDA_DIR: Path = Path("/home/ankdesh/.gemini/antigravity/scratch/conda_eda/bin")
DEFAULT_TIMEOUT_SEC: float = 10.0
PASS_PATTERN: re.Pattern = re.compile(r"your\s+design\s+passed", re.IGNORECASE)


class RTLToolEnvironment:
    """Independent execution environment for Verilog linting and simulation.

    Operates in zero-pollution temporary directories and runs static analysis
    (Verilator) and behavioral simulation (Icarus Verilog).
    """

    def __init__(
        self,
        iverilog_path: Optional[str] = None,
        vvp_path: Optional[str] = None,
        verilator_path: Optional[str] = None,
    ) -> None:
        """Initialize and detect available EDA tool binaries."""
        self._iverilog_path = self._resolve_binary("iverilog", iverilog_path)
        self._vvp_path = self._resolve_binary("vvp", vvp_path)
        self._verilator_path = self._resolve_verilator(verilator_path)

    def _resolve_binary(self, name: str, explicit_path: Optional[str]) -> Optional[Path]:
        """Locate executable binary using explicit path, environment, Conda EDA, or PATH."""
        if explicit_path and Path(explicit_path).is_file():
            return Path(explicit_path).resolve()

        # Check conda eda path
        candidate = DEFAULT_CONDA_EDA_DIR / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

        # Check virtualenv bin
        venv_bin = Path(sys.prefix) / "bin" / name
        if venv_bin.is_file() and os.access(venv_bin, os.X_OK):
            return venv_bin

        # Search PATH
        found = shutil.which(name)
        if found:
            return Path(found).resolve()

        return None

    def _resolve_verilator(self, explicit_path: Optional[str]) -> Optional[Path]:
        """Locate verilator-cli executable."""
        if explicit_path and Path(explicit_path).is_file():
            return Path(explicit_path).resolve()

        # Check .venv/bin/verilator-cli
        venv_cli = Path(sys.prefix) / "bin" / "verilator-cli"
        if venv_cli.is_file() and os.access(venv_cli, os.X_OK):
            return venv_cli

        venv_verilator = Path(sys.prefix) / "bin" / "verilator"
        if venv_verilator.is_file() and os.access(venv_verilator, os.X_OK):
            return venv_verilator

        found_cli = shutil.which("verilator-cli")
        if found_cli:
            return Path(found_cli).resolve()

        found = shutil.which("verilator")
        if found:
            return Path(found).resolve()

        return None

    def lint(self, code: str, module_name: str = "rtl") -> Tuple[bool, str]:
        """Run fast static linting on Verilog source code using Verilator.

        Args:
            code: Verilog source code.
            module_name: Module identifier used for temp filename.

        Returns:
            Tuple of (lint_ok, diagnostic_output).
        """
        if not self._verilator_path:
            logger.warning("Verilator binary not found. Skipping static lint check.")
            return True, "Verilator not available on host system."

        with tempfile.TemporaryDirectory(prefix="refl_lint_") as temp_dir:
            file_path = Path(temp_dir) / f"{module_name}.v"
            file_path.write_text(code, encoding="utf-8")

            cmd = [
                str(self._verilator_path),
                "--lint-only",
                "-Wall",
                "-Wno-fatal",
                str(file_path),
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                )
                output = (proc.stdout + "\n" + proc.stderr).strip()
                has_error = proc.returncode != 0 or "%Error" in output
                return not has_error, output
            except subprocess.TimeoutExpired:
                return False, "Linting timed out after 5.0 seconds."
            except Exception as e:
                return False, f"Lint execution error: {str(e)}"

    def simulate(
        self,
        code: str,
        testbench_code: str,
        module_name: str = "rtl",
        timeout: float = DEFAULT_TIMEOUT_SEC,
    ) -> Tuple[bool, str, bool]:
        """Compile and execute behavioral simulation using Icarus Verilog.

        Args:
            code: Generated RTL Verilog code.
            testbench_code: White-box testbench code.
            module_name: Module identifier.
            timeout: Maximum execution seconds before timeout.

        Returns:
            Tuple of (sim_ok, sim_output, timed_out).
        """
        if not self._iverilog_path or not self._vvp_path:
            return False, "Icarus Verilog (iverilog/vvp) not found.", False

        with tempfile.TemporaryDirectory(prefix="refl_sim_") as temp_dir:
            rtl_file = Path(temp_dir) / f"{module_name}.v"
            tb_file = Path(temp_dir) / "testbench.v"
            vvp_out = Path(temp_dir) / "sim.vvp"

            rtl_file.write_text(code, encoding="utf-8")
            tb_file.write_text(testbench_code, encoding="utf-8")

            # 1. Compilation with iverilog
            compile_cmd = [
                str(self._iverilog_path),
                "-g2012",
                "-o",
                str(vvp_out),
                str(rtl_file),
                str(tb_file),
            ]

            try:
                compile_proc = subprocess.run(
                    compile_cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if compile_proc.returncode != 0 or not vvp_out.is_file():
                    err_msg = (compile_proc.stdout + "\n" + compile_proc.stderr).strip()
                    return False, f"Compilation failed:\n{err_msg}", False
            except subprocess.TimeoutExpired:
                return False, f"Compilation timed out after {timeout} seconds.", True
            except Exception as e:
                return False, f"Compilation error: {str(e)}", False

            # 2. Simulation execution with vvp
            run_cmd = [str(self._vvp_path), str(vvp_out)]
            try:
                run_proc = subprocess.run(
                    run_cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                sim_output = (run_proc.stdout + "\n" + run_proc.stderr).strip()
                sim_ok = bool(PASS_PATTERN.search(sim_output))
                return sim_ok, sim_output, False
            except subprocess.TimeoutExpired:
                return False, f"Simulation timed out after {timeout} seconds (possible infinite loop or hang).", True
            except Exception as e:
                return False, f"Simulation runtime error: {str(e)}", False
