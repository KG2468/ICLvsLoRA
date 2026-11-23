from __future__ import annotations

import fcntl
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
import platform
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from contextlib import ExitStack
from pathlib import Path

from .backend import MLXBackend
from .config import digest, model_path, resume_results
from .data import examples, tasks
from .gpu import available_bytes, replica_count
from .language import Language
from .prompts import prefix, query
from .scoring import execute, score
from .training import SupervisedDataset

CODE_FINAL_TOKENS = 750


def final_instruction(benchmark):
    if benchmark.startswith("humaneval"):
        dialect = "synthetic" if benchmark.endswith("synthetic") else "standard"
        form = f"the complete {dialect} Python program, including any imports"
    elif benchmark == "gpqa":
        form = "a single letter A, B, C, or D"
    else:
        form = "a single integer from 0 to 999"
    return f"Give your best final answer now. Reply only with {form}. No reasoning."


def final_only_prompt(prompt, instruction):
    return prompt[:-1] + [{"role": "user", "content": prompt[-1]["content"] + "\n" + instruction}]


def score_with_followup(backend, prompt, generated, task, benchmark, lang, seed, cfg):
    timeout = cfg["evaluation"]["timeout"]
    coding = benchmark.startswith("humaneval")
    output = generated["text"]
    # Qwen puts the opening think tag in the prompt, outside the raw trace.
    if generated.get("thinking") and "</think>" not in output:
        output = ""
    initial = score(output, task, benchmark, lang, timeout)
    if generated.get("finish_reason") != "length" or (
        not coding and initial["status"] != "answer_missing"
    ):
        return initial
    limit = CODE_FINAL_TOKENS if coding else 25
    instruction = final_instruction(benchmark)
    turns = prompt + [
        {"role": "assistant", "content": generated["text"]},
        {"role": "user", "content": instruction},
    ]
    remaining = cfg["generation"]["max_context"] - len(backend.tokens(turns, thinking=False))
    include_draft = True
    if coding and remaining < limit:
        # Preflight reserves room for this version even with the longest ICL context.
        turns = final_only_prompt(prompt, instruction)
        include_draft = False
        remaining = cfg["generation"]["max_context"] - len(backend.tokens(turns, thinking=False))
        if remaining < limit:
            raise ValueError("Context too small for the 750-token final code budget")
    budget = min(limit, remaining)
    if budget < 1:
        return {**initial, "initial_score": initial, "followup": {"status": "context_full"}}
    reply = backend.generate(turns, seed, max_tokens=budget, thinking=False)
    final = score(reply["text"], task, benchmark, lang, timeout)
    return {
        **final,
        "initial_score": initial,
        "followup": {
            "instruction": instruction,
            "includes_draft_turn": include_draft,
            "budget": budget,
            **reply,
        },
    }


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


def preflight(cfg: dict) -> dict:
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
        lang = Language(seed)
        train, valid = examples(cfg, lang, seed)
        processed = SupervisedDataset(train + valid, tokenizer, lang, cfg)
        max_training = max(max_training, max(len(row[0]) for row in processed.rows))
        for benchmark in cfg["experiment"]["benchmarks"]:
            # The maximum N ICL prompt bounds the smaller nested prefixes.
            messages = prefix(lang, "icl", train, benchmark.endswith("synthetic"))
            for task in tasks(cfg, benchmark):
                prompt = messages + [query(task, benchmark, lang)]
                tokens = tokenizer.apply_chat_template(
                    prompt,
                    tokenize=True,
                    return_dict=False,
                    add_generation_prompt=True,
                    enable_thinking=benchmark.startswith("humaneval")
                    or cfg["generation"]["enable_thinking"],
                )
                longest = max(longest, len(tokens))
                if benchmark.startswith("humaneval"):
                    final_tokens = tokenizer.apply_chat_template(
                        final_only_prompt(prompt, final_instruction(benchmark)),
                        tokenize=True,
                        return_dict=False,
                        add_generation_prompt=True,
                        enable_thinking=False,
                    )
                    if len(final_tokens) + CODE_FINAL_TOKENS > cfg["generation"]["max_context"]:
                        raise ValueError("Context too small for the 750-token final code budget")
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


def run(cfg: dict, stage: str = "all", *, workers: int | None = None):
    stages(stage)
    exp = cfg["experiment"]
    root = Path(exp["output_dir"]) / exp["name"]
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("This experiment is already running") from exc
        _run(cfg, root, stage, workers=workers)


