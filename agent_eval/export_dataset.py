"""CLI script for exporting RTLLM v2.1 benchmark datasets."""

import argparse
import logging
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent_eval.dataset_exporter import DatasetExporter


def main() -> int:
    """Run dataset export CLI."""
    parser = argparse.ArgumentParser(
        description="Extract and export RTLLM v2.1 benchmark specifications into JSON and JSONL datasets."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Target directory to write rtllm_v2_1_dataset.json and .jsonl (default: current directory).",
    )
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=None,
        help="Base directory of RTLLM repository (default: repository root).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    exporter = DatasetExporter(root_dir=args.root_dir)
    json_path, jsonl_path = exporter.export_all(output_dir=args.output_dir)

    print(f"Successfully generated RTLLM v2.1 datasets:")
    print(f"  JSON : {json_path}")
    print(f"  JSONL: {jsonl_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
