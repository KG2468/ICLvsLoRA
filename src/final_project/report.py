from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .config import read_jsonl


def summarize(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["benchmark"], row["condition"], row["n"], row["seed"])].append(row)
    base = {
        (b, seed): statistics.mean(float(r["passed"]) for r in group)
        for (b, condition, n, seed), group in groups.items()
        if condition == "base"
    }
    base_ids = {
        (b, seed): {r.get("task_id", i) for i, r in enumerate(group)}
        for (b, condition, n, seed), group in groups.items()
        if condition == "base"
    }
    aggregated = defaultdict(list)
    for (benchmark, condition, n, seed), group in groups.items():
        accuracy = statistics.mean(float(r["passed"]) for r in group)
        parse = [float(r["parse_valid"]) for r in group if "parse_valid" in r]
        paired = base_ids.get((benchmark, seed)) == {
            r.get("task_id", i) for i, r in enumerate(group)
        }
        generations = [attempt for row in group for attempt in (row, row.get("followup", {}))]
        gpu = [attempt["gpu"] for attempt in generations if "gpu" in attempt]
        aggregated[(benchmark, condition, n)].append(
            {
                "accuracy": accuracy,
                "parse_validity": statistics.mean(parse) if parse else None,
                "delta": accuracy - base[(benchmark, seed)] if paired else None,
                "tasks": len(group),
                "seconds": sum(attempt.get("seconds", 0) for attempt in generations),
                "peak_bytes": max((g["mlx_peak_bytes"] for g in gpu), default=None),
                "samples": sum(g["samples"] for g in gpu),
                "busy_sum": sum(
                    g["samples"] * (g["device_utilization_mean_pct"] or 0) for g in gpu
                ),
                "workers": max(
                    (r["generation_workers"] for r in group if "generation_workers" in r),
                    default=None,
                ),
            }
        )
    summary = []
    for (benchmark, condition, n), values in sorted(aggregated.items()):
        accuracy = [v["accuracy"] for v in values]
        parses = [v["parse_validity"] for v in values if v["parse_validity"] is not None]
        deltas = [v["delta"] for v in values if v["delta"] is not None]
        samples = sum(v["samples"] for v in values)
        summary.append(
            {
                "benchmark": benchmark,
                "condition": condition,
                "n": n,
                "seeds": len(values),
                "tasks": sum(v["tasks"] for v in values),
                "accuracy": statistics.mean(accuracy),
                "seed_std": statistics.stdev(accuracy) if len(accuracy) > 1 else None,
                "parse_validity": statistics.mean(parses) if parses else None,
                "delta_from_base": statistics.mean(deltas) if deltas else None,
                "paired_seeds": len(deltas),
                "generation_seconds": sum(v["seconds"] for v in values),
                "worker_peak_mlx_gb": max(
                    (v["peak_bytes"] / 1e9 for v in values if v["peak_bytes"] is not None),
                    default=None,
                ),
                "device_utilization_mean_pct": sum(v["busy_sum"] for v in values) / samples
                if samples
                else None,
                "gpu_samples": samples,
                "max_generation_workers": max(
                    (v["workers"] for v in values if v["workers"] is not None), default=None
                ),
            }
        )
    return summary


def report(root: Path):
    rows = read_jsonl(root / "results.jsonl")
    summary = summarize(rows)
    manifest = json.loads((root / "manifest.json").read_text())
    expected = manifest["plan"]["evaluations"]
    status = "COMPLETE" if len(rows) == expected else "PARTIAL"
    (root / "summary.json").write_text(
        json.dumps(
            {"status": status, "completed": len(rows), "expected": expected, "groups": summary},
            indent=2,
        )
    )
    if not summary:
        return
    with (root / "summary.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    lines = [
        f"# Experiment: {root.name}",
        "",
        f"{status}: {len(rows)}/{expected} evaluations.",
        "",
        "One sampled completion per task (pass@1 for code; exact-match accuracy otherwise).",
        "Seed standard deviations describe repeat variability, not confidence intervals.",
        "Positive delta means better than base; negative delta means interference.",
        "",
        "| Benchmark | Condition | N | Seeds | Accuracy | Parse validity | Delta vs base |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        fmt = lambda x: f"{100 * x:.1f}%" if x is not None else "—"
        lines.append(
            f"| {r['benchmark']} | {r['condition']} | {r['n']} | {r['seeds']} | "
            f"{fmt(r['accuracy'])} | {fmt(r['parse_validity'])} | {fmt(r['delta_from_base'])} |"
        )
    lines += [
        "",
        "Small smoke runs verify plumbing only; they do not establish the research hypotheses.",
    ]
    (root / "report.md").write_text("\n".join(lines) + "\n")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    benchmarks = sorted({r["benchmark"] for r in summary})
    fig, axes = plt.subplots(1, len(benchmarks), figsize=(5 * len(benchmarks), 4), squeeze=False)
    for ax, benchmark in zip(axes[0], benchmarks):
        for condition in ["base", "icl", "lora"]:
            points = sorted(
                [r for r in summary if r["benchmark"] == benchmark and r["condition"] == condition],
                key=lambda r: r["n"],
            )
            if condition == "base" and points:
                ax.axhline(points[0]["accuracy"], color="gray", linestyle="--", label="base")
            elif points:
                ax.errorbar(
                    [r["n"] for r in points],
                    [r["accuracy"] for r in points],
                    yerr=[r["seed_std"] or 0 for r in points],
                    marker="o",
                    label=condition,
                )
        ax.set(
            title=benchmark,
            xlabel="Training / ICL examples (N)",
            ylabel="Accuracy",
            ylim=(-0.05, 1.05),
        )
        ax.legend()
    fig.suptitle(f"{root.name} ({status.lower()})")
    fig.tight_layout()
    fig.savefig(root / "accuracy.png", dpi=160)
    plt.close(fig)
    print(f"Report: {root / 'report.md'}", flush=True)
