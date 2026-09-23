"""Unit tests for PipelineVisualizer and HTML generation."""

import json
import tempfile
from pathlib import Path

from agent_eval.pipeline_visualizer import PipelineVisualizer


def test_pipeline_visualizer_generate_html() -> None:
    synthetic_run_data = {
        "manifest": {
            "run_id": "test_run_123",
            "framework": "reflection_agent_fw",
            "model": "gpt-4o-mini",
            "start_time": "2026-09-23T20:00:00",
            "max_rounds": 3,
        },
        "designs": [
            {
                "design_name": "adder_8bit",
                "category": "Arithmetic",
                "subcategory": "Adder",
                "tier": 1,
                "solved": True,
                "solved_level": "L0_ZERO_SHOT",
                "final_code": "module adder_8bit; endmodule",
                "total_prompt_tokens": 120,
                "total_completion_tokens": 80,
                "total_elapsed_sec": 3.45,
                "steps": [
                    {
                        "step_index": 0,
                        "level": "L0_ZERO_SHOT",
                        "prompt": "Design adder_8bit",
                        "completion": "module adder_8bit; endmodule",
                        "extracted_code": "module adder_8bit; endmodule",
                        "lint_ok": True,
                        "lint_output": "Clean",
                        "sim_ok": True,
                        "sim_output": "Your Design Passed",
                        "prompt_tokens": 120,
                        "completion_tokens": 80,
                        "elapsed_sec": 3.45,
                        "stages": [
                            {
                                "stage_id": "prompt_prep",
                                "stage_name": "Prompt Assembly",
                                "status": "SUCCESS",
                                "duration_sec": 0.01,
                            },
                            {
                                "stage_id": "rtl_generation",
                                "stage_name": "RTL Code Generation",
                                "status": "SUCCESS",
                                "duration_sec": 3.2,
                                "metrics": {"prompt_tokens": 120, "completion_tokens": 80},
                            },
                            {
                                "stage_id": "static_lint",
                                "stage_name": "Verilator Static Lint",
                                "status": "SUCCESS",
                                "duration_sec": 0.04,
                            },
                            {
                                "stage_id": "behavioral_sim",
                                "stage_name": "Icarus Verilog Simulation",
                                "status": "SUCCESS",
                                "duration_sec": 0.2,
                            },
                        ],
                    }
                ],
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_html = Path(tmp_dir) / "test_viz.html"
        generated = PipelineVisualizer.generate_html_report(synthetic_run_data, out_html)

        assert generated.is_file()
        content = generated.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "adder_8bit" in content
        assert "RTLLM Pipeline Execution Visualizer" in content
        assert "Stage-Gated Pipeline Visualizer" in content
        assert "gpt-4o-mini" in content
