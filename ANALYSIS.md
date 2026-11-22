# LoRA vs. Persistent ICL: Preliminary Results

**Analysis date:** November 22, 2026  
**Experiment:** `full-keywords-v3`  
**Model:** Qwen3.5-2B, FP16, running locally with MLX

## Summary

The simplified synthetic language produces nonzero accuracy, resolving the flat-zero outcome of the original language. However, increasing the number of in-context examples improves syntax compliance more clearly than functional correctness. The available LoRA results suggest stronger syntax acquisition at N=64, alongside severe ordinary-Python output degradation at N=16. The experiment is incomplete, so neither a reliable LoRA/ICL crossover nor forgetting relative to the clean base model can yet be established.

This analysis covers **6,027 of 12,306 planned evaluations (49.0%)**. All ICL evaluations are complete, but most LoRA evaluations and all clean-base evaluations are missing. Missing results are not counted as failures.

## Experimental setup

The experiment compares persistent in-context learning (ICL) and LoRA adaptation using N=16, 64, or 256 MBPP examples. Three seeds vary example selection and generation. Evaluation covers synthetic-language HumanEval, ordinary-Python HumanEval, AIME 2024, AIME 2025, and GPQA Diamond.

The `keywords-v3` language replaces selected Python keywords with short pseudo-words, such as `def → pil` and `return → wert`. Punctuation, operators, identifiers, builtins, imports (`import`, `from`, `as`), and literal words (`True`, `False`, `None`) remain unchanged. Synthetic task signatures are translated into the same syntax. Outputs containing untranslated mapped keywords are rejected rather than silently repaired.

Generation uses temperature 0.6, top-p 0.95, top-k 20, a maximum of 2,048 output tokens, and thinking disabled. Each task receives one sampled completion. Code scores are pass@1 against the benchmark tests; math and QA scores use exact final-answer extraction.

LoRA uses rank 8, alpha 16, the last 16 transformer layers, three epochs, learning rate 1e-4, and assistant-only training loss. Persistent ICL retains the synthetic-language grammar and demonstrations when answering unrelated tasks; LoRA receives a clean prompt with its adapter active.

## Evaluation coverage

| Condition | Completed | Planned | Coverage |
|---|---:|---:|---:|
| ICL | 5,274 | 5,274 | 100.0% |
| LoRA | 753 | 5,274 | 14.3% |
| Clean base | 0 | 1,758 | 0.0% |

All nine ICL combinations of example count and seed are complete. For LoRA, N=16 has all five benchmarks for seed 0. N=64 has synthetic HumanEval for seed 0 and only three ordinary-Python tasks. The latter three tasks are excluded from substantive model comparisons.

## ICL results

The following scores aggregate the three seeds. Per N, the denominators are 492 evaluations for each code benchmark, 90 for each AIME year, and 594 for GPQA. These are repeated evaluations of the same tasks, not independent samples of that many distinct problems.

| Examples (N) | Synthetic pass@1 | Synthetic parse validity | Python pass@1 | AIME 2024 | AIME 2025 | GPQA |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 4.67% | 30.28% | 46.95% | 5.56% | 3.33% | 20.03% |
| 64 | 5.89% | 41.26% | 45.53% | 2.22% | 1.11% | 21.38% |
| 256 | 5.28% | 42.07% | 42.48% | 1.11% | 1.11% | 18.69% |

### Synthetic-language acquisition

Increasing N from 16 to 64 substantially improves parse validity, but functional accuracy rises by only 1.22 percentage points. Increasing N to 256 does not improve accuracy further. Paired task-bootstrap intervals for both accuracy changes relative to N=16 include zero.

Among parse-valid synthetic programs, pass rates are 15.44%, 14.29%, and 12.56% for N=16, 64, and 256 respectively. Thus, producing syntactically valid code remains distinct from solving the task correctly.

### Was the 5–10% target reached consistently?

| Examples (N) | Seed 0 | Seed 1 | Seed 2 |
|---:|---:|---:|---:|
| 16 | 6.71% | 4.27% | 3.05% |
| 64 | 4.27% | 7.93% | 5.49% |
| 256 | 1.22% | 6.71% | 7.93% |