def generate_row(backend, cfg, condition, n, seed, benchmark, lang, messages, example_ids, task):
    key = f"{condition}/{n}/{seed}/{benchmark}/{task['id']}"
    generation_seed = int(digest([seed, benchmark, task["id"]])[:8], 16)
    prompt = messages + [query(task, benchmark, lang)]
    print(f"Generating {key}", flush=True)
    thinking = benchmark.startswith("humaneval") or cfg["generation"]["enable_thinking"]
    generated = backend.generate(prompt, generation_seed, thinking=thinking)
    scored = score_with_followup(
        backend, prompt, generated, task, benchmark, lang, generation_seed, cfg
    )
    return {
        "key": key,
        "condition": condition,
        "n": n,
        "seed": seed,
        "generation_seed": generation_seed,
        "benchmark": benchmark,
        "task_id": task["id"],
        "example_ids": example_ids,
        "messages": prompt,
        **generated,
        **scored,
    }


# Each spawned process owns its model, adapter, RNG and mutable MLX cache.
def init_replica(cfg, adapter, condition, n, seed, benchmark, messages, example_ids):
    global _replica
    backend = MLXBackend(cfg, adapter)
    backend.set_prefix(messages)
    _replica = (backend, cfg, condition, n, seed, benchmark, Language(seed), messages, example_ids)


def replica_task(task):
    return generate_row(*_replica, task)


def parallel_rows(count, initargs, tasks):
    with ProcessPoolExecutor(
        max_workers=count,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=init_replica,
        initargs=initargs,
    ) as pool:
        yield from pool_rows(pool, replica_task, tasks, count)


def pool_rows(pool, fn, tasks, count):
    remaining = iter(tasks)
    active = {pool.submit(fn, task) for _, task in zip(range(count), remaining)}
    while active:
        done, active = wait(active, return_when=FIRST_COMPLETED)
        for future in done:
            yield future.result()
            task = next(remaining, None)
            if task is not None:
                active.add(pool.submit(fn, task))


def init_group_replica(cfg, adapter, condition, n, seed, rows):
    global _group
    lang = Language(seed)
    _group = {
        "backend": MLXBackend(cfg, adapter),
        "cfg": cfg,
        "condition": condition,
        "n": n,
        "seed": seed,
        "lang": lang,
        "ids": [row["id"] for row in rows],
        "prefixes": {mode: prefix(lang, condition, rows, mode) for mode in (True, False)},
        "mode": None,
    }


def group_task(item):
    benchmark, task = item
    group = _group
    mode = benchmark.endswith("synthetic")
    messages = group["prefixes"][mode]
    if mode != group["mode"]:
        group["backend"].set_prefix(messages)
        group["mode"] = mode
    return generate_row(
        group["backend"],
        group["cfg"],
        group["condition"],
        group["n"],
        group["seed"],
        benchmark,
        group["lang"],
        messages,
        group["ids"],
        task,
    )


def compatible_scheduler_identity(inputs, previous):
    # Reconstruct the prior digest only for the exact scheduling-only source revision.
    migration = json.loads(Path(__file__).with_name("scheduler_compat.json").read_text())
    implementation = inputs["implementation"]
    if any(implementation.get(k) != v for k, v in migration["after"].items()):
        return False
    for prior in [migration["before"], *migration.get("earlier", [])]:
        old_inputs = {**inputs, "implementation": {**implementation, **prior}}
        if digest(old_inputs) == previous:
            return True
    return False


