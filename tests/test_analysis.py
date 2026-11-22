import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "analysis", Path(__file__).parents[1] / "scripts/analyze_results.py"
)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_snapshot_does_not_include_later_appends(tmp_path):
    path = tmp_path / "rows.jsonl"
    first = (json.dumps({"key": "a", "messages": ["private prompt"]}) + "\n").encode()
    path.write_bytes(first + b'{"key":"b"}\n')
    rows, meta = analysis.snapshot(path, len(first))
    assert rows == [{"key": "a"}]
    assert meta["bytes"] == len(first)


def test_duplicate_results_are_rejected(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"key":"a"}\n{"key":"a"}\n')
    with pytest.raises(ValueError, match="Duplicate"):
        analysis.snapshot(path)


def test_paired_comparison_clusters_seeds_and_excludes_unmatched():
    left = [{"seed": s, "task_id": t, "passed": False} for s in (0, 1, 2) for t in ("a", "b")]
    right = [dict(r, passed=True) for r in left]
    right.append({"seed": 0, "task_id": "extra", "passed": False})
    result = analysis.paired(left, right)
    assert result["paired_evaluations"] == 6
    assert result["distinct_tasks"] == 2
    assert result["paired_seeds"] == 3
    assert result["delta"] == result["ci_low"] == result["ci_high"] == 1
