"""Cross-framework and cross-model comparison utility for RTLLM benchmark runs."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class FrameworkComparator:
    """Compiles and compares benchmark statistics across multiple runs, frameworks, and models."""

    @classmethod
    def load_run_data(cls, run_dir: Path) -> Dict[str, Any]:
        """Load manifest and summary analytics from a run directory."""
        summary_file = run_dir / "summary.json"
        manifest_file = run_dir / "manifest.json"

        if not summary_file.is_file():
            raise FileNotFoundError(f"Missing summary.json in {run_dir}")

        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        manifest = {}
        if manifest_file.is_file():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        return {
            "run_dir": str(run_dir.name),
            "framework": manifest.get("framework", "unknown"),
            "model": manifest.get("model", "unknown"),
            "summary": summary,
        }

    @classmethod
    def generate_markdown_comparison(cls, runs_data: List[Dict[str, Any]]) -> str:
        """Generate side-by-side comparison Markdown table."""
        lines = [
            "# RTLLM Cross-Framework & Cross-Model Comparison Report",
            "",
            "## 1. Overall Performance & Reflection Progression",
            "",
            "| Run Directory | Framework | Model | Solved / Total | Pass Rate | L0 Pass | L1 Pass | L2 Pass | L3+ Pass | Avg Tokens/Solve |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for r in runs_data:
            s = r["summary"]
            cum = s.get("cumulative_pass_rates", {})
            l0_pct = cum.get("L0_ZERO_SHOT", 0.0) * 100
            l1_pct = cum.get("L1_LINT", 0.0) * 100
            l2_pct = cum.get("L2_SIM", 0.0) * 100
            l3_pct = cum.get("L3_MULTI_TURN", 0.0) * 100
            overall_pct = s.get("overall_solve_rate", 0.0) * 100

            lines.append(
                f"| `{r['run_dir']}` | `{r['framework']}` | `{r['model']}` | "
                f"{s.get('total_solved', 0)} / {s.get('total_designs', 0)} | "
                f"**{overall_pct:.1f}%** | {l0_pct:.1f}% | {l1_pct:.1f}% | {l2_pct:.1f}% | {l3_pct:.1f}% | "
                f"{s.get('avg_tokens_per_solve', 0):.0f} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 2. Circuit Complexity Tier Breakdown",
            "",
            "| Run Directory | Framework | Tier 1 (Comb) | Tier 2 (Seq) | Tier 3 (FSM) | Tier 4 (Subsystems) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for r in runs_data:
            s = r["summary"]
            tiers = s.get("tier_stats", {})
            t1 = tiers.get("1", {}).get("solve_rate", 0.0) * 100
            t2 = tiers.get("2", {}).get("solve_rate", 0.0) * 100
            t3 = tiers.get("3", {}).get("solve_rate", 0.0) * 100
            t4 = tiers.get("4", {}).get("solve_rate", 0.0) * 100
            lines.append(
                f"| `{r['run_dir']}` | `{r['framework']}` | {t1:.1f}% | {t2:.1f}% | {t3:.1f}% | {t4:.1f}% |"
            )

        return "\n".join(lines)


def main() -> int:
    """CLI utility to compare multiple run directories."""
    parser = argparse.ArgumentParser(description="Compare multiple RTLLM benchmark runs.")
    parser.add_argument("run_dirs", nargs="+", type=Path, help="Paths to run directories to compare.")
    parser.add_argument("--output", type=Path, default=None, help="Path to write output markdown comparison.")
    args = parser.parse_args()

    runs_data = []
    for rdir in args.run_dirs:
        try:
            data = FrameworkComparator.load_run_data(rdir)
            runs_data.append(data)
        except Exception as e:
            logger.error("Failed to load run from %s: %s", rdir, str(e))

    if not runs_data:
        print("No valid runs loaded.")
        return 1

    report = FrameworkComparator.generate_markdown_comparison(runs_data)
    print("\n" + report + "\n")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Saved comparison report to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