The flat-zero problem is resolved, but **consistent 5–10% accuracy at N=16 is not established**: only one of the three seeds reaches 5%.

The first 32 HumanEval tasks were used for exploratory calibration. At N=16, that subset scores 6/96 (6.25%), while the remaining 132 tasks score 17/396 (4.29%). These subsets should be reported separately, and pilot results should not be pooled with the full sweep because they repeat the same task/seed combinations. The remaining tasks were held out from the `keywords-v3` pilot, but HumanEval had earlier exploratory exposure under the old grammar; this is not a pristine external test set.

### Untargeted tasks

Ordinary-Python accuracy decreases from 46.95% at N=16 to 42.48% at N=256. The paired difference is −4.47 percentage points, with a descriptive 95% task-bootstrap interval of [−8.54, −0.41]. This suggests a modest decline with longer persistent context in the observed seeds, but it is not an estimate of interference relative to the unadapted model because the clean-base evaluations are missing.

AIME scores are near the floor, and GPQA scores fluctuate without a clear monotonic trend. Answer completion and extraction failures substantially complicate their interpretation.

## Matched LoRA comparisons

LoRA must be compared with ICL using the same N, seed, and task set. All available complete comparisons below use **seed 0 only**, rather than comparing one LoRA seed against a three-seed ICL average.

| Benchmark | N | ICL | LoRA | LoRA − ICL |
|---|---:|---:|---:|---:|
| Synthetic HumanEval | 16 | 6.71% | 4.88% | −1.83 pp |
| Synthetic HumanEval | 64 | 4.27% | 7.93% | +3.66 pp |
| Ordinary-Python HumanEval | 16 | 40.85% | 0.61% | −40.24 pp |
| AIME 2024 | 16 | 3.33% | 0.00% | −3.33 pp |
| AIME 2025 | 16 | 3.33% | 3.33% | 0.00 pp |
| GPQA Diamond | 16 | 18.69% | 20.20% | +1.52 pp |

### Stronger syntax acquisition at N=64

For synthetic HumanEval at N=64, LoRA produces 138/164 parse-valid programs (84.15%), compared with 75/164 (45.73%) for matched ICL. It passes 13 tasks, compared with ICL's seven.

This is a promising syntax-acquisition signal. However, the paired interval for the pass-rate difference is [−1.22, +9.15] percentage points, and only one seed is available. These results do not establish a reliable crossover in which LoRA overtakes ICL as N increases.

### Severe ordinary-Python degradation at N=16

The N=16 adapter passes only **1/164** ordinary-Python tasks, versus **67/164** for matched ICL. Its outcomes are:

| Outcome | Count |
|---|---:|
| Parse error | 82 |
| Missing required function | 52 |
| Failed tests | 29 |
| Passed | 1 |

In addition, 127/164 outputs (77.44%) hit the output-token cap. Token-limit events overlap the outcome categories above and should not be added to them. A representative trace repeatedly emits imports until reaching the cap.

This is evidence of severe output degeneration or task-compliance failure with the active adapter. It does not by itself establish irreversible loss of knowledge, identify the cause, or prove a training bug. The three available N=64 Python results are insufficient to determine whether more training examples resolve the problem.

## Answer extraction and truncation

ICL GPQA exact accuracy ranges from 18.69% to 21.38%, below the 25% uniform-choice reference. However, only 51–55% of responses contain a recognized final answer. Conditional accuracy among those responses is approximately 35–39%.

That conditional accuracy is selection-biased and should not replace the official score. It does show that failing to finish or format the final answer is a material component of the low exact accuracy. Between 27% and 38% of ICL GPQA outputs hit the token cap.

For AIME, exact accuracy ranges from 1.11% to 5.56%. Depending on N and year, roughly 31–63% of outputs hit the cap, and many lack the required final integer. These observations do not isolate mathematical reasoning ability from generation-budget and answer-format effects.

LoRA N=16 has even higher truncation rates: 93.33% on AIME 2024, 86.67% on AIME 2025, and 65.15% on GPQA. No outputs were permissively rescored for this analysis.

