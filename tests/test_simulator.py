"""Integration tests for Icarus Verilog and Verilator simulation backends."""

from pathlib import Path
import pytest

from agent_eval.iverilog_simulator import IverilogSimulator
from agent_eval.verilator_simulator import VerilatorSimulator


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_iverilog_availability() -> None:
    """Verify Icarus Verilog backend is properly installed and detected."""
    sim = IverilogSimulator()
    assert sim.check_available(), "Icarus Verilog (iverilog & vvp) should be available"


def test_iverilog_simulate_pass(repo_root: Path) -> None:
    """Verify simulation of a known-working design passes testbench."""
    sim = IverilogSimulator()
    rtl = repo_root / "_chatgpt4" / "t1" / "adder_8bit.v"
    tb = repo_root / "Arithmetic" / "Adder" / "adder_8bit" / "testbench.v"

    assert rtl.is_file()
    assert tb.is_file()

    result = sim.simulate(rtl_path=rtl, tb_path=tb, design_name="adder_8bit")
    assert result.syntax_ok is True
    assert result.func_ok is True
    assert result.timed_out is False
    assert result.return_code == 0
    assert "Your Design Passed" in result.sim_output


def test_verilator_lint(repo_root: Path, tmp_path: Path) -> None:
    """Verify Verilator static linting identifies syntax errors."""
    vlt = VerilatorSimulator()
    assert vlt.check_available(), "Verilator should be available"

    # Valid design
    valid_rtl = repo_root / "_chatgpt4" / "t1" / "adder_8bit.v"
    res_valid = vlt.lint(rtl_path=valid_rtl)
    assert res_valid.syntax_ok is True

    # Invalid design with syntax errors
    bad_rtl = tmp_path / "broken.v"
    bad_rtl.write_text("module broken(input a; output b); assign b = a; endmodule")
    res_bad = vlt.lint(rtl_path=bad_rtl)
    assert res_bad.syntax_ok is False
    assert res_bad.return_code != 0
