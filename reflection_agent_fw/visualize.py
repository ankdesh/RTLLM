"""Standalone visualization generator for reflection_agent_fw trajectories."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from reflection_agent_fw.html_template import HTML_TEMPLATE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("refl_visualize")


class TrajectoryVisualizer:
    """Renders single SolveResult trajectories into standalone interactive HTML pages."""

    @classmethod
    def render_solve_result(cls, trajectory_data: Dict[str, Any], output_path: Path) -> Path:
        """Render single problem solve trajectory to HTML."""
        design_name = trajectory_data.get("problem_name") or trajectory_data.get("design_name", "design")
        run_data = {
            "manifest": {
                "framework": "reflection_agent_fw",
                "model": "Single Problem Run",
                "start_time": "N/A",
                "max_rounds": len(trajectory_data.get("steps", [])),
            },
            "designs": [
                {
                    "design_name": design_name,
                    "category": trajectory_data.get("category", "Custom"),
                    "subcategory": trajectory_data.get("subcategory", "RTL"),
                    "tier": 1,
                    "solved": trajectory_data.get("solved", False),
                    "solved_level": trajectory_data.get("solved_level"),
                    "final_code": trajectory_data.get("final_code", ""),
                    "steps": trajectory_data.get("steps", []),
                    "total_prompt_tokens": trajectory_data.get("total_prompt_tokens", 0),
                    "total_completion_tokens": trajectory_data.get("total_completion_tokens", 0),
                    "total_elapsed_sec": trajectory_data.get("total_elapsed_sec", 0.0),
                }
            ],
        }

        json_str = json.dumps(run_data)
        html_content = HTML_TEMPLATE.replace("%DATA_JSON%", json_str)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")
        return output_path


def main() -> int:
    """CLI utility to generate visualization from a JSON trajectory."""
    parser = argparse.ArgumentParser(description="Generate interactive HTML from trajectory JSON.")
    parser.add_argument("json_file", type=Path, help="Path to solve trajectory JSON file.")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output HTML path.")
    args = parser.parse_args()

    if not args.json_file.is_file():
        logger.error("JSON file not found: %s", args.json_file)
        return 1

    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    out_file = args.output or args.json_file.with_suffix(".html")
    TrajectoryVisualizer.render_solve_result(data, out_file)
    print(f"\nGenerated visualization: file://{out_file.resolve()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
