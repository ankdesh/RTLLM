"""Unit tests for BenchmarkStatisticsAggregator and BenchmarkReporter."""

import tempfile
from pathlib import Path

from agent_eval.benchmark_reporter import BenchmarkReporter
from agent_eval.framework_adapter import FrameworkTrajectory
from agent_eval.statistics_aggregator import BenchmarkStatisticsAggregator


def test_statistics_aggregator_level_progression_and_deltas() -> None:
    # Construct synthetic trajectories:
    # adder_8bit: solved at L0
    # counter_12: solved at L1
    # fsm: solved at L2
    # asyn_fifo: failed
    trajectories = [
        FrameworkTrajectory(
            design_name="adder_8bit",
            category="Arithmetic",
            subcategory="Adder",
            solved=True,
            solved_level="L0_ZERO_SHOT",
            final_code="",
            total_prompt_tokens=100,
            total_completion_tokens=50,
            total_elapsed_sec=2.0,
        ),
        FrameworkTrajectory(
            design_name="counter_12",
            category="Control",
            subcategory="Counter",
            solved=True,
            solved_level="L1_LINT",
            final_code="",
            total_prompt_tokens=200,
            total_completion_tokens=100,
            total_elapsed_sec=3.0,
        ),
        FrameworkTrajectory(
            design_name="fsm",
            category="Control",
            subcategory="FSM",
            solved=True,
            solved_level="L2_SIM",
            final_code="",
            total_prompt_tokens=300,
            total_completion_tokens=150,
            total_elapsed_sec=4.0,
        ),
        FrameworkTrajectory(
            design_name="asyn_fifo",
            category="Memory",
            subcategory="FIFO",
            solved=False,
            solved_level=None,
            final_code="",
            failure_reason="Functional mismatch",
            total_prompt_tokens=400,
            total_completion_tokens=200,
            total_elapsed_sec=5.0,
        ),
    ]

    report = BenchmarkStatisticsAggregator.aggregate(trajectories)
    assert report.total_designs == 4
    assert report.total_solved == 3
    assert report.overall_solve_rate == 0.75

    # Level counts
    assert report.level_counts["L0_ZERO_SHOT"] == 1
    assert report.level_counts["L1_LINT"] == 1
    assert report.level_counts["L2_SIM"] == 1

    # Cumulative rates
    assert report.cumulative_pass_rates["L0_ZERO_SHOT"] == 0.25
    assert report.cumulative_pass_rates["L1_LINT"] == 0.50
    assert report.cumulative_pass_rates["L2_SIM"] == 0.75

    # Recovery deltas
    # Failed L0 = 3. 1 was recovered in L1 -> delta_l0_to_l1 = 1/3 = 33.3%
    assert abs(report.recovery_deltas["delta_l0_to_l1 (Lint Recovery)"] - (1 / 3)) < 1e-4

    # Terminal rendering check
    terminal_str = BenchmarkReporter.render_terminal_summary(report, "reflection_agent_fw", "gpt-4o")
    assert "RTLLM v2.1 BENCHMARK REPORT" in terminal_str
    assert "CIRCUIT COMPLEXITY TIERS" in terminal_str

    # File exports check
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_file = Path(tmp_dir) / "report.md"
        json_file = Path(tmp_dir) / "summary.json"
        csv_file = Path(tmp_dir) / "designs.csv"

        BenchmarkReporter.write_markdown_report(report, trajectories, md_file, "reflection_agent_fw", "gpt-4o")
        BenchmarkReporter.write_csv_and_json(report, trajectories, json_file, csv_file)

        assert md_file.is_file()
        assert json_file.is_file()
        assert csv_file.is_file()
        assert "Tier 1: Combinational Arithmetic" in md_file.read_text(encoding="utf-8")
