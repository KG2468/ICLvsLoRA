"""Download official benchmark splits and materialize auditable local JSONL."""

from __future__ import annotations

import ast
import json
import random
from pathlib import Path

from .config import digest, read_jsonl, write_jsonl
from .language import Language

SOURCES = {
    "mbpp": ("google-research-datasets/mbpp", "full"),
    "humaneval": ("openai/openai_humaneval", None),
    "aime2024": ("project-numina/aimo-validation-aime", None),
    "aime2025": ("yentinglin/aime_2025", None),
    "gpqa": ("Idavidrein/gpqa", "gpqa_diamond"),
}


def prepare(cfg: dict):
    from datasets import load_dataset

    root = Path(cfg["experiment"]["data_dir"])
    root.mkdir(parents=True, exist_ok=True)
    wanted = {"mbpp"} | {
        "humaneval" if b.startswith("humaneval") else b for b in cfg["experiment"]["benchmarks"]
    }
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for name in sorted(wanted):
        files = ["mbpp_train", "mbpp_valid"] if name == "mbpp" else [name]
        if name in manifest and all((root / f"{file}.jsonl").exists() for file in files):
            for file in files:
                if digest(read_jsonl(root / f"{file}.jsonl")) != manifest[name]["hashes"][file]:
                    raise ValueError(f"Dataset modified: {file}; use a new data directory")
            print(f"Using verified local {name}", flush=True)
            continue
        repo, subset = SOURCES[name]
        print(f"Downloading {repo} ({subset or 'default'})", flush=True)
        try:
            ds = load_dataset(repo, subset)
        except Exception as exc:
            if name == "gpqa" and (
                "gated" in str(exc).lower() or "authenticated" in str(exc).lower()
            ):
                raise RuntimeError(
                    "GPQA Diamond requires approved Hugging Face access. Accept access at "
                    "https://huggingface.co/datasets/Idavidrein/gpqa and run `uv run hf auth login`, "
                    "then rerun prepare. Other downloaded datasets are preserved."
                ) from exc
            raise
        rows_by_file = {}
        if name == "mbpp":
            for split, file in [("train", "mbpp_train"), ("validation", "mbpp_valid")]:
                rows_by_file[file] = [
                    {"id": f"mbpp/{r['task_id']}", "prompt": r["text"], "code": r["code"]}
                    for r in ds[split]
                ]
        elif name == "humaneval":
            rows_by_file[name] = [
                {
                    "id": r["task_id"],
                    "prompt": r["prompt"],
                    "test": r["test"],
                    "entry_point": r["entry_point"],
                }
                for r in ds["test"]
            ]
        elif name.startswith("aime"):
            year = name[-4:]
            rows = list(ds["train"])
            if name == "aime2024":
                rows = [r for r in rows if "2024_AIME" in r.get("url", "")]
            if len(rows) != 30:
                raise ValueError(f"Expected 30 {year} AIME questions, got {len(rows)}")
            rows_by_file[name] = [
                {"id": f"{name}/{r['id']}", "prompt": r["problem"], "answer": str(int(r["answer"]))}
                for r in rows
            ]
        else:
            rows = []
            for i, r in enumerate(ds["train"]):
                choices = [(r["Correct Answer"], True)] + [
                    (r[f"Incorrect Answer {j}"], False) for j in (1, 2, 3)
                ]
                random.Random(182 + i).shuffle(choices)
                answer = next("ABCD"[j] for j, (_, ok) in enumerate(choices) if ok)
                prompt = (
                    r["Question"]
                    + "\n"
                    + "\n".join(f"{letter}. {text}" for letter, (text, _) in zip("ABCD", choices))
                )
                rows.append({"id": f"gpqa/{i}", "prompt": prompt, "answer": answer})
            if len(rows) != 198:
                raise ValueError(f"Expected 198 GPQA Diamond questions, got {len(rows)}")
            rows_by_file[name] = rows
        for file, rows in rows_by_file.items():
            write_jsonl(root / f"{file}.jsonl", rows)
        manifest[name] = {
            "repo": repo,
            "subset": subset,
            "fingerprints": {k: v._fingerprint for k, v in ds.items()},
            "hashes": {file: digest(rows) for file, rows in rows_by_file.items()},
            "counts": {file: len(rows) for file, rows in rows_by_file.items()},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def examples(cfg: dict, lang: Language, seed: int) -> tuple[list[dict], list[dict]]:
    root = Path(cfg["experiment"]["data_dir"])
    train, valid = [read_jsonl(root / f"mbpp_{split}.jsonl") for split in ("train", "valid")]
    # Duplicate normalized solutions are excluded from validation. No evaluation
    # answers are loaded or used for training/example selection.
    fingerprints = {ast.dump(ast.parse(r["code"])) for r in train}
    valid = [r for r in valid if ast.dump(ast.parse(r["code"])) not in fingerprints]
    random.Random(seed).shuffle(train)
    random.Random(seed).shuffle(valid)
    needed = max(cfg["experiment"]["sizes"])
    nvalid = cfg["training"]["validation_examples"]
    if len(train) < needed or len(valid) < nvalid:
        raise ValueError("Not enough distinct train/validation examples")
    # Never silently drop a problem when the transpiler encounters unsupported syntax.
    return (
        [dict(r, synthetic=lang.encode(r["code"])) for r in train[:needed]],
        [dict(r, synthetic=lang.encode(r["code"])) for r in valid[:nvalid]],
    )


def tasks(cfg: dict, benchmark: str) -> list[dict]:
    name = "humaneval" if benchmark.startswith("humaneval") else benchmark
    rows = read_jsonl(Path(cfg["experiment"]["data_dir"]) / f"{name}.jsonl")
    limit = cfg["evaluation"]["limit"]
    return rows[:limit] if limit else rows
