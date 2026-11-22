"""Compile an immutable, bounded snapshot without editing experiment code or raw results."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import statistics
from pathlib import Path

import numpy as np


def export(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


SNAPSHOT_BYTES = 253683271
SNAPSHOT_SHA256 = "56d03bf1c7e126fa20cba9df1f1233070355ad1a5b8f35138408c84566c28bd6"


def snapshot(path, limit=None):
    size = path.stat().st_size if limit is None else limit
    if path.stat().st_size < size:
        raise ValueError("Source is shorter than the archived snapshot")
    digest = hashlib.sha256()
    rows, incomplete = [], 0
    with path.open("rb") as source:
        while source.tell() < size:
            data = source.readline(size - source.tell())
            digest.update(data)
            try:
                row = json.loads(data)
            except ValueError:
                if source.tell() != size:
                    raise
                incomplete += 1
                continue
            row.pop("messages", None)
            rows.append(row)
    keys = [r["key"] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate evaluation keys; refusing to double-count")
    return rows, {"bytes": size, "sha256": digest.hexdigest(), "incomplete_final_lines": incomplete}


def stats(rows):
    count = len(rows)
    parsed = sum(r.get("parse_valid", False) for r in rows)
    passed = sum(r["passed"] for r in rows)
    code = bool(rows) and rows[0]["benchmark"].startswith("humaneval")
    answered = sum(r.get("answer") is not None for r in rows)
    return {
        "evaluations": count,
        "passes": passed,
        "accuracy": passed / count if count else None,
        "parse_valid": parsed if code else None,
        "parse_rate": parsed / count if code and count else None,
        "pass_given_parse": passed / parsed if code and parsed else None,
        "answers_extracted": answered if not code else None,
        "answer_coverage": answered / count if not code and count else None,
        "accuracy_given_answer": passed / answered if not code and answered else None,
        "length_capped": sum(r.get("finish_reason") == "length" for r in rows),
        "generation_hours": sum(r.get("seconds", 0) for r in rows) / 3600,
    }


def paired(left, right):
    """Right minus left; resample tasks, keeping all observed seed pairs together."""
    a = {(r["seed"], r["task_id"]): r for r in left}
    b = {(r["seed"], r["task_id"]): r for r in right}
    common = sorted(a.keys() & b.keys())
    by_task = collections.defaultdict(list)
    wins = losses = 0
    for k in common:
        delta = int(b[k]["passed"]) - int(a[k]["passed"])
        by_task[k[1]].append(delta)
        wins += delta > 0
        losses += delta < 0
    if not common:
        return {}
    values = np.array([np.mean(v) for v in by_task.values()])
    rng = np.random.default_rng(182)
    means = rng.choice(values, size=(10000, len(values))).mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return {
        "paired_evaluations": len(common),
        "distinct_tasks": len(values),
        "paired_seeds": len({k[0] for k in common}),
        "left_accuracy": sum(a[k]["passed"] for k in common) / len(common),
        "right_accuracy": sum(b[k]["passed"] for k in common) / len(common),
        "delta": float(values.mean()),
        "ci_low": float(low),
        "ci_high": float(high),
        "right_only_passes": wins,
        "left_only_passes": losses,
    }


def pct(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("runs/full-keywords-v3"))
    parser.add_argument(
        "--out", type=Path, default=Path("runs/full-keywords-v3/analysis-2026-11-22")
    )
    args = parser.parse_args()
    root, out = args.run, args.out
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "manifest.json").read_text())
    rows, source = snapshot(root / "results.jsonl", SNAPSHOT_BYTES)
    if source["sha256"] != SNAPSHOT_SHA256:
        raise ValueError(
            "This narrative analyzes the November 22 snapshot only; input checksum changed"
        )
    for name, expected_hash in manifest["datasets"].items():
        path = Path(manifest["config"]["experiment"]["data_dir"]) / f"{name}.jsonl"
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Dataset does not match the run manifest: {name}")
    groups = collections.defaultdict(list)
    aggregates = collections.defaultdict(list)
    for r in rows:
        groups[(r["condition"], r["n"], r["seed"], r["benchmark"])].append(r)
        aggregates[(r["condition"], r["n"], r["benchmark"])].append(r)
    cfg = manifest["config"]["experiment"]
    counts = manifest["plan"]["tasks_per_benchmark"]
    expected_keys = set()
    for condition in ("icl", "lora", "base"):
        for n in [0] if condition == "base" else cfg["sizes"]:
            for seed in cfg["seeds"]:
                for benchmark in counts:
                    name = "humaneval" if benchmark.startswith("humaneval") else benchmark
                    tasks = [
                        json.loads(l) for l in (Path(cfg["data_dir"]) / f"{name}.jsonl").open()
                    ]
                    expected_keys.update(
                        f"{condition}/{n}/{seed}/{benchmark}/{t['id']}" for t in tasks
                    )
    actual_keys = {r["key"] for r in rows}
    if actual_keys - expected_keys:
        raise ValueError("Unexpected result keys")
    source.update(
        run=str(root.resolve()),
        manifest_identity=manifest["identity"],
        language_version=manifest.get("language_version"),
        completed=len(rows),
        planned=len(expected_keys),
        missing=len(expected_keys - actual_keys),
    )
    (out / "snapshot.json").write_text(json.dumps(source, indent=2) + "\n")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    coverage = []
    for c in ("icl", "lora", "base"):
        for n in [0] if c == "base" else cfg["sizes"]:
            for s in cfg["seeds"]:
                for b, expected in counts.items():
                    rs = groups.get((c, n, s, b), [])
                    coverage.append(
                        dict(
                            condition=c,
                            n=n,
                            seed=s,
                            benchmark=b,
                            expected=expected,
                            coverage="complete"
                            if len(rs) == expected
                            else "partial"
                            if rs
                            else "missing",
                            **stats(rs),
                        )
                    )
    export(out / "coverage_by_seed.csv", coverage)
    summary = []
    for (c, n, b), rs in sorted(aggregates.items()):
        seeds = sorted({r["seed"] for r in rs})
        complete = [s for s in seeds if len(groups[(c, n, s, b)]) == counts[b]]
        rates = [stats(groups[(c, n, s, b)])["accuracy"] for s in complete]
        summary.append(
            dict(
                condition=c,
                n=n,
                benchmark=b,
                seeds_observed=len(seeds),
                complete_seeds=len(complete),
                planned_seeds=len(cfg["seeds"]),
                expected_evaluations=counts[b] * len(cfg["seeds"]),
                seed_std=statistics.stdev(rates) if len(rates) > 1 else None,
                **stats(rs),
            )
        )
    export(out / "metrics.csv", summary)
    export(
        out / "trials.csv",
        [
            {
                k: r.get(k)
                for k in [
                    "key",
                    "condition",
                    "n",
                    "seed",
                    "benchmark",
                    "task_id",
                    "passed",
                    "parse_valid",
                    "status",
                    "answer",
                    "expected",
                    "finish_reason",
                    "prompt_tokens",
                    "cached_tokens",
                    "generation_tokens",
                    "seconds",
                ]
            }
            for r in rows
        ],
    )
    failures = []
    for (c, n, b), rs in sorted(aggregates.items()):
        for status, count in sorted(collections.Counter(r["status"] for r in rs).items()):
            failures.append(
                {
                    "condition": c,
                    "n": n,
                    "benchmark": b,
                    "status": status,
                    "count": count,
                    "rate": count / len(rs),
                }
            )
    export(out / "outcomes.csv", failures)
    comparisons = []
    for b in counts:
        for n in (64, 256):
            v = paired(aggregates.get(("icl", 16, b), []), aggregates.get(("icl", n, b), []))
            if v:
                comparisons.append(dict(benchmark=b, comparison=f"ICL {n} minus ICL 16", **v))
        for n in cfg["sizes"]:
            # Only completed benchmark/seed cells enter model comparisons.
            seeds = [
                s
                for s in cfg["seeds"]
                if len(groups.get(("lora", n, s, b), [])) == counts[b]
                and len(groups.get(("icl", n, s, b), [])) == counts[b]
            ]
            v = paired(
                [r for r in aggregates.get(("icl", n, b), []) if r["seed"] in seeds],
                [r for r in aggregates.get(("lora", n, b), []) if r["seed"] in seeds],
            )
            if v:
                comparisons.append(dict(benchmark=b, comparison=f"LoRA minus ICL, N={n}", **v))
    export(out / "paired_comparisons.csv", comparisons)
    splits = []
    for (c, n, s, b), rs in sorted(groups.items()):
        if b != "humaneval_synthetic":
            continue
        for label, lower, upper in [("calibration", 0, 32), ("confirmation", 32, 164)]:
            part = [r for r in rs if lower <= int(r["task_id"].split("/")[-1]) < upper]
            splits.append(
                dict(condition=c, n=n, seed=s, split=label, expected=upper - lower, **stats(part))
            )
    export(out / "synthetic_calibration_confirmation.csv", splits)
    training = []
    for path in sorted((root / "adapters").glob("*/complete.json")):
        complete = json.loads(path.read_text())
        config = json.loads((path.parent / "adapter_config.json").read_text())
        loss = [json.loads(l) for l in (path.parent / "loss.jsonl").open()]
        val = [r for r in loss if r["kind"] == "validation"]
        train = [r for r in loss if r["kind"] == "train"]
        actual_hash = hashlib.sha256(
            (path.parent / "adapters.safetensors").read_bytes()
        ).hexdigest()
        training.append(
            {
                "adapter": path.parent.name,
                "updates": complete["iterations"],
                "checksum_ok": actual_hash == complete["weights_sha256"],
                "validation_initial": val[0]["val_loss"],
                "validation_final": val[-1]["val_loss"],
                "train_loss_final": train[-1]["train_loss"],
                "peak_memory_gb": max(r.get("peak_memory", 0) for r in train),
                "learning_rate": config["learning_rate"],
            }
        )
    export(out / "training.csv", training)
    # Keep short, keyed illustrations; no benchmark answers are rewritten/rescored.
    examples = []
    for c, n, b in [("lora", 16, "humaneval_python"), ("icl", 16, "humaneval_synthetic")]:
        matches = [r for r in aggregates[(c, n, b)] if not r["passed"]]
        for r in matches[:3]:
            examples.append(
                {k: r.get(k) for k in ["key", "status", "error", "finish_reason"]}
                | {"output_excerpt": r["text"][:900]}
            )
    (out / "trace_examples.json").write_text(json.dumps(examples, indent=2) + "\n")
    make_plot(out, summary)
    report(out, rows, source, summary, coverage, comparisons, splits, training)
    print(json.dumps(source, indent=2))


def make_plot(out, summary):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullLocator

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    for ax, b, title in zip(
        axes,
        ["humaneval_synthetic", "humaneval_python", "gpqa"],
        ["Synthetic code", "Ordinary Python", "GPQA Diamond"],
    ):
        rows = [r for r in summary if r["condition"] == "icl" and r["benchmark"] == b]
        ax.errorbar(
            [r["n"] for r in rows],
            [100 * r["accuracy"] for r in rows],
            yerr=[100 * r["seed_std"] for r in rows],
            marker="o",
            capsize=4,
            color="#2463a6",
            label="ICL: 3 seeds",
        )
        if b == "humaneval_synthetic":
            ax.axhspan(5, 10, color="#57a773", alpha=0.12, label="5–10% target")
        ax.set(
            xscale="log",
            xticks=[16, 64, 256],
            xticklabels=["16", "64", "256"],
            xlabel="Examples (N)",
            ylabel="Pass@1 / accuracy (%)",
            title=title,
        )
        ax.set_ylim(bottom=0)
        ax.xaxis.set_minor_locator(NullLocator())
        ax.grid(axis="y", alpha=0.2)
        ax.legend(fontsize=9)
    fig.suptitle("Complete ICL sweep — error bars show variation across three seeds")
    fig.tight_layout()
    fig.savefig(out / "icl_summary.png", dpi=180)
    plt.close(fig)


def report(out, rows, source, summary, coverage, comparisons, splits, training):
    lines = [
        "# Results analysis — keywords-v3",
        "",
        f"Snapshot: **{source['completed']:,}/{source['planned']:,} evaluations ({source['completed'] / source['planned']:.1%})**. Raw outputs and scores are unchanged.",
        "",
        "## What is complete",
        "",
        "| Stage | Completed | Planned | Coverage |",
        "|---|---:|---:|---:|",
    ]
    for c in ["icl", "lora", "base"]:
        observed = sum(r["condition"] == c for r in rows)
        expected = sum(r["expected"] for r in coverage if r["condition"] == c)
        lines.append(f"| {c} | {observed:,} | {expected:,} | {observed / expected:.1%} |")
    lines += [
        "",
        "All nine ICL seed/example-count combinations are complete. LoRA N=16 has all five benchmarks for seed 0 only. LoRA N=64 has synthetic HumanEval for seed 0 and just 3 ordinary-Python tasks. No other LoRA cells or base evaluations are present. Missing results are not failures and are not imputed.",
        "The existing top-level report was stale (written after ICL); this analysis reads the later raw records. It does not restart or alter the sweep.",
        "",
        "## Complete ICL results",
        "",
        "| N | Synthetic code | Parse validity | Python | AIME 2024 | AIME 2025 | GPQA |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lookup = {(r["condition"], r["n"], r["benchmark"]): r for r in summary}
    for n in [16, 64, 256]:
        s = lookup["icl", n, "humaneval_synthetic"]
        values = [
            pct(lookup["icl", n, b]["accuracy"])
            for b in ["humaneval_python", "aime2024", "aime2025", "gpqa"]
        ]
        lines.append(
            f"| {n} | {pct(s['accuracy'])} ({s['passes']}/492) | {pct(s['parse_rate'])} | "
            + " | ".join(values)
            + " |"
        )
    lines += [
        "",
        "ICL denominators per N: 492 evaluations for each code benchmark (164 tasks × 3 seeds), 90 for each AIME year, and 594 for GPQA. These are repeated observations of the same tasks, not that many independent problems.",
        "",
        "![ICL accuracy and across-seed variation](icl_summary.png)",
        "",
        "### Did simplification meet the 5–10% goal?",
        "",
        "| N | Seed 0 | Seed 1 | Seed 2 | Confirmation subset (tasks 32–163) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for n in [16, 64, 256]:
        rates = [
            next(
                r
                for r in coverage
                if r["condition"] == "icl"
                and r["n"] == n
                and r["seed"] == s
                and r["benchmark"] == "humaneval_synthetic"
            )
            for s in [0, 1, 2]
        ]
        conf = [
            r
            for r in splits
            if r["condition"] == "icl" and r["n"] == n and r["split"] == "confirmation"
        ]
        lines.append(
            f"| {n} | "
            + " | ".join(f"{pct(r['accuracy'])} ({r['passes']}/164)" for r in rates)
            + f" | {pct(sum(r['passes'] for r in conf) / 396)} ({sum(r['passes'] for r in conf)}/396) |"
        )
    lines += [
        "",
        "**The flat-zero problem is resolved, but consistent 5–10% at N=16 is not established.** Its full mean is 4.67%; only seed 0 reaches 5%. The calibration subset scores 6/96 (6.25%), versus 17/396 (4.29%) on the remaining tasks. Grammar and prompt design used the first 32 tasks; treat that subset as exploratory, not independent confirmation. The pilot uses the same tasks/seeds and must not be pooled into the full sweep.",
        "More examples improve parse validity (30.28% → 41.26% → 42.07%), but functional accuracy is roughly flat (4.67% → 5.89% → 5.28%). Among parse-valid programs, pass rates are 15.44%, 14.29%, and 12.56% respectively. Syntax compliance alone is not enough to solve the programs.",
        "",
        "## Matched LoRA comparisons",
        "",
        "Compare against ICL with the same N, seed, and task set—not the three-seed ICL average. All LoRA comparisons here are **seed 0 only**.",
        "",
        "| Benchmark | N | ICL | LoRA | LoRA − ICL (percentage points) | Paired 95% interval |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in comparisons:
        if not r["comparison"].startswith("LoRA"):
            continue
        n = r["comparison"].split("=")[-1]
        lines.append(
            f"| {r['benchmark']} | {n} | {pct(r['left_accuracy'])} | {pct(r['right_accuracy'])} | {100 * r['delta']:+.2f} | [{100 * r['ci_low']:+.2f}, {100 * r['ci_high']:+.2f}] |"
        )
    lines += [
        "",
        "LoRA N=64 improves synthetic parse validity to 138/164 (84.15%), compared with 75/164 (45.73%) for matched ICL. It passes 13/164 versus 7/164. This is a promising syntax-acquisition signal, but only one seed is available. There is no complete N=256 LoRA result and no evidence yet for a reliable LoRA/ICL crossover.",
        "**N=16 LoRA has severe ordinary-Python output degradation:** 1/164 passes versus 67/164 for matched ICL. Of its 164 Python outputs, 82 are parse errors, 52 lack the entry point, 29 fail tests, and one passes; 127/164 (77.44%) hit the output-token cap. The first trace repeatedly emits imports until the cap. This supports an output-degeneration/task-compliance problem; it does not by itself establish irreversible loss of knowledge or prove a training bug.",
        "The three available N=64 ordinary-Python tasks are too few to interpret and are excluded from this comparison table. No base condition exists yet, so accuracy loss relative to the unadapted model—and hence the proposed symmetric interference comparison—cannot be estimated.",
        "",
        "## Answer extraction and truncation",
        "",
        "| Condition | N | Benchmark | Exact accuracy | Answer extracted | Correct among extracted | Token-cap rate |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for r in summary:
        if r["benchmark"].startswith("humaneval"):
            continue
        lines.append(
            f"| {r['condition']} | {r['n']} | {r['benchmark']} | {pct(r['accuracy'])} | {pct(r['answer_coverage'])} | {pct(r['accuracy_given_answer'])} | {pct(r['length_capped'] / r['evaluations'])} |"
        )
    lines += [
        "",
        "GPQA ICL exact accuracy is 18.69–21.38%, below the 25% uniform-choice reference, but only about half the outputs yield a recognized final answer. Accuracy conditional on extraction is 35–39%. That conditional metric is selection-biased and is not a replacement score; it shows that answer completion/formatting materially contributes to failure. Missing answers and token caps overlap and must not be added.",
        "AIME accuracy is near the floor (1.11–5.56%). Many responses lack the required final integer and/or hit the 2,048-token limit. These results cannot distinguish reasoning limitations from generation-budget and answer-format failures without additional controlled experiments. No outputs were permissively rescored.",
        "",
        "## Uncertainty and limitations",
        "",
        "Paired intervals use 10,000 bootstrap resamples of task IDs, retaining all observed seed pairs together (RNG seed 182). They are descriptive percentile intervals conditional on these seeds, not confidence intervals over new training seeds or languages. No multiplicity correction is applied. Individual-seed variability is shown separately; repeated task/seed observations are not treated as independent trials.",
        "",
        "| ICL contrast | Benchmark | Difference (pp) | Paired 95% interval |",
        "|---|---|---:|---:|",
    ]
    for r in comparisons:
        if r["comparison"].startswith("ICL"):
            lines.append(
                f"| {r['comparison']} | {r['benchmark']} | {100 * r['delta']:+.2f} | [{100 * r['ci_low']:+.2f}, {100 * r['ci_high']:+.2f}] |"
            )
    lines += [
        "",
        "The old all-token language, intermediate v2 pilots, and smoke runs use different grammars/prompts or task sets. They are excluded from the main estimates. The old 0/164 synthetic result is useful development history, not a controlled estimate of the effect of changing only the language. Only one language mapping was evaluated. The remaining 132 tasks were not used in the keywords-v3 pilot, but HumanEval had earlier exploratory exposure under the old grammar; confirmation here means held out from that pilot, not an entirely untouched external benchmark.",
        "",
        "## Training and resource audit",
        "",
        "| Adapter | Updates | Final train loss | Validation: initial → final | Peak training GB | Checksum |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in training:
        lines.append(
            f"| {r['adapter']} | {r['updates']} | {r['train_loss_final']:.3f} | {r['validation_initial']:.3f} → {r['validation_final']:.3f} | {r['peak_memory_gb']:.2f} | {'verified' if r['checksum_ok'] else 'MISMATCH'} |"
        )
    hours = sum(r["seconds"] for r in rows) / 3600
    lines += [
        "",
        f"Saved generation timings sum to {hours:.2f} hours. This excludes training, model loading, prefix prefill outside generation, scoring, and idle time, so it is not total wall time. Both available adapters have finite logged losses and matching weight checksums. Lower loss does not guarantee task success; training and validation example difficulty differ.",
        "",
        "## Recommended next steps",
        "",
        "1. Run the missing clean-base evaluations before drawing forgetting/interference conclusions. They are independent of the unfinished LoRA jobs and provide the missing reference.",
        "2. Inspect and diagnose the N=16 adapter on a fixed set of Python and QA probes before spending compute on the remaining LoRA matrix. Compare adapter off/on, verify prompt/EOS masking, inspect repetitive generations, then test lower learning rate/fewer epochs in separately named runs if warranted. The present results do not isolate which factor is responsible.",
        "3. Finish LoRA seed replication and N=256 before claiming a targeted-acquisition crossover. Preserve the current grammar; further tuning on HumanEval would weaken the held-out interpretation.",
        "4. Separate answer-format compliance and token-budget effects with a predeclared follow-up. Do not mix modified prompts, decoding limits, or permissive scoring with this sweep.",
        "",
        "## Reproducibility",
        "",
        "Inputs: `../results.jsonl` and `../manifest.json`. `snapshot.json` records the exact byte boundary and SHA-256 of the raw snapshot; `manifest.json` copies its run configuration. `trials.csv` has one compact row per evaluation; `coverage_by_seed.csv` includes missing cells; other CSVs contain metrics, outcomes, matched contrasts, calibration/confirmation splits, and training diagnostics. `trace_examples.json` contains short keyed failure excerpts. Original raw outputs remain intact. The analysis script reads the fixed 253,683,271-byte prefix and verifies its checksum, so later appended evaluations do not silently change this dated report. A newer snapshot requires updating the analysis and its narrative.",
        "",
        "Rebuild with `uv run python scripts/analyze_results.py --run runs/full-keywords-v3 --out runs/full-keywords-v3/analysis-2026-11-22`.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
