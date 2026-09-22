"""Dataset exporter for crawling RTLLM v2.1 benchmark designs and exporting datasets."""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agent_eval.models import DesignMeta

logger = logging.getLogger(__name__)

# Canonical domain categories in RTLLM v2.1
KNOWN_CATEGORIES = ("Arithmetic", "Memory", "Control", "Miscellaneous")
MODULE_NAME_PATTERN = re.compile(r"Module\s+name:\s*([a-zA-Z0-9_]+)", re.IGNORECASE)


class DatasetExporter:
    """Discovers, parses, and exports RTLLM v2.1 circuit specifications and metadata."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        """Initialize exporter with benchmark root directory.

        Args:
            root_dir: Base directory of RTLLM repository. Defaults to repository root.
        """
        if root_dir is None:
            self._root_dir = Path(__file__).resolve().parent.parent
        else:
            self._root_dir = Path(root_dir).resolve()

        if not self._root_dir.is_dir():
            raise FileNotFoundError(f"Root directory does not exist: {self._root_dir}")

    @property
    def root_dir(self) -> Path:
        """Return base repository directory."""
        return self._root_dir

    def discover_designs(self) -> List[DesignMeta]:
        """Scan benchmark directories and extract metadata for all designs.

        Returns:
            List of sorted DesignMeta records.

        Raises:
            RuntimeError: If fewer than 50 designs are discovered or files are missing.
        """
        designs: List[DesignMeta] = []

        for desc_path in self._root_dir.rglob("design_description.txt"):
            design_dir = desc_path.parent
            tb_path = design_dir / "testbench.v"
            if not tb_path.is_file():
                logger.warning("Skipping %s: testbench.v not found", design_dir)
                continue

            # Identify verified RTL file
            verified_files = list(design_dir.glob("verified_*.v"))
            if not verified_files:
                raise FileNotFoundError(f"Missing verified reference RTL in {design_dir}")
            verified_rtl = verified_files[0]

            # Categorize by directory structure relative to root
            rel_parts = design_dir.relative_to(self._root_dir).parts
            if len(rel_parts) < 2:
                continue

            category = rel_parts[0]
            if category not in KNOWN_CATEGORIES:
                continue

            subcategory = rel_parts[1] if len(rel_parts) >= 3 else "General"
            design_name = design_dir.name

            # Read prompt and parse target module name
            prompt_text = desc_path.read_text(encoding="utf-8", errors="replace").strip()
            module_match = MODULE_NAME_PATTERN.search(prompt_text)
            module_name = module_match.group(1).strip() if module_match else design_name

            meta = DesignMeta(
                design_name=design_name,
                category=category,
                subcategory=subcategory,
                target_filename=f"{design_name}.v",
                prompt=prompt_text,
                testbench_path=str(tb_path.relative_to(self._root_dir)),
                verified_rtl_path=str(verified_rtl.relative_to(self._root_dir)),
                module_name=module_name,
            )
            designs.append(meta)

        # Sort predictably by Category then Design Name
        designs.sort(key=lambda d: (d.category, d.subcategory, d.design_name))

        if len(designs) != 50:
            logger.warning("Discovered %d designs (expected 50)", len(designs))

        return designs

    def export_json(self, output_path: Path) -> Path:
        """Export all discovered designs to a structured JSON array file.

        Args:
            output_path: Destination JSON path.

        Returns:
            Path to exported JSON file.
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        designs = self.discover_designs()
        data = [d.to_dict() for d in designs]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info("Exported %d designs to %s", len(data), output_path)
        return output_path

    def export_jsonl(self, output_path: Path) -> Path:
        """Export all discovered designs to a line-delimited JSONL file.

        Args:
            output_path: Destination JSONL path.

        Returns:
            Path to exported JSONL file.
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        designs = self.discover_designs()
        with open(output_path, "w", encoding="utf-8") as f:
            for d in designs:
                f.write(json.dumps(d.to_dict()) + "\n")

        logger.info("Exported %d designs to %s", len(designs), output_path)
        return output_path

    def export_all(self, output_dir: Optional[Path] = None) -> Tuple[Path, Path]:
        """Export both JSON and JSONL datasets into the target directory.

        Args:
            output_dir: Target directory (default: benchmark root).

        Returns:
            Tuple of (json_path, jsonl_path).
        """
        dest_dir = self._root_dir if output_dir is None else Path(output_dir).resolve()
        json_path = self.export_json(dest_dir / "rtllm_v2_1_dataset.json")
        jsonl_path = self.export_jsonl(dest_dir / "rtllm_v2_1_dataset.jsonl")
        return json_path, jsonl_path
