"""Unit tests for ReflectionPromptBuilder."""

from reflection_agent_fw.prompt_builder import ReflectionPromptBuilder


def test_build_l0_messages() -> None:
    msgs = ReflectionPromptBuilder.build_l0_messages(
        prompt="Design an 8-bit accumulator.",
        module_name="accu",
    )
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert "Design an 8-bit accumulator." in msgs[1]["content"]
    assert "accu" in msgs[1]["content"]


def test_build_l1_lint_messages() -> None:
    msgs = ReflectionPromptBuilder.build_l1_lint_messages(
        module_name="accu",
        previous_code="module accu; syntax error; endmodule",
        lint_output="%Error: syntax error near 'error'",
    )
    assert len(msgs) == 2
    assert "syntax error near 'error'" in msgs[1]["content"]
    assert "module accu; syntax error; endmodule" in msgs[1]["content"]


def test_build_l2_sim_messages_whitebox() -> None:
    tb_code = "module testbench; initial $display(\"Testing\"); endmodule"
    msgs = ReflectionPromptBuilder.build_l2_sim_messages(
        module_name="accu",
        previous_code="module accu(input clk); endmodule",
        sim_output="Failed vector 3: expected 15, got 0",
        testbench_code=tb_code,
    )
    assert len(msgs) == 2
    assert "Failed vector 3: expected 15, got 0" in msgs[1]["content"]
    assert "White-Box Reference" in msgs[1]["content"]
    assert tb_code in msgs[1]["content"]
