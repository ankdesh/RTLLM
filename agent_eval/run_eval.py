"""CLI entry point for running RTLLM v2.1 agentic evaluations."""

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent_eval.eval_runner import EvaluationRunner
from agent_eval.iverilog_simulator import IverilogSimulator
from agent_eval.simulator_interface import BaseSimulator
from agent_eval.verilator_simulator import VerilatorSimulator

logger = logging.getLogger(__name__)


def main() -> int:
    """Execute evaluation CLI."""
    parser = argparse.ArgumentParser(
        description="Modernized, multi-threaded evaluation engine for RTLLM v2.1 benchmark."
    )
    parser.add_argument(
        "--model-dir",
        "-m",
        type=Path,
        required=True,
        help="Path to directory containing generated Verilog files (e.g., _chatgpt4 or custom folder).",
    )
    parser.add_argument(
        "--simulator",
        "-s",
        choices=["iverilog", "verilator"],
        default="iverilog",
        help="Simulation backend to employ (default: iverilog).",
    )
    parser.add_argument(
        "--sim-bin",
        type=Path,
        default=None,
        help="Custom directory containing simulator executables.",
    )
    parser.add_argument(
        "--threads",
        "-t",
        type=int,
        default=None,
        help="Number of concurrent worker threads (default: CPU count).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-test execution timeout in seconds (default: 10.0).",
    )
    parser.add_argument(
        "--lint-only",
        action="store_true",
        help="Run static linting checks only without executing functional testbenches.",
    )
    parser.add_argument(
        "--output-json",
        "-o",
        type=Path,
        default=Path("eval_results.json"),
        help="Path to save detailed JSON evaluation report (default: eval_results.json).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging output.",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    simulator: BaseSimulator
    if args.simulator == "iverilog":
        simulator = IverilogSimulator(bin_dir=args.sim_bin)
    else:
        simulator = VerilatorSimulator(bin_dir=args.sim_bin)

    if not simulator.check_available():
        print(
            f"Error: Simulator backend '{args.simulator}' executables were not found.\n"
            f"Please verify installation or pass --sim-bin /path/to/bin.",
            file=sys.stderr,
        )
        return 1

    kwargs = {"simulator": simulator, "timeout": args.timeout}
    if args.threads:
        kwargs["threads"] = args.threads

    runner = EvaluationRunner(**kwargs)
    summary = runner.evaluate(model_dir=args.model_dir, lint_only=args.lint_only)

    runner.print_summary_table(summary)

    if args.output_json:
        out_path = Path(args.output_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)
        print(f"Detailed JSON results exported to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
