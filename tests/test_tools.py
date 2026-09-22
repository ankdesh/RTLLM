"""Unit tests for RTLToolEnvironment."""

from pathlib import Path

from reflection_agent_fw.tools import RTLToolEnvironment


def test_tool_environment_lint_valid_code() -> None:
    tools = RTLToolEnvironment()
    code = (
        "module adder_test(\n"
        "    input [7:0] a,\n"
        "    input [7:0] b,\n"
        "    output [7:0] sum\n"
        ");\n"
        "    assign sum = a + b;\n"
        "endmodule\n"
    )
    ok, diag = tools.lint(code, module_name="adder_test")
    assert ok is True


def test_tool_environment_lint_invalid_code() -> None:
    tools = RTLToolEnvironment()
    code = (
        "module broken_test(\n"
        "    input a,\n"
        "    output b\n"
        ");\n"
        "    this is not valid verilog syntax\n"
        "endmodule\n"
    )
    ok, diag = tools.lint(code, module_name="broken_test")
    assert ok is False
    assert "%Error" in diag or "syntax" in diag.lower()


def test_tool_environment_simulate_pass() -> None:
    tools = RTLToolEnvironment()
    rtl = (
        "module simple_gate(input a, input b, output y);\n"
        "    assign y = a & b;\n"
        "endmodule\n"
    )
    tb = (
        "`timescale 1ns/1ps\n"
        "module testbench;\n"
        "    reg a, b;\n"
        "    wire y;\n"
        "    simple_gate dut (.a(a), .b(b), .y(y));\n"
        "    initial begin\n"
        "        a = 1; b = 1; #1;\n"
        "        if (y == 1) $display(\"Your Design Passed\");\n"
        "        $finish;\n"
        "    end\n"
        "endmodule\n"
    )
    ok, output, timed_out = tools.simulate(code=rtl, testbench_code=tb, module_name="simple_gate")
    assert ok is True
    assert timed_out is False
    assert "Your Design Passed" in output
