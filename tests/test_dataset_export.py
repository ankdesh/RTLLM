"""Integration tests for dataset discovery and export."""

import json
from pathlib import Path
import pytest

from agent_eval.dataset_exporter import DatasetExporter, KNOWN_CATEGORIES


def test_discover_designs_count() -> None:
    """Validate that exactly 50 designs are discovered with valid files."""
    exporter = DatasetExporter()
    designs = exporter.discover_designs()
    assert len(designs) == 50

    root = exporter.root_dir
    for d in designs:
        assert d.design_name
        assert d.category in KNOWN_CATEGORIES
        assert d.subcategory
        assert d.target_filename.endswith(".v")
        assert len(d.prompt) > 20
        assert (root / d.testbench_path).is_file()
        assert (root / d.verified_rtl_path).is_file()


def test_export_json_and_jsonl(tmp_path: Path) -> None:
    """Verify that export produces valid JSON and JSONL matching schema."""
    exporter = DatasetExporter()
    json_p, jsonl_p = exporter.export_all(output_dir=tmp_path)

    assert json_p.is_file()
    assert jsonl_p.is_file()

    with open(json_p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 50
    assert "prompt" in data[0]
    assert "testbench_path" in data[0]

    with open(jsonl_p, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 50
    first_line_obj = json.loads(lines[0])
    assert first_line_obj["design_name"] == data[0]["design_name"]
