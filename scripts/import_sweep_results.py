"""Merge a completed or partial evaluation snapshot into the full sweep."""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from final_project.config import digest, load_config
from final_project.data import tasks


def read(path):
    return json.loads(path.read_text())


def merge(source, root):
    manifest = read(source / "manifest.json")
    target = read(root / "manifest.json")
    cfg = target["config"]
    exp = cfg["experiment"]
    src_cfg = manifest["config"]
    # Sandbox selection is host-specific. Generation and training settings must agree.
    normalized = {**src_cfg, "evaluation": {**src_cfg["evaluation"], "sandbox": cfg["evaluation"]["sandbox"]}}
    if normalized != cfg:
        raise ValueError("Source experiment configuration differs")
    batches = {b: tasks(cfg, b) for b in exp["benchmarks"]}
    ids = {b: {t["id"] for t in rows} for b, rows in batches.items()}
    if "datasets" in manifest:
        if manifest["datasets"] != target["datasets"] or manifest["language_mappings_by_seed"] != target["language_mappings_by_seed"]:
            raise ValueError("Dataset or language mapping mismatch")
        weights = manifest["weights"]
    else:
        adapter = root / "adapters" / f"seed{manifest['seed']}-n{manifest['n']}"
        if manifest["tasks"] != digest(batches) or manifest["checkpoint"] != read(adapter / "complete.json"):
            raise ValueError("Task or adapter identity mismatch")
        weights = manifest["model"]
    known = [target["weights"], read(root / "provenance/server-icl/manifest.json")["weights"]]
    if not any(all(weights.get(k) == v for k, v in artifact.items()) for artifact in known):
        raise ValueError("Unrecognized model or tokenizer checksum")
    path = root / "results.jsonl"
    with (root / ".lock").open("a") as lock, tempfile.TemporaryDirectory(dir=root) as tmp:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        seen = {}
        with path.open("rb") as local:
            for line in local:
                row = json.loads(line)
                key = row["key"]
                if key in seen:
                    raise ValueError(f"Duplicate local key: {key}")
                seen[key] = digest(row)
        staged = Path(tmp) / "results.jsonl"
        shutil.copyfile(path, staged)
        added = []
        snapshot = hashlib.sha256()
        with staged.open("ab") as out, (source / "results.jsonl").open("rb") as incoming:
            for line in incoming:
                snapshot.update(line)
                r = json.loads(line)
                c, n, s, b, t = (r[k] for k in ("condition", "n", "seed", "benchmark", "task_id"))
                key = f"{c}/{n}/{s}/{b}/{t}"
                if (key != r["key"] or s not in exp["seeds"] or t not in ids[b]
                        or c not in ("base", "icl", "lora") or n not in ([0] if c == "base" else exp["sizes"])
                        or r["generation_seed"] != int(digest([s, b, t])[:8], 16)):
                    raise ValueError(f"Unexpected evaluation: {key}")
                if "checkpoint" in manifest and (c, s, n) != ("lora", manifest["seed"], manifest["n"]):
                    raise ValueError(f"Row outside checkpoint selection: {key}")
                fingerprint = digest(r)
                if key in seen:
                    if fingerprint != seen[key]:
                        raise ValueError(f"Conflicting traces: {key}")
                    continue
                seen[key] = fingerprint
                added.append(key)
                out.write(line.rstrip(b"\n") + b"\n")
            out.flush()
            os.fsync(out.fileno())
        if added:
            receipt = root / "provenance" / "imports" / snapshot.hexdigest()
            receipt.mkdir(parents=True, exist_ok=True)
            (receipt / "manifest.json").write_text(json.dumps(manifest, indent=2))
            (receipt / "keys.json").write_text(json.dumps(added, indent=2))
            staged.replace(path)
        print(f"{len(added)} new rows; {len(seen)} unique evaluations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Directory containing manifest.json and results.jsonl")
    args = parser.parse_args()
    experiment = load_config("configs/full.toml")["experiment"]
    merge(args.snapshot, Path(experiment["output_dir"]) / experiment["name"])
