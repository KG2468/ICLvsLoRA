# Full FP16 sweep

This is the canonical run directory for `configs/full.toml`. Raw prompts, model traces, retries, per-task scores and worker telemetry are in `results.jsonl`. `adapters/` holds all nine verified training checkpoints. `provenance/` preserves the original manifests, source counts and imported Colab task IDs. The root manifest identifies the local runner used for resumption. Source manifests identify the platforms and weight hashes used elsewhere.

## Coverage at consolidation

Each completed condition, seed and N contains 586 evaluations. The three columns within each adaptation method are N=16, 64 and 256.

| Seed | Base | ICL 16 / 64 / 256 | LoRA 16 / 64 / 256 |
|---|---:|---|---|
| 0 | 586 | 586 / 586 / 586 | 586 / 586 / 586 |
| 1 | 586 | 586 / 586 / 586 | 0 / 0 / 0 |
| 2 | 586 | 586 / 360 / 0 | 0 / 0 / 0 |

7,978 of 12,306 evaluation rows are present. Remaining work totals 812 ICL and 3,516 LoRA evaluations. [Seed 0 analysis](analysis/seed-0.md) covers all paired tasks. [Sweep report](report.md) includes partial groups. The root selection files record the training and validation IDs for jobs already started.

## Import another snapshot

Place a snapshot directory containing both `results.jsonl` and `manifest.json` under `incoming/`. From the project root run:

```sh
RUN=runs/full-keywords-v4-reviewed-gpu-v2
uv run python scripts/import_sweep_results.py "$RUN/incoming/<snapshot>"
uv run final-project report "$RUN"
```

The importer takes the runner lock, checks experiment inputs, skips identical rows, and rejects conflicting traces for the same key. New imports record their manifest and added keys under `provenance/imports/`. The coverage table above is a dated snapshot of the consolidation; the regenerated report tracks subsequent imports.
