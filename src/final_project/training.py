from __future__ import annotations

import gc
import hashlib
import json
import math
import types
from pathlib import Path

from .config import digest, model_path, write_jsonl
from .language import Language
from .prompts import training_messages


class SupervisedDataset:
    """Explicit assistant-only loss; identical nonthinking template to inference."""

    def __init__(self, rows, tokenizer, lang, cfg):
        self.rows = []
        for row in rows:
            messages = training_messages(lang, row)
            prompt = tokenizer.apply_chat_template(
                messages[:-1],
                tokenize=True,
                return_dict=False,
                add_generation_prompt=True,
                enable_thinking=cfg["generation"]["enable_thinking"],
            )
            completion = tokenizer.encode(messages[-1]["content"], add_special_tokens=False)
            tokens = prompt + completion + [tokenizer.eos_token_id]
            if len(tokens) > cfg["training"]["max_seq_length"]:
                raise ValueError(
                    f"{row['id']} has {len(tokens)} training tokens; increase "
                    "max_seq_length (training examples are never truncated)"
                )
            self.rows.append((tokens, len(prompt)))

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        return self.rows[index]

    def process(self, row):
        return row


def train_adapter(
    cfg: dict, lang: Language, rows: list[dict], valid: list[dict], seed: int, directory: Path
) -> Path:
    import mlx.core as mx
    import numpy as np
    from mlx_lm import load
    from mlx_lm.lora import CONFIG_DEFAULTS, train_model
    from mlx_lm.tuner.callbacks import TrainingCallback

    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / "complete.json"
    identity = digest({"cfg": cfg, "rows": rows, "valid": valid, "seed": seed})
    if marker.exists():
        completed = json.loads(marker.read_text())
        if completed["identity"] != identity:
            raise ValueError("Adapter configuration mismatch; use a new experiment name")
        if not (directory / "adapters.safetensors").exists():
            raise ValueError("Completed adapter weights are missing")
        checksum = hashlib.sha256((directory / "adapters.safetensors").read_bytes()).hexdigest()
        if checksum != completed["weights_sha256"]:
            raise ValueError("Completed adapter weights changed")
        print(f"Reusing completed adapter {directory}", flush=True)
        return directory
    train = cfg["training"]
    if len(rows) % train["batch_size"]:
        raise ValueError("batch_size must divide N so training never drops examples")
    if len(valid) < train["batch_size"]:
        raise ValueError("Not enough validation examples for batch_size")
    write_jsonl(
        directory / "train.jsonl",
        [{"id": r["id"], "messages": training_messages(lang, r)} for r in rows],
    )
    write_jsonl(
        directory / "valid.jsonl",
        [{"id": r["id"], "messages": training_messages(lang, r)} for r in valid],
    )
    np.random.seed(seed)
    mx.random.seed(seed)
    model, tokenizer = load(str(model_path(cfg)))
    training_set = SupervisedDataset(rows, tokenizer, lang, cfg)
    validation_set = SupervisedDataset(valid, tokenizer, lang, cfg)
    iters = math.ceil(train["epochs"] * len(rows) / train["batch_size"])
    args = types.SimpleNamespace(
        **(
            CONFIG_DEFAULTS
            | {
                "model": str(model_path(cfg)),
                "data": str(directory),
                "train": True,
                "seed": seed,
                "adapter_path": str(directory),
                "iters": iters,
                "num_layers": train["num_layers"],
                "batch_size": train["batch_size"],
                "learning_rate": train["learning_rate"],
                "max_seq_length": train["max_seq_length"],
                "grad_checkpoint": train["grad_checkpoint"],
                "mask_prompt": True,
                "val_batches": -1,
                "steps_per_report": min(10, iters),
                "steps_per_eval": max(1, iters),
                "save_every": max(1, iters),
                # MLX scale is the actual multiplier, unlike PEFT's alpha parameter.
                "lora_parameters": {
                    "rank": train["rank"],
                    "scale": train["alpha"] / train["rank"],
                    "dropout": 0.0,
                },
            }
        )
    )

    class LossLog(TrainingCallback):
        def record(self, kind, info):
            for key, value in info.items():
                if "loss" in key and isinstance(value, (int, float)) and not math.isfinite(value):
                    raise RuntimeError(f"Nonfinite {key}; training aborted")
            with (directory / "loss.jsonl").open("a") as handle:
                handle.write(json.dumps({"kind": kind, **info}) + "\n")

        def on_train_loss_report(self, info):
            self.record("train", info)

        def on_val_loss_report(self, info):
            self.record("validation", info)

    print(f"Training seed={seed}, N={len(rows)}, {iters} updates", flush=True)
    train_model(args, model, training_set, validation_set, LossLog())
    mx.eval(model.trainable_parameters())
    checksum = hashlib.sha256((directory / "adapters.safetensors").read_bytes()).hexdigest()
    marker.write_text(
        json.dumps(
            {"identity": identity, "iterations": iters, "weights_sha256": checksum}, indent=2
        )
        + "\n"
    )
    del model, tokenizer, training_set, validation_set
    gc.collect()
    mx.clear_cache()
    return directory
