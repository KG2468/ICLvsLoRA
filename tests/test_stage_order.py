import json

from final_project import experiment, report
from final_project.config import load_config


def test_runner_completes_every_icl_job_before_any_training(tmp_path, monkeypatch):
    cfg = load_config("configs/smoke.toml")
    cfg["experiment"].update(sizes=[1, 2], seeds=[0, 1], benchmarks=["humaneval_python"])
    events = []
    monkeypatch.setattr(experiment.platform, "platform", lambda: "test")
    row = {"id": "example", "synthetic": "code", "prompt": "task"}
    monkeypatch.setattr(experiment, "examples", lambda *args: ([row, row], [row]))
    monkeypatch.setattr(experiment, "tasks", lambda *args: [{"id": "task", "prompt": "task"}])
    monkeypatch.setattr(experiment, "file_hash", lambda path: "fixture")
    monkeypatch.setattr(experiment, "preflight", lambda *args: {})
    monkeypatch.setattr(experiment, "prefix", lambda lang, condition, *args: [condition])
    monkeypatch.setattr(experiment, "score", lambda *args: {"passed": True, "status": "passed"})
    monkeypatch.setattr(report, "report", lambda *args: None)
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: events.append("train"))

    class Backend:
        def __init__(self, *args):
            pass

        def set_prefix(self, messages):
            pass

        def generate(self, messages, seed, *, thinking):
            assert thinking
            events.append(messages[0])
            return {"text": "answer", "generation_tokens": 1, "seconds": 0}

        def close(self):
            pass

    monkeypatch.setattr(experiment, "MLXBackend", Backend)
    experiment._run(cfg, tmp_path)
    assert events == ["icl"] * 4 + ["train", "lora"] * 4 + ["base"] * 2
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    mappings = manifest["language_mappings_by_seed"]
    assert mappings["0"] != mappings["1"]


def test_parallel_fallback_resumes_only_uncommitted_results(tmp_path, monkeypatch):
    from unittest.mock import Mock

    cfg = load_config("configs/smoke.toml")
    cfg["experiment"].update(seeds=[0], benchmarks=["gpqa"])
    tasks = [{"id": str(i), "prompt": "?", "answer": "A"} for i in range(5)]
    monkeypatch.setattr(experiment, "tasks", lambda *args: tasks)
    monkeypatch.setattr(experiment, "preflight", lambda *args: {})
    monkeypatch.setattr(experiment, "file_hash", lambda path: "fixture")
    monkeypatch.setattr(experiment, "available_bytes", lambda: 32 * 2**30)
    monkeypatch.setattr(report, "report", lambda *args: None)
    backend = Mock()
    backend.return_value.generate.return_value = {
        "text": "A",
        "generation_tokens": 1,
        "seconds": 1,
        "gpu": {"mlx_peak_bytes": 2**30},
    }
    monkeypatch.setattr(experiment, "MLXBackend", backend)

    def partial_pool(count, initargs, remaining):
        assert count == 2
        row = {"key": "base/0/0/gpqa/1", "status": "scored", "seconds": 1, "generation_tokens": 1}
        yield row
        raise MemoryError("out of memory")

    monkeypatch.setattr(experiment, "parallel_rows", partial_pool)
    for _ in range(2):
        experiment._run(cfg, tmp_path, "base")
    rows = [json.loads(line) for line in (tmp_path / "results.jsonl").read_text().splitlines()]
    assert [r["key"] for r in rows] == [f"base/0/0/gpqa/{i}" for i in range(5)]
    assert [r["generation_workers"] for r in rows] == [1, 2, 1, 1, 1]
    assert backend.return_value.generate.call_count == 4
