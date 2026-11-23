from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    # JSONL records are separated by LF. Unicode separators such as U+2028
    # can legally occur inside JSON strings (including real GPQA questions).
    return [json.loads(line) for line in path.read_text().split("\n") if line.strip()]


def resume_results(path: Path) -> list[dict]:
    """Recover only a torn final append; never hide corruption in earlier rows."""
    if not path.exists():
        return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        boundary = raw.rfind(b"\n") + 1
        tail = raw[boundary:]
        try:
            json.loads(tail)
        except (ValueError, UnicodeDecodeError):
            archive = path.with_suffix(f".incomplete-{hashlib.sha256(tail).hexdigest()[:12]}")
            archive.write_bytes(tail)
            path.write_bytes(raw[:boundary])
        else:
            with path.open("ab") as handle:
                handle.write(b"\n")
    return read_jsonl(path)


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def load_config(path: str | Path) -> dict:
    cfg = tomllib.loads(Path(path).read_text())
    for section in ("model", "experiment", "training", "generation", "evaluation"):
        if section not in cfg:
            raise ValueError(f"Missing [{section}] config section")
    exp, gen, train = cfg["experiment"], cfg["generation"], cfg["training"]
    if not exp["sizes"] or any(n <= 0 for n in exp["sizes"]):
        raise ValueError("sizes must be positive")
    if len(set(exp["sizes"])) != len(exp["sizes"]) or not exp["seeds"]:
        raise ValueError("sizes must be unique and seeds nonempty")
    if len(set(exp["seeds"])) != len(exp["seeds"]):
        raise ValueError("seeds must be unique")
    if not exp["benchmarks"] or set(exp["benchmarks"]) - {
        "humaneval_synthetic",
        "humaneval_python",
        "aime2024",
        "aime2025",
        "gpqa",
    }:
        raise ValueError("Unknown or empty benchmark selection")
    if cfg["model"]["precision"] not in {"fp16", "fp8", "int8"}:
        raise ValueError("precision must be fp16, fp8 (MXFP8), or int8 (affine)")
    if type(gen.get("max_workers", 2)) is not int or gen.get("max_workers", 2) < 1:
        raise ValueError("generation.max_workers must be a positive integer")
    if gen["max_tokens"] <= 0 or gen["max_context"] <= gen["max_tokens"]:
        raise ValueError("max_context must exceed positive max_tokens")
    if train["rank"] <= 0 or train["batch_size"] <= 0 or train["epochs"] <= 0:
        raise ValueError("rank, batch_size and epochs must be positive")
    if cfg["evaluation"]["limit"] < 0 or cfg["evaluation"]["timeout"] <= 0:
        raise ValueError("limit must be nonnegative and timeout positive")
    if cfg["evaluation"].get("sandbox") not in {"macos", "linux-chroot"}:
        raise ValueError("Unknown code-scoring sandbox")
    if len(set(exp["benchmarks"])) != len(exp["benchmarks"]):
        raise ValueError("benchmarks must be unique")
    if not exp["name"] or Path(exp["name"]).name != exp["name"] or exp["name"] in {".", ".."}:
        raise ValueError("experiment.name must be a single directory name")
    if gen["prefill_step_size"] <= 0 or gen["temperature"] < 0 or gen["top_k"] < 0:
        raise ValueError("Invalid prefill size or sampling settings")
    if not 0 <= gen["top_p"] <= 1 or not 0 <= gen["min_p"] <= 1:
        raise ValueError("Sampling probabilities must be between zero and one")
    if train["validation_examples"] <= 0 or train["max_seq_length"] <= 0:
        raise ValueError("Validation size and training context must be positive")
    if train["num_layers"] == 0 or train["num_layers"] < -1:
        raise ValueError("num_layers must be positive or -1 for all layers")
    if train["alpha"] <= 0 or train["learning_rate"] <= 0:
        raise ValueError("LoRA alpha and learning rate must be positive")
    return cfg


def model_path(cfg: dict) -> Path:
    return Path(cfg["model"]["directory"]) / cfg["model"]["precision"]
