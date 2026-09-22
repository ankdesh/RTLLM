"""End-to-end integration test for the evaluation engine."""

from pathlib import Path
import pytest

from agent_eval.eval_runner import EvaluationRunner
from agent_eval.iverilog_simulator import IverilogSimulator


def test_evaluation_runner_end_to_end() -> None:
    """Run evaluation over _chatgpt4/t1 and verify summary contents."""
    sim = IverilogSimulator()
    runner = EvaluationRunner(simulator=sim, threads=4, timeout=5.0)

    repo_root = Path(__file__).resolve().parent.parent
    model_dir = repo_root / "_chatgpt4" / "t1"

    summary = runner.evaluate(model_dir=model_dir)

    assert summary.total_designs == 50
    assert summary.total_trials == 1
    assert summary.syntax_success_designs > 20
    assert summary.func_success_designs > 5
    assert "Arithmetic" in summary.category_breakdown
    assert "pass@1" in summary.pass_at_k
