"""Unit tests for Verilog code extraction."""

from reflection_agent_fw.code_extractor import VerilogCodeExtractor


def test_extract_from_fenced_block() -> None:
    text = (
        "Here is the module you requested:\n\n"
        "```verilog\n"
        "module adder_8bit(\n"
        "    input [7:0] a,\n"
        "    input [7:0] b,\n"
        "    output [7:0] sum\n"
        ");\n"
        "    assign sum = a + b;\n"
        "endmodule\n"
        "```\n"
        "I hope this helps!"
    )
    code = VerilogCodeExtractor.extract(text, expected_module="adder_8bit")
    assert "module adder_8bit" in code
    assert "assign sum = a + b;" in code
    assert "endmodule" in code
    assert "Here is the module" not in code


def test_extract_without_fences() -> None:
    text = (
        "Below is the code:\n\n"
        "module counter_12(\n"
        "    input clk,\n"
        "    output reg [3:0] count\n"
        ");\n"
        "    always @(posedge clk) count <= count + 1;\n"
        "endmodule\n"
        "Notice non-blocking assignment is used."
    )
    code = VerilogCodeExtractor.extract(text, expected_module="counter_12")
    assert code.startswith("module counter_12")
    assert code.endswith("endmodule")
