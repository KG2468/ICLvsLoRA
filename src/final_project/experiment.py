from __future__ import annotations

import fcntl
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path

from .backend import MLXBackend
from .config import digest, model_path, resume_results
from .data import examples, tasks
from .language import Language
from .prompts import prefix, query
from .scoring import execute, score
from .training import SupervisedDataset


def plan(cfg: dict) -> dict:
    exp = cfg["experiment"]
    counts = {b: len(tasks(cfg, b)) for b in exp["benchmarks"]}
    return {
        "model": str(model_path(cfg)),
        "precision": cfg["model"]["precision"],
        "training_jobs": len(exp["sizes"]) * len(exp["seeds"]),
        "evaluations": sum(counts.values()) * len(exp["seeds"]) * (1 + 2 * len(exp["sizes"])),
        "tasks_per_benchmark": counts,
        "sizes": exp["sizes"],
        "seeds": exp["seeds"],
    }


def preflight(cfg: dict, lang: Language) -> dict:
    from transformers import AutoTokenizer

    from .backend import verify_model

    verify_model(cfg)
    architecture = json.loads((model_path(cfg) / "config.json").read_text())
    capacity = architecture.get("text_config", architecture).get("max_position_embeddings")
    if capacity and cfg["generation"]["max_context"] > capacity:
        raise ValueError(f"Configured context exceeds the model's {capacity}-token native limit")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path(cfg)), local_files_only=True)
    longest, max_training = 0, 0
    for seed in cfg["experiment"]["seeds"]:
        train, valid = examples(cfg, lang, seed)
        processed = SupervisedDataset(train + valid, tokenizer, lang, cfg)
        max_training = max(max_training, max(len(row[0]) for row in processed.rows))
        for benchmark in cfg["experiment"]["benchmarks"]:
            # The maximum N ICL prompt bounds the smaller nested prefixes.
            messages = prefix(lang, "icl", train, benchmark.endswith("synthetic"))
            for task in tasks(cfg, benchmark):
                tokens = tokenizer.apply_chat_template(
                    messages + [query(task, benchmark, lang)],
                    tokenize=True,
                    return_dict=False,
                    add_generation_prompt=True,
                    enable_thinking=cfg["generation"]["enable_thinking"],
                )
                longest = max(longest, len(tokens))
    if longest + cfg["generation"]["max_tokens"] > cfg["generation"]["max_context"]:
        raise ValueError(
            f"Largest ICL prompt is {longest} tokens, exceeding context budget "
            "with generation reserve. Increase max_context or explicitly reduce N."
        )
    if any(b.startswith("humaneval") for b in cfg["experiment"]["benchmarks"]):
        result = execute(
            "def identity(x): return x", "def check(f): assert f(3) == 3", "identity", 3
        )
        if not result["passed"]:
            raise RuntimeError(f"Sandbox preflight failed: {result}")
    return {"max_prompt_tokens": longest, "max_training_tokens": max_training}


def file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def stages(stage: str = "all") -> tuple[str, ...]:
    if stage not in {"all", "icl", "lora", "base"}:
        raise ValueError(f"Unknown execution stage: {stage}")
    return ("icl", "lora", "base") if stage == "all" else (stage,)


def run(cfg: dict, stage: str = "all"):
    stages(stage)
    exp = cfg["experiment"]
    root = Path(exp["output_dir"]) / exp["name"]
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("This experiment is already running") from exc
        _run(cfg, root, stage)