def _run(cfg: dict, root: Path, stage: str = "all", *, workers: int | None = None):
    from .report import report

    exp = cfg["experiment"]
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
    inputs = {
        "cfg": cfg,
        "data": data_hashes,
        "weights": weight_hashes,
        "packages": packages,
        "implementation": {
            p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))
        },
    }
    identity = digest(inputs)
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())["identity"]
        if previous != identity and not compatible_scheduler_identity(inputs, previous):
            raise ValueError(
                "Run inputs/code changed; choose a new experiment.name to avoid mixing results"
            )
    print("Checking context budgets, training lengths, and code sandbox...", flush=True)
    checks = preflight(cfg)
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
        "language_mappings_by_seed": {seed: Language(seed).mapping for seed in exp["seeds"]},
        "language_version": Language.version,
    }
    temporary_manifest = manifest_path.with_suffix(".tmp")
    temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary_manifest.replace(manifest_path)
    results_path = root / "results.jsonl"
    results = resume_results(results_path)
    completed = {r["key"] for r in results}
    if len(completed) != len(results):
        raise ValueError("Duplicate result keys in run log")
    del results
    print(json.dumps(manifest["plan"] | checks, indent=2), flush=True)

    def commit(row, workers):
        row["generation_workers"] = workers
        with results_path.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        completed.add(row["key"])
        print(
            f"  {row['key']} {row['status']}; {row['generation_tokens']} tokens, "
            f"{row['seconds']:.1f}s",
            flush=True,
        )

    def group_recorder(benchmark, task_count):
        started = time.monotonic()
        committed = total_tokens = 0

        def record(row, count):
            nonlocal committed, total_tokens
            commit(row, count)
            committed += 1
            total_tokens += row["generation_tokens"] + row.get("followup", {}).get(
                "generation_tokens", 0
            )
            if committed % 10 == 0 or committed == task_count:
                elapsed = time.monotonic() - started
                print(
                    f"{benchmark}: {committed}/{task_count} pending tasks committed; "
                    f"{total_tokens / elapsed:.1f} wall tokens/s, "
                    f"{60 * committed / elapsed:.2f} tasks/min",
                    flush=True,
                )

        return record

    def evaluate(condition: str, n: int, seed: int, rows: list[dict], adapter=None):
        lang = Language(seed)
        example_ids = [row["id"] for row in rows]
        backend = None
        resources = ExitStack()
        shared_pool = None
        cap = cfg["generation"].get("max_workers", 2) if workers is None else workers
        try:
            for benchmark in exp["benchmarks"]:
                key_prefix = f"{condition}/{n}/{seed}/{benchmark}/"
                batch = [t for t in tasks(cfg, benchmark) if key_prefix + t["id"] not in completed]
                if not batch:
                    continue
                record = group_recorder(benchmark, len(batch))

                if workers is not None and workers > 1:
                    count = min(workers, len(batch))
                    if shared_pool is None:
                        shared_pool = resources.enter_context(
                            ProcessPoolExecutor(
                                max_workers=workers,
                                mp_context=multiprocessing.get_context("spawn"),
                                initializer=init_group_replica,
                                initargs=(cfg, adapter, condition, n, seed, rows),
                            )
                        )
                    print(
                        f"{benchmark}: forcing {count} generation worker(s) for {len(batch)} pending tasks",
                        flush=True,
                    )
                    for row in pool_rows(
                        shared_pool, group_task, ((benchmark, t) for t in batch), count
                    ):
                        record(row, count)
                    continue
                messages = prefix(lang, condition, rows, benchmark.endswith("synthetic"))
                args = (cfg, condition, n, seed, benchmark, lang, messages, example_ids)
                remaining = batch
                count = min(cap, len(batch))
                if workers is not None:
                    print(
                        f"{benchmark}: forcing {count} generation worker(s) for {len(batch)} pending tasks",
                        flush=True,
                    )
                if workers is None or count == 1:
                    if backend is None:
                        backend = MLXBackend(cfg, adapter)
                    backend.set_prefix(messages)
                if workers is None:
                    pilot = generate_row(backend, *args, batch[0])
                    record(pilot, 1)
                    remaining = batch[1:]
                    count = 1
                if workers is None and cap > 1 and len(remaining) > 1:
                    peak = max(
                        r.get("gpu", {}).get("mlx_peak_bytes", 0)
                        for r in (pilot, pilot.get("followup", {}))
                    )
                    free = available_bytes()
                    gpu = pilot.get("gpu", {})
                    utilization = (
                        gpu.get("device_utilization_mean_pct")
                        if gpu.get("samples", 0) >= 3
                        else None
                    )
                    count = replica_count(
                        cap,
                        len(remaining),
                        peak,
                        free,
                        utilization,
                        utilization_source=gpu.get("utilization_source"),
                    )
                    print(
                        f"{benchmark}: {count} generation worker(s), "
                        f"pilot peak {peak / 1e9:.1f} GB, free {free / 1e9:.1f} GB",
                        flush=True,
                    )
                if count > 1:
                    if backend is not None:
                        backend.close()
                        backend = None
                    initargs = (cfg, adapter, condition, n, seed, benchmark, messages, example_ids)
                    try:
                        for row in parallel_rows(count, initargs, remaining):
                            record(row, count)
                        continue
                    except (RuntimeError, MemoryError) as exc:
                        oom = isinstance(exc, (MemoryError, BrokenProcessPool)) or any(
                            term in str(exc).lower()
                            for term in (
                                "out of memory",
                                "out_of_memory",
                                "insufficient memory",
                                "allocation failed",
                                "bad_alloc",
                                "cudaerrormemoryallocation",
                            )
                        )
                        if workers is not None or not oom:
                            raise
                        print(
                            f"Replica pool failed ({exc}); resuming this group serially", flush=True
                        )
                        cap = 1
                        remaining = [t for t in remaining if key_prefix + t["id"] not in completed]
                        backend = MLXBackend(cfg, adapter)
                        backend.set_prefix(messages)
                for task in remaining:
                    record(generate_row(backend, *args, task), 1)
        finally:
            resources.close()
            if backend is not None:
                backend.close()

    for condition in stages(stage):
        print(f"Starting {condition.upper()} stage", flush=True)
        for seed in exp["seeds"]:
            if condition == "base":
                evaluate("base", 0, seed, [])
                continue
            train, valid = examples(cfg, Language(seed), seed)
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
