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

        def generate(self, messages, seed):
            events.append(messages[0])
            return {"text": "answer", "generation_tokens": 1, "seconds": 0}

        def close(self):
            pass

    monkeypatch.setattr(experiment, "MLXBackend", Backend)
    experiment._run(cfg, tmp_path)
    assert events == ["icl"] * 4 + ["train", "lora"] * 4 + ["base"] * 2
