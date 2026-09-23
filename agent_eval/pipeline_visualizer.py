"""Pipeline visualizer generating interactive standalone HTML reports of RTL reflection runs."""

import json
from pathlib import Path
from typing import Any, Dict, List

from reflection_agent_fw.html_template import HTML_TEMPLATE


class PipelineVisualizer:
    """Reads execution logs and checkpoints to generate interactive HTML visualizations."""

    TIER_MAPPING: Dict[str, int] = {
        "adder_8bit": 1, "adder_16bit": 1, "adder_32bit": 1, "adder_pipe_64bit": 1, "adder_bcd": 1,
        "sub_64bit": 1, "multi_8bit": 1, "multi_16bit": 1, "multi_booth_8bit": 1, "multi_pipe_4bit": 1,
        "multi_pipe_8bit": 1, "comparator_3bit": 1, "comparator_4bit": 1, "accu": 1,
        "fixed_point_adder": 1, "fixed_point_substractor": 1, "float_multi": 1, "div_16bit": 1,
        "counter_12": 2, "JC_counter": 2, "ring_counter": 2, "up_down_counter": 2,
        "right_shifter": 2, "LFSR": 2, "barrel_shifter": 2,
        "fsm": 3, "sequence_detector": 3, "traffic_light": 3, "calendar": 3, "freq_div": 3,
        "freq_divbyeven": 3, "freq_divbyodd": 3, "freq_divbyfrac": 3, "signal_generator": 3,
        "square_wave": 3, "edge_detect": 3, "pulse_detect": 3, "synchronizer": 3,
        "width_8to16": 3, "parallel2serial": 3, "serial2parallel": 3,
        "asyn_fifo": 4, "LIFObuffer": 4, "alu": 4, "pe": 4, "instr_reg": 4, "ROM": 4, "RAM": 4,
        "clkgenerator": 4, "radix2_div": 4,
    }

    @classmethod
    def load_from_checkpoints_jsonl(cls, checkpoints_path: Path) -> List[Dict[str, Any]]:
        """Parse list of design trajectories from a checkpoints.jsonl file."""
        designs: List[Dict[str, Any]] = []
        if not checkpoints_path.is_file():
            return designs

        with checkpoints_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    design_name = data.get("design_name", "unknown")
                    data["tier"] = cls.TIER_MAPPING.get(design_name, 1)
                    designs.append(data)
                except Exception:
                    continue
        return designs

    @classmethod
    def load_from_run_dir(cls, run_dir: Path) -> Dict[str, Any]:
        """Load manifest and all design trajectories from a run directory."""
        checkpoints_file = run_dir / "checkpoints.jsonl"
        manifest_file = run_dir / "manifest.json"

        manifest: Dict[str, Any] = {}
        if manifest_file.is_file():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        designs = cls.load_from_checkpoints_jsonl(checkpoints_file)
        return {
            "manifest": manifest,
            "designs": designs,
        }

    @classmethod
    def generate_html_report(cls, run_data: Dict[str, Any], output_path: Path) -> Path:
        """Render complete standalone HTML visualization file."""
        json_str = json.dumps(run_data)
        html_content = HTML_TEMPLATE.replace("%DATA_JSON%", json_str)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")
        return output_path
