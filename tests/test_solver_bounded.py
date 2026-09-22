"""Unit tests verifying ReflectionAgentSolver bounds and early stopping."""

from typing import Dict, List, Tuple
from unittest.mock import MagicMock

from reflection_agent_fw.llm_client import OpenAICompatibleClient
from reflection_agent_fw.problem import RTLProblem
from reflection_agent_fw.solver import ReflectionAgentSolver
from reflection_agent_fw.tools import RTLToolEnvironment


def test_solver_early_exit_on_l0_success() -> None:
    # Mock LLM that returns working code immediately
    mock_llm = MagicMock(spec=OpenAICompatibleClient)
    mock_llm.complete.return_value = (
        "```verilog\n"
        "module simple_gate(input a, input b, output y);\n"
        "    assign y = a & b;\n"
        "endmodule\n"
        "```",
        100,
        50,
    )

    tb = (
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

    problem = RTLProblem(
        name="simple_gate",
        module_name="simple_gate",
        prompt="Implement an AND gate",
        testbench_code=tb,
        max_reflection_rounds=5,
    )

    solver = ReflectionAgentSolver(llm_client=mock_llm)
    res = solver.solve(problem)

    assert res.solved is True
    assert res.solved_level == "L0_ZERO_SHOT"
    assert len(res.steps) == 1
    assert mock_llm.complete.call_count == 1


def test_solver_strictly_bounds_reflection_rounds() -> None:
    # Mock LLM that always returns syntax error code
    mock_llm = MagicMock(spec=OpenAICompatibleClient)
    mock_llm.complete.return_value = (
        "```verilog\n"
        "module broken_mod(input a, output b);\n"
        "    syntax error;\n"
        "endmodule\n"
        "```",
        50,
        20,
    )

    problem = RTLProblem(
        name="broken_mod",
        module_name="broken_mod",
        prompt="Broken prompt",
        testbench_code="module testbench; endmodule",
        max_reflection_rounds=3,  # strictly bounded to 3 rounds
    )

    solver = ReflectionAgentSolver(llm_client=mock_llm)
    res = solver.solve(problem)

    assert res.solved is False
    assert res.solved_level is None
    assert len(res.steps) == 3
    assert mock_llm.complete.call_count == 3
    assert "Exhausted maximum reflection budget (3 rounds)" in (res.failure_reason or "")