## Training diagnostics

| Adapter | Updates | Final training loss | Initial validation loss | Final validation loss | Peak training memory |
|---|---:|---:|---:|---:|---:|
| Seed 0, N=16 | 48 | 0.252 | 2.020 | 1.173 | 8.65 GB |
| Seed 0, N=64 | 192 | 0.161 | 2.020 | 1.074 | 8.64 GB |

Both available adapters have finite logged losses and verified weight checksums. The losses decrease, but this does not demonstrate successful transfer to the evaluation tasks or preservation of unrelated capabilities. Training and validation examples also differ in difficulty, so their loss gap alone is not a definitive diagnosis of overfitting.

## What the results support

The current evidence supports three preliminary observations:

1. Short keyword substitutions make the synthetic task learnable to a limited extent, but the N=16 target is not consistently achieved across seeds.
2. More ICL examples improve syntax compliance more than functional correctness. The available N=64 LoRA adapter improves syntax compliance further, without enough evidence to establish superior task accuracy.
3. The N=16 adapter exhibits severe ordinary-Python output degradation, while math and QA outcomes are heavily affected by missing final answers and truncation.

The main project hypotheses remain unresolved. A reliable acquisition crossover requires more LoRA seeds and N=256 results. Symmetric interference relative to the clean base model requires the missing baseline evaluations.

## Limitations

- Only 49% of the planned matrix is present, and LoRA coverage is concentrated in seed 0.
- No clean-base results are available. Comparisons between LoRA and ICL cannot substitute for degradation relative to base.
- The grammar and prompt were adapted using exploratory results. Calibration tasks are not an independent test set.
- Only one synthetic-language mapping was evaluated.
- Repeated evaluations share task identities. Uncertainty calculations must preserve this dependence.
- The reported paired intervals use 10,000 bootstrap resamples of task IDs, keeping observed seed pairs together. They are conditional on the observed seeds and language, not intervals over new training seeds or language mappings. No multiple-comparison correction was applied.
- Old-language, intermediate-pilot, and smoke results are excluded from the main estimates because their grammars, prompts, or evaluation scopes differ.

## Recommended next steps

1. **Run clean-base evaluations.** These provide the missing reference for the interference question and can be executed independently of unfinished LoRA jobs.
2. **Diagnose the N=16 adapter before extending the sweep.** Use fixed Python and QA probes to compare adapter off/on, inspect repetitive outputs, and verify prompt/EOS masking. If warranted, test lower learning rates or fewer epochs in separately named runs.
3. **Complete LoRA replication and N=256.** Additional seeds are necessary before interpreting the apparent syntax advantage as a reliable acquisition crossover.
4. **Separate formatting and token-budget effects.** Use a predeclared follow-up with controlled decoding or answer-format changes, preserving the original sweep's scores.
5. **Freeze the grammar for the remaining comparisons.** Further tuning on HumanEval would weaken the interpretation of held-out performance.

## Artifacts and reproducibility

This write-up summarizes the November 22 snapshot without modifying raw traces or scores. The detailed analysis directory contains per-seed coverage, compact trial records, outcome counts, paired comparisons, calibration/confirmation splits, training diagnostics, and a chart.

- [Detailed report](runs/full-keywords-v3/analysis-2026-11-22/report.md)
- [Aggregated metrics](runs/full-keywords-v3/analysis-2026-11-22/metrics.csv)
- [Coverage by seed](runs/full-keywords-v3/analysis-2026-11-22/coverage_by_seed.csv)
- [Paired comparisons](runs/full-keywords-v3/analysis-2026-11-22/paired_comparisons.csv)
- [ICL chart](runs/full-keywords-v3/analysis-2026-11-22/icl_summary.png)
- [Snapshot metadata and checksum](runs/full-keywords-v3/analysis-2026-11-22/snapshot.json)
- [Reproducible analysis script](scripts/analyze_results.py)

The script reads and verifies the fixed 253,683,271-byte snapshot prefix. Later appended evaluations do not silently change this dated analysis.
