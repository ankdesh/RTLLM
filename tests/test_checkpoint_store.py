"""Unit tests for BenchmarkCheckpointStore."""

import tempfile
from pathlib import Path

from agent_eval.checkpoint_store import BenchmarkCheckpointStore
from agent_eval.framework_adapter import FrameworkTrajectory


def test_checkpoint_store_atomic_save_and_resume() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        run_dir = Path(tmp_dir) / "run_test"
        store = BenchmarkCheckpointStore(run_dir)

        store.write_manifest({"framework": "reflection_agent_fw", "model": "gpt-4o"})
        assert store.manifest_file.is_file()

        traj1 = FrameworkTrajectory(
            design_name="adder_8bit",
            category="Arithmetic",
            subcategory="Adder",
            solved=True,
            solved_level="L0_ZERO_SHOT",
            final_code="module adder_8bit; endmodule",
            total_prompt_tokens=100,
            total_completion_tokens=50,
            total_elapsed_sec=1.2,
        )
        store.save_trajectory(traj1)

        # Verify RTL file was saved
        code_file = store.code_dir / "adder_8bit.v"
        assert code_file.is_file()
        assert "module adder_8bit" in code_file.read_text(encoding="utf-8")

        # Verify resume loading
        completed = store.load_completed_trajectories()
        assert len(completed) == 1
        assert "adder_8bit" in completed
        assert completed["adder_8bit"].solved is True
        assert completed["adder_8bit"].solved_level == "L0_ZERO_SHOT"
