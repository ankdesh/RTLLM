"""Evaluation runner coordinating multi-threaded evaluation across RTLLM designs and trials."""

import concurrent.futures
import json
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from agent_eval.dataset_exporter import DatasetExporter
from agent_eval.metrics_calculator import MetricsCalculator
from agent_eval.models import BenchmarkSummary, DesignMeta, SimResult
from agent_eval.simulator_interface import DEFAULT_SIMULATION_TIMEOUT_SEC, BaseSimulator

logger = logging.getLogger(__name__)

# Constants
DEFAULT_NUM_THREADS: int = min(8, max(1, os.cpu_count() or 4))


def _run_single_task(
    simulator: BaseSimulator,
    meta: DesignMeta,
    trial_name: str,
    rtl_path: Path,
    tb_path: Path,
    timeout: float,
    lint_only: bool,
) -> SimResult:
    """Worker task to simulate or lint a single design trial."""
    if lint_only:
        return simulator.lint(rtl_path=rtl_path, design_name=meta.design_name)
    return simulator.simulate(
        rtl_path=rtl_path,
        tb_path=tb_path,
        design_name=meta.design_name,
        trial_name=trial_name,
        timeout=timeout,
    )


class EvaluationRunner:
    """Manages batch simulation execution, worker threads, and result collation."""

    def __init__(
        self,
        simulator: BaseSimulator,
        root_dir: Optional[Path] = None,
        timeout: float = DEFAULT_SIMULATION_TIMEOUT_SEC,
        threads: int = DEFAULT_NUM_THREADS,
    ) -> None:
        """Initialize evaluation runner.

        Args:
            simulator: Simulator backend instance.
            root_dir: Base RTLLM repository directory.
            timeout: Per-test timeout in seconds.
            threads: Number of parallel execution workers.
        """
        self._simulator = simulator
        self._root_dir = (
            Path(root_dir).resolve()
            if root_dir
            else Path(__file__).resolve().parent.parent
        )
        self._timeout = timeout
        self._threads = threads
        self._exporter = DatasetExporter(root_dir=self._root_dir)
        self._metrics_calc = MetricsCalculator()

    def discover_trials(self, model_dir: Path) -> List[Tuple[str, Path]]:
        """Identify trial directories inside the model output directory.

        Detects patterns like 't1', 't2', 't3' or treats model_dir itself as a single trial.

        Args:
            model_dir: Path to directory containing generated Verilog files.

        Returns:
            List of (trial_name, trial_path) tuples.
        """
        model_dir = Path(model_dir).resolve()
        if not model_dir.is_dir():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")

        trial_subdirs = sorted(
            [d for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("t") and d.name[1:].isdigit()],
            key=lambda d: int(d.name[1:]),
        )

        if trial_subdirs:
            return [(d.name, d) for d in trial_subdirs]

        # Single directory without t1..tN subdirectories
        return [("t1", model_dir)]

    def evaluate(
        self,
        model_dir: Path,
        lint_only: bool = False,
        progress_callback: Optional[Callable[[SimResult], None]] = None,
    ) -> BenchmarkSummary:
        """Run batch evaluation over all RTLLM designs across discovered trials.

        Args:
            model_dir: Path to model-generated Verilog directory.
            lint_only: If True, execute static linting only.
            progress_callback: Optional callback invoked after each trial completes.

        Returns:
            BenchmarkSummary containing comprehensive performance metrics.
        """
        catalog = self._exporter.discover_designs()
        trials = self.discover_trials(model_dir)

        logger.info(
            "Starting evaluation with %s: %d designs across %d trials (%d workers)",
            self._simulator.name,
            len(catalog),
            len(trials),
            self._threads,
        )

        results_by_design: Dict[str, List[SimResult]] = {d.design_name: [] for d in catalog}

        # Build execution tasks
        tasks = []
        for meta in catalog:
            tb_abs = self._root_dir / meta.testbench_path
            for trial_name, trial_path in trials:
                rtl_abs = trial_path / meta.target_filename
                tasks.append((meta, trial_name, rtl_abs, tb_abs))

        with concurrent.futures.ThreadPoolExecutor(max_workers=self._threads) as executor:
            future_to_info = {}
            for meta, trial_name, rtl_abs, tb_abs in tasks:
                if not rtl_abs.is_file():
                    # Missing generated file counts as immediate failure
                    res = SimResult(
                        design_name=meta.design_name,
                        trial_name=trial_name,
                        syntax_ok=False,
                        func_ok=False,
                        timed_out=False,
                        return_code=-1,
                        compile_output=f"Target file not found: {rtl_abs.name}",
                        sim_output="",
                        elapsed_sec=0.0,
                    )
                    results_by_design[meta.design_name].append(res)
                    if progress_callback:
                        progress_callback(res)
                    continue

                future = executor.submit(
                    _run_single_task,
                    self._simulator,
                    meta,
                    trial_name,
                    rtl_abs,
                    tb_abs,
                    self._timeout,
                    lint_only,
                )
                future_to_info[future] = (meta.design_name, trial_name)

            for future in concurrent.futures.as_completed(future_to_info):
                d_name, t_name = future_to_info[future]
                try:
                    result = future.result()
                except Exception as exc:
                    logger.error("Error evaluating %s on %s: %s", d_name, t_name, exc)
                    result = SimResult(
                        design_name=d_name,
                        trial_name=t_name,
                        syntax_ok=False,
                        func_ok=False,
                        timed_out=False,
                        return_code=-1,
                        compile_output=str(exc),
                        sim_output="",
                        elapsed_sec=0.0,
                    )
                results_by_design[d_name].append(result)
                if progress_callback:
                    progress_callback(result)

        # Compute summary
        summary = self._metrics_calc.compute_benchmark_summary(
            simulator_name=self._simulator.name,
            catalog=catalog,
            results=results_by_design,
        )
        return summary

    def print_summary_table(self, summary: BenchmarkSummary) -> None:
        """Render a formatted ANSI table of benchmark metrics to stdout."""
        border = "=" * 78
        print("\n" + border)
        print(f" RTLLM v2.1 BENCHMARK REPORT — Simulator: {summary.simulator.upper()}")
        print(border)
        print(f" Total Designs: {summary.total_designs:<6} Total Trials Evaluated: {summary.total_trials}")
        print(
            f" Syntax Pass  : {summary.syntax_success_designs}/{summary.total_designs} "
            f"({summary.overall_syntax_pass_rate * 100:.1f}%)"
        )
        print(
            f" Functional   : {summary.func_success_designs}/{summary.total_designs} "
            f"({summary.overall_func_pass_rate * 100:.1f}%)"
        )

        if summary.pass_at_k:
            print("\n Pass@k Metrics:")
            for k_name, val in summary.pass_at_k.items():
                print(f"   {k_name:<10}: {val * 100:.2f}%")

        print("\n Category Breakdown:")
        print(f" {'Category':<16} | {'Designs':<8} | {'Syntax %':<10} | {'Func %':<10}")
        print("-" * 52)
        for cat, metrics in summary.category_breakdown.items():
            tot = int(metrics["total_designs"])
            syn_pct = metrics["syntax_pass_rate"] * 100
            fn_pct = metrics["func_pass_rate"] * 100
            print(f" {cat:<16} | {tot:<8} | {syn_pct:>7.1f}%   | {fn_pct:>7.1f}%")
        print(border + "\n")
