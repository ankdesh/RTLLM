"""Main CLI entry point for executing RTLLM multi-framework benchmarks."""

import argparse
import datetime
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Ensure repository root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent_eval.adapters.reflection_fw_adapter import ReflectionFWAdapter
from agent_eval.adapters.zero_shot_adapter import ZeroShotBaselineAdapter
from agent_eval.agent_benchmark_runner import AgentBenchmarkRunner
from agent_eval.benchmark_reporter import BenchmarkReporter
from agent_eval.checkpoint_store import BenchmarkCheckpointStore
from agent_eval.dataset_exporter import DatasetExporter
from agent_eval.framework_adapter import BaseAgentAdapter
from reflection_agent_fw.llm_client import OpenAICompatibleClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agent_eval")


def parse_args() -> argparse.ArgumentParser:
    """Build command line arguments parser."""
    parser = argparse.ArgumentParser(
        prog="run_framework_eval",
        description="Benchmark agent frameworks (e.g. reflection_agent_fw, zero_shot) on RTLLM v2.1.",
    )
    parser.add_argument(
        "--framework",
        type=str,
        default="reflection_agent_fw",
        choices=["reflection_agent_fw", "zero_shot"],
        help="Agent framework to benchmark.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="OpenAI-compatible model identifier.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="OpenAI-compatible base API URL (e.g. http://localhost:8000/v1 for vLLM/Ollama).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key (defaults to OPENAI_API_KEY environment variable).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent worker threads for solving designs.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=5,
        help="Maximum bounded reflection iterations per problem.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout in seconds for each simulation step.",
    )
    parser.add_argument(
        "--tier",
        type=int,
        default=None,
        choices=[1, 2, 3, 4],
        help="Filter designs by circuit complexity tier (1 to 4).",
    )
    parser.add_argument(
        "--designs",
        type=str,
        default=None,
        help="Comma-separated design names to benchmark (e.g. 'adder_8bit,counter_12').",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs"),
        help="Base directory to store benchmark runs.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom run ID directory name.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume; overwrite/restart existing checkpoints.",
    )
    return parser


def main() -> int:
    """Execute RTLLM benchmark run with selected framework and configuration."""
    parser = parse_args()
    args = parser.parse_args()

    # 1. Setup Run Directory & Storage
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_model_name = args.model.replace("/", "_").replace(":", "_")
    run_id = args.run_id or f"{args.framework}_{clean_model_name}_{timestamp}"
    run_dir = args.output_dir / run_id
    checkpoint_store = BenchmarkCheckpointStore(run_dir)

    # 2. Record Manifest
    manifest_data = {
        "run_id": run_id,
        "framework": args.framework,
        "model": args.model,
        "base_url": args.base_url or os.environ.get("OPENAI_BASE_URL", "default"),
        "max_rounds": args.max_rounds,
        "workers": args.workers,
        "timeout": args.timeout,
        "tier": args.tier,
        "designs_filter": args.designs,
        "start_time": datetime.datetime.now().isoformat(),
    }
    checkpoint_store.write_manifest(manifest_data)

    # 3. Discover RTLLM Benchmark Designs
    repo_root = Path(__file__).resolve().parent.parent
    exporter = DatasetExporter(repo_root)
    all_designs = exporter.discover_designs()
    logger.info("Discovered %d total designs in RTLLM v2.1 benchmark.", len(all_designs))

    # Parse design filter
    filter_list: Optional[List[str]] = None
    if args.designs:
        filter_list = [d.strip() for d in args.designs.split(",") if d.strip()]

    # 4. Instantiate Framework Adapter
    llm_client = OpenAICompatibleClient(
        model=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
    )

    adapter: BaseAgentAdapter
    if args.framework == "reflection_agent_fw":
        adapter = ReflectionFWAdapter(llm_client=llm_client, repo_root=repo_root)
    elif args.framework == "zero_shot":
        adapter = ZeroShotBaselineAdapter(llm_client=llm_client, repo_root=repo_root)
    else:
        logger.error("Unsupported framework: %s", args.framework)
        return 1

    # 5. Run Benchmark
    runner = AgentBenchmarkRunner(
        adapter=adapter,
        checkpoint_store=checkpoint_store,
        max_rounds=args.max_rounds,
        timeout=args.timeout,
        workers=args.workers,
    )

    report_data = runner.run_benchmark(
        designs=all_designs,
        resume=not args.no_resume,
        tier_filter=args.tier,
        design_filter=filter_list,
    )

    # 6. Generate and Save Reports
    terminal_output = BenchmarkReporter.render_terminal_summary(
        data=report_data,
        framework_name=args.framework,
        model_name=args.model,
    )
    print("\n" + terminal_output + "\n")

    # Load all completed trajectories for file exports
    completed_trajectories = list(checkpoint_store.load_completed_trajectories().values())
    md_path = run_dir / "benchmark_report.md"
    json_path = run_dir / "summary.json"
    csv_path = run_dir / "designs.csv"

    BenchmarkReporter.write_markdown_report(
        data=report_data,
        trajectories=completed_trajectories,
        output_path=md_path,
        framework_name=args.framework,
        model_name=args.model,
    )
    BenchmarkReporter.write_csv_and_json(
        data=report_data,
        trajectories=completed_trajectories,
        json_path=json_path,
        csv_path=csv_path,
    )

    logger.info("Saved benchmark reports to directory: %s", run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
