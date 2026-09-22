"""Reporting generator for benchmark summary tables, markdown reports, and export formats."""

import csv
import json
from pathlib import Path
from typing import List

from agent_eval.framework_adapter import FrameworkTrajectory
from agent_eval.statistics_aggregator import BenchmarkReportData, TIER_MAPPING


class BenchmarkReporter:
    """Renders formatted benchmark reports across ANSI terminal, Markdown, JSON, and CSV."""

    @classmethod
    def render_terminal_summary(cls, data: BenchmarkReportData, framework_name: str, model_name: str) -> str:
        """Render ANSI formatted terminal summary table."""
        lines = []
        lines.append("=" * 78)
        lines.append(f"  RTLLM v2.1 BENCHMARK REPORT: {framework_name} ({model_name})")
        lines.append("=" * 78)
        lines.append(f"  Overall Result: {data.total_solved}/{data.total_designs} Solved ({data.overall_solve_rate * 100:.1f}%)")
        lines.append(f"  Total Tokens:   {data.total_tokens:,} (Prompt: {data.total_prompt_tokens:,}, Comp: {data.total_completion_tokens:,})")
        lines.append(f"  Total Runtime:  {data.total_elapsed_sec:.1f}s")
        lines.append("-" * 78)
        lines.append(f"  {'Stage / Level':<24} | {'Solved':<8} | {'Cumulative Pass':<18} | {'Recovery Delta'}")
        lines.append("-" * 78)

        # Level progression rows
        deltas = list(data.recovery_deltas.values())
        delta_labels = ["-", f"{deltas[0]*100:.1f}%", f"{deltas[1]*100:.1f}%", f"{deltas[2]*100:.1f}%", "-", "-"]
        idx = 0
        for lvl, cnt in data.level_counts.items():
            cum_rate = data.cumulative_pass_rates.get(lvl, 0.0) * 100
            d_str = delta_labels[idx] if idx < len(delta_labels) else "-"
            lines.append(f"  {lvl:<24} | {cnt:<8} | {cum_rate:>15.1f}% | {d_str}")
            idx += 1

        lines.append("-" * 78)
        lines.append("  CIRCUIT COMPLEXITY TIERS:")
        lines.append(f"  {'Tier':<35} | {'Solved / Total':<16} | {'Pass Rate':<10} | {'Avg Rounds'}")
        lines.append("-" * 78)
        for t_id, stats in sorted(data.tier_stats.items()):
            lines.append(
                f"  {stats.tier_name:<35} | {stats.solved_designs:>3}/{stats.total_designs:<12} | "
                f"{stats.solve_rate * 100:>8.1f}% | {stats.avg_rounds_to_solve:>8.1f}"
            )

        lines.append("-" * 78)
        lines.append("  FAILURE CLASSIFICATION:")
        for fail_type, count in data.failure_breakdown.items():
            lines.append(f"    - {fail_type:<32}: {count}")
        lines.append("=" * 78)
        return "\n".join(lines)

    @classmethod
    def write_markdown_report(
        cls,
        data: BenchmarkReportData,
        trajectories: List[FrameworkTrajectory],
        output_path: Path,
        framework_name: str,
        model_name: str,
    ) -> None:
        """Write detailed markdown report to file."""
        lines = [
            f"# RTLLM v2.1 Benchmark Evaluation Report",
            f"",
            f"- **Framework**: `{framework_name}`",
            f"- **Model**: `{model_name}`",
            f"- **Total Solved**: **{data.total_solved} / {data.total_designs} ({data.overall_solve_rate * 100:.1f}%)**",
            f"- **Total Compute**: {data.total_tokens:,} tokens ({data.avg_tokens_per_design:.0f} tokens/design)",
            f"- **Execution Time**: {data.total_elapsed_sec:.2f} seconds",
            f"",
            f"---",
            f"",
            f"## 1. Level-by-Level Solve Progression & Reflection Gains",
            f"",
            f"| Reflection Level | Solved at Level | Cumulative Pass Rate | Recovery Delta (\\$\\Delta\\$) |",
            f"| :--- | :--- | :--- | :--- |",
        ]

        delta_keys = list(data.recovery_deltas.keys())
        d_vals = [
            "-",
            f"{data.recovery_deltas.get(delta_keys[0], 0.0) * 100:.1f}%",
            f"{data.recovery_deltas.get(delta_keys[1], 0.0) * 100:.1f}%",
            f"{data.recovery_deltas.get(delta_keys[2], 0.0) * 100:.1f}%",
            "-",
            "-",
        ]

        idx = 0
        for lvl, cnt in data.level_counts.items():
            cum_pct = data.cumulative_pass_rates.get(lvl, 0.0) * 100
            d_val = d_vals[idx] if idx < len(d_vals) else "-"
            lines.append(f"| `{lvl}` | {cnt} | **{cum_pct:.1f}%** | {d_val} |")
            idx += 1

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 2. Circuit Complexity Tier Performance",
            f"",
            f"| Complexity Tier | Solved / Total | Pass Rate | Avg Rounds to Solve |",
            f"| :--- | :--- | :--- | :--- |",
        ])

        for t_id, stats in sorted(data.tier_stats.items()):
            lines.append(
                f"| **{stats.tier_name}** | {stats.solved_designs} / {stats.total_designs} | "
                f"**{stats.solve_rate * 100:.1f}%** | {stats.avg_rounds_to_solve:.1f} |"
            )

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 3. Failure Taxonomy",
            f"",
            f"| Failure Category | Count |",
            f"| :--- | :--- |",
        ])
        for fail_type, count in data.failure_breakdown.items():
            lines.append(f"| {fail_type} | {count} |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 4. Per-Design Trajectory Results",
            f"",
            f"| Design Name | Tier | Solved | Solved Level | Steps Taken | Tokens | Time (s) |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for t in sorted(trajectories, key=lambda x: x.design_name):
            tier = TIER_MAPPING.get(t.design_name, 1)
            status_icon = "PASS" if t.solved else "FAIL"
            lvl_str = f"`{t.solved_level}`" if t.solved_level else "-"
            tok_sum = t.total_prompt_tokens + t.total_completion_tokens
            lines.append(
                f"| `{t.design_name}` | Tier {tier} | {status_icon} | {lvl_str} | "
                f"{len(t.steps)} | {tok_sum:,} | {t.total_elapsed_sec:.2f} |"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")

    @classmethod
    def write_csv_and_json(
        cls,
        data: BenchmarkReportData,
        trajectories: List[FrameworkTrajectory],
        json_path: Path,
        csv_path: Path,
    ) -> None:
        """Export raw analytics to JSON and per-design results to CSV."""
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(data.to_dict(), indent=2), encoding="utf-8")

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "design_name",
                "category",
                "subcategory",
                "tier",
                "solved",
                "solved_level",
                "steps_count",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "elapsed_sec",
                "failure_reason",
            ])
            for t in trajectories:
                tier = TIER_MAPPING.get(t.design_name, 1)
                writer.writerow([
                    t.design_name,
                    t.category,
                    t.subcategory,
                    tier,
                    t.solved,
                    t.solved_level or "",
                    len(t.steps),
                    t.total_prompt_tokens,
                    t.total_completion_tokens,
                    t.total_prompt_tokens + t.total_completion_tokens,
                    round(t.total_elapsed_sec, 4),
                    t.failure_reason or "",
                ])
