"""CLI utility to generate interactive HTML visualizations from RTLLM benchmark runs."""

import argparse
import logging
import sys
from pathlib import Path

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent_eval.pipeline_visualizer import PipelineVisualizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("visualizer")


def parse_args() -> argparse.ArgumentParser:
    """Build CLI arguments parser."""
    parser = argparse.ArgumentParser(
        prog="visualize_pipeline",
        description="Generate interactive HTML visualization of RTL reflection pipeline execution.",
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a benchmark run directory (e.g. runs/run_xxx) or checkpoints.jsonl file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output filepath for HTML visualization (defaults to <run_dir>/pipeline_visualization.html).",
    )
    return parser


def main() -> int:
    """CLI execution entrypoint."""
    parser = parse_args()
    args = parser.parse_args()

    input_path: Path = args.input_path.resolve()
    if not input_path.exists():
        logger.error("Input path does not exist: %s", input_path)
        return 1

    if input_path.is_dir():
        run_data = PipelineVisualizer.load_from_run_dir(input_path)
        default_out = input_path / "pipeline_visualization.html"
    elif input_path.is_file():
        if input_path.name.endswith(".jsonl"):
            designs = PipelineVisualizer.load_from_checkpoints_jsonl(input_path)
            run_data = {"manifest": {"framework": "RTLLM Run", "model": "Extracted"}, "designs": designs}
            default_out = input_path.parent / f"{input_path.stem}_viz.html"
        else:
            # Single trajectory json
            import json
            data = json.loads(input_path.read_text(encoding="utf-8"))
            data["tier"] = PipelineVisualizer.TIER_MAPPING.get(data.get("design_name", ""), 1)
            run_data = {"manifest": {"framework": "Single Problem Run"}, "designs": [data]}
            default_out = input_path.parent / f"{input_path.stem}_viz.html"
    else:
        logger.error("Unsupported input path: %s", input_path)
        return 1

    output_path = (args.output or default_out).resolve()
    generated_file = PipelineVisualizer.generate_html_report(run_data, output_path)

    logger.info("Successfully generated interactive pipeline visualization at: %s", generated_file)
    print(f"\n✨ Interactive Pipeline Visualization generated:\nfile://{generated_file}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
