import json

import pytest

from final_project.config import read_jsonl, resume_results, write_jsonl


def test_unicode_separators_inside_json_strings(tmp_path):
    path = tmp_path / "questions.jsonl"
    rows = [{"prompt": "first\u2028second\u2029third\x85fourth"}, {"prompt": "next"}]
    write_jsonl(path, rows)
    assert read_jsonl(path) == rows


def test_torn_last_result_is_archived(tmp_path):
    path = tmp_path / "results.jsonl"
    path.write_bytes(b'{"key":"a"}\n{"key":"b')
    assert resume_results(path) == [{"key": "a"}]
    assert path.read_text() == '{"key":"a"}\n'
    assert len(list(tmp_path.glob("results.incomplete-*"))) == 1


def test_valid_last_result_gets_newline(tmp_path):
    path = tmp_path / "results.jsonl"
    path.write_text('{"key":"a"}')
    assert resume_results(path) == [{"key": "a"}]
    assert path.read_text().endswith("\n")


def test_middle_corruption_is_not_hidden(tmp_path):
    path = tmp_path / "results.jsonl"
    path.write_text('broken\n{"key":"a"}\n')
    with pytest.raises(json.JSONDecodeError):
        resume_results(path)