def _run(cfg: dict, root: Path, stage: str = "all"):
    from .report import report

    exp = cfg["experiment"]
    lang = Language(exp["language_seed"])
    data_root = Path(exp["data_dir"])
    dataset_names = {"mbpp_train", "mbpp_valid"} | {
        "humaneval" if b.startswith("humaneval") else b for b in exp["benchmarks"]
    }
    data_hashes = {name: file_hash(data_root / f"{name}.jsonl") for name in sorted(dataset_names)}
    weight_hashes = {p.name: file_hash(p) for p in sorted(model_path(cfg).glob("*.safetensors"))}
    for name in ["config.json", "tokenizer.json", "tokenizer_config.json", "chat_template.jinja"]:
        path = model_path(cfg) / name
        if path.exists():
            weight_hashes[name] = file_hash(path)
    packages = {
        p: importlib.metadata.version(p) for p in ("mlx", "mlx-lm", "transformers", "datasets")
    }
    identity = digest(
        {
            "cfg": cfg,
            "data": data_hashes,
            "weights": weight_hashes,
            "packages": packages,
            "implementation": {
                p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))
            },
        }
    )
    manifest_path = root / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text())["identity"] != identity:
        raise ValueError(
            "Run inputs/code changed; choose a new experiment.name to avoid mixing results"
        )
    print("Checking context budgets, training lengths, and code sandbox...", flush=True)
    checks = preflight(cfg, lang)
    manifest = {
        "identity": identity,
        "config": cfg,
        "datasets": data_hashes,
        "weights": weight_hashes,
        "packages": packages,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "plan": plan(cfg),
        "preflight": checks,
        "language_mapping": lang.mapping,
        "language_version": lang.version,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    results_path = root / "results.jsonl"
    results = resume_results(results_path)
    completed = {r["key"] for r in results}
    if len(completed) != len(results):
        raise ValueError("Duplicate result keys in run log")
    print(json.dumps(manifest["plan"] | checks, indent=2), flush=True)

    def evaluate(condition: str, n: int, seed: int, rows: list[dict], adapter=None):
        pending = [
            (b, t)
            for b in exp["benchmarks"]
            for t in tasks(cfg, b)
            if f"{condition}/{n}/{seed}/{b}/{t['id']}" not in completed
        ]
        if not pending:
            return
        backend = MLXBackend(cfg, adapter)
        try:
            for benchmark in exp["benchmarks"]:
                batch = [t for b, t in pending if b == benchmark]
                if not batch:
                    continue
                messages = prefix(lang, condition, rows, benchmark.endswith("synthetic"))
                backend.set_prefix(messages)
                for task in batch:
                    key = f"{condition}/{n}/{seed}/{benchmark}/{task['id']}"
                    generation_seed = int(digest([seed, benchmark, task["id"]])[:8], 16)
                    prompt = messages + [query(task, benchmark, lang)]
                    print(f"Generating {key}", flush=True)
                    generated = backend.generate(prompt, generation_seed)
                    scored = score(
                        generated["text"], task, benchmark, lang, cfg["evaluation"]["timeout"]
                    )
                    row = {
                        "key": key,
                        "condition": condition,
                        "n": n,
                        "seed": seed,
                        "generation_seed": generation_seed,
                        "benchmark": benchmark,
                        "task_id": task["id"],
                        "example_ids": [r["id"] for r in rows],
                        "messages": prompt,
                        **generated,
                        **scored,
                    }
                    with results_path.open("a") as handle:
                        handle.write(json.dumps(row) + "\n")
                        handle.flush()
                        os.fsync(handle.fileno())
                    completed.add(key)
                    print(
                        f"  {scored['status']}; {generated['generation_tokens']} tokens, "
                        f"{generated['seconds']:.1f}s",
                        flush=True,
                    )
        finally:
            backend.close()

    for condition in stages(stage):
        print(f"Starting {condition.upper()} stage", flush=True)
        for seed in exp["seeds"]:
            if condition == "base":
                evaluate("base", 0, seed, [])
                continue
            train, valid = examples(cfg, lang, seed)
            for n in exp["sizes"]:
                selected = train[:n]
                selection = {
                    "train_ids": [r["id"] for r in selected],
                    "valid_ids": [r["id"] for r in valid],
                }
                (root / f"selection-seed{seed}-n{n}.json").write_text(
                    json.dumps(selection, indent=2) + "\n"
                )
                if condition == "icl":
                    evaluate("icl", n, seed, selected)
                    continue
                # A fresh process isolates gradient checkpointing and releases
                # optimizer memory before evaluation.
                adapter = root / "adapters" / f"seed{seed}-n{n}"
                import subprocess
                import sys

                job_path = root / "training-job.json"
                job_path.write_text(
                    json.dumps({"cfg": cfg, "seed": seed, "n": n, "adapter": str(adapter)})
                )
                subprocess.run(
                    [sys.executable, "-m", "final_project", "_train", str(job_path)], check=True
                )
                evaluate("lora", n, seed, [], adapter)
        report(root)
        print(f"Completed {condition.upper()} stage", flush=True)
