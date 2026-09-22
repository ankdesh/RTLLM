"""Batch benchmark execution engine running agent frameworks against RTLLM designs."""

import concurrent.futures
import logging
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

from agent_eval.checkpoint_store import BenchmarkCheckpointStore
from agent_eval.framework_adapter import BaseAgentAdapter, FrameworkTrajectory
from agent_eval.models import DesignMeta
from agent_eval.statistics_aggregator import (
    BenchmarkReportData,
    BenchmarkStatisticsAggregator,
    TIER_MAPPING,
)

logger = logging.getLogger(__name__)


class AgentBenchmarkRunner:
    """Coordinates batch evaluation of RTLLM designs across concurrent worker threads."""

    def __init__(
        self,
        adapter: BaseAgentAdapter,
        checkpoint_store: BenchmarkCheckpointStore,
        max_rounds: int = 5,
        timeout: float = 10.0,
        workers: int = 4,
    ) -> None:
        """Initialize runner with adapter, storage, and execution parameters."""
        self.adapter = adapter
        self.checkpoint_store = checkpoint_store
        self.max_rounds = max_rounds
        self.timeout = timeout
        self.workers = max(1, workers)

    def run_benchmark(
        self,
        designs: List[DesignMeta],
        resume: bool = True,
        tier_filter: Optional[int] = None,
        design_filter: Optional[List[str]] = None,
    ) -> BenchmarkReportData:
        """Run benchmark evaluation over selected designs and aggregate results."""
        # 1. Filter designs
        target_designs: List[DesignMeta] = []
        for d in designs:
            if design_filter and d.design_name not in design_filter:
                continue
            if tier_filter is not None and TIER_MAPPING.get(d.design_name, 1) != tier_filter:
                continue
            target_designs.append(d)

        if not target_designs:
            logger.warning("No designs matched the specified filter criteria.")
            return BenchmarkStatisticsAggregator.aggregate([])

        # 2. Check existing checkpoints if resume enabled
        completed_map: Dict[str, FrameworkTrajectory] = {}
        if resume:
            completed_map = self.checkpoint_store.load_completed_trajectories()
            if completed_map:
                logger.info("Resuming run: found %d already completed designs.", len(completed_map))

        remaining_designs: List[DesignMeta] = [
            d for d in target_designs if d.design_name not in completed_map
        ]
        logger.info(
            "Executing benchmark: %d total target designs, %d remaining to solve using %d workers.",
            len(target_designs),
            len(remaining_designs),
            self.workers,
        )

        trajectories: List[FrameworkTrajectory] = list(completed_map.values())

        # 3. Concurrent execution over remaining designs
        if remaining_designs:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_design = {
                    executor.submit(
                        self.adapter.solve,
                        design,
                        self.max_rounds,
                        self.timeout,
                    ): design
                    for design in remaining_designs
                }

                with tqdm(total=len(remaining_designs), desc="Evaluating designs") as pbar:
                    for future in concurrent.futures.as_completed(future_to_design):
                        design = future_to_design[future]
                        try:
                            traj = future.result()
                            self.checkpoint_store.save_trajectory(traj)
                            trajectories.append(traj)
                            status_str = f"SOLVED ({traj.solved_level})" if traj.solved else "FAILED"
                            pbar.set_postfix_str(f"{design.design_name}: {status_str}")
                        except Exception as e:
                            logger.error("Error evaluating design %s: %s", design.design_name, str(e))
                            failed_traj = FrameworkTrajectory(
                                design_name=design.design_name,
                                category=design.category,
                                subcategory=design.subcategory,
                                solved=False,
                                solved_level=None,
                                final_code="",
                                failure_reason=f"Runner execution exception: {str(e)}",
                            )
                            self.checkpoint_store.save_trajectory(failed_traj)
                            trajectories.append(failed_traj)
                        finally:
                            pbar.update(1)

        # 4. Aggregate analytics across all target designs
        return BenchmarkStatisticsAggregator.aggregate(trajectories)
