"""Atomic checkpoint storage and artifact persistence for benchmark evaluation runs."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_eval.framework_adapter import FrameworkTrajectory

logger = logging.getLogger(__name__)


class BenchmarkCheckpointStore:
    """Manages disk-based persistence and resumption for long-running benchmark jobs."""

    def __init__(self, run_dir: Path) -> None:
        """Initialize store pointing to a dedicated run directory."""
        self.run_dir = run_dir.resolve()
        self.code_dir = self.run_dir / "code"
        self.checkpoints_file = self.run_dir / "checkpoints.jsonl"
        self.manifest_file = self.run_dir / "manifest.json"

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.code_dir.mkdir(parents=True, exist_ok=True)

    def write_manifest(self, manifest_data: Dict[str, Any]) -> None:
        """Persist benchmark execution metadata to manifest.json."""
        self.manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    def save_trajectory(self, trajectory: FrameworkTrajectory) -> None:
        """Atomically persist a completed design trajectory and its RTL code to disk."""
        # 1. Save final RTL code artifact if present
        if trajectory.final_code:
            code_path = self.code_dir / f"{trajectory.design_name}.v"
            code_path.write_text(trajectory.final_code, encoding="utf-8")

        # 2. Append trajectory entry to JSONL
        line = json.dumps(trajectory.to_dict())
        with self.checkpoints_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load_completed_trajectories(self) -> Dict[str, FrameworkTrajectory]:
        """Load previously completed trajectories from checkpoints.jsonl for resumption."""
        completed: Dict[str, FrameworkTrajectory] = {}
        if not self.checkpoints_file.is_file():
            return completed

        with self.checkpoints_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    traj = FrameworkTrajectory(
                        design_name=data["design_name"],
                        category=data["category"],
                        subcategory=data["subcategory"],
                        solved=data["solved"],
                        solved_level=data.get("solved_level"),
                        final_code=data.get("final_code", ""),
                        steps=data.get("steps", []),
                        total_prompt_tokens=data.get("total_prompt_tokens", 0),
                        total_completion_tokens=data.get("total_completion_tokens", 0),
                        total_elapsed_sec=data.get("total_elapsed_sec", 0.0),
                        failure_reason=data.get("failure_reason"),
                    )
                    completed[traj.design_name] = traj
                except Exception as e:
                    logger.warning("Skipping corrupted checkpoint line: %s", str(e))

        return completed
