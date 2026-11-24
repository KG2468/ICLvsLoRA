# Experiment: full-keywords-v4-reviewed-gpu-v2

PARTIAL: 7978/12306 evaluations.

One sampled completion per task (pass@1 for code; exact-match accuracy otherwise).
Seed standard deviations describe repeat variability, not confidence intervals.
Positive delta means better than base; negative delta means interference.

| Benchmark | Condition | N | Seeds | Accuracy | Parse validity | Delta vs base |
|---|---|---:|---:|---:|---:|---:|
| aime2024 | base | 0 | 3 | 4.4% | — | 0.0% |
| aime2024 | icl | 16 | 3 | 4.4% | — | 0.0% |
| aime2024 | icl | 64 | 3 | 4.4% | — | 0.0% |
| aime2024 | icl | 256 | 2 | 3.3% | — | -1.7% |
| aime2024 | lora | 16 | 1 | 3.3% | — | 0.0% |
| aime2024 | lora | 64 | 1 | 0.0% | — | -3.3% |
| aime2024 | lora | 256 | 1 | 0.0% | — | -3.3% |
| aime2025 | base | 0 | 3 | 8.9% | — | 0.0% |
| aime2025 | icl | 16 | 3 | 5.6% | — | -3.3% |
| aime2025 | icl | 64 | 3 | 2.2% | — | -6.7% |
| aime2025 | icl | 256 | 2 | 5.0% | — | -5.0% |
| aime2025 | lora | 16 | 1 | 6.7% | — | 0.0% |
| aime2025 | lora | 64 | 1 | 3.3% | — | -3.3% |
| aime2025 | lora | 256 | 1 | 0.0% | — | -6.7% |
| gpqa | base | 0 | 3 | 44.4% | — | 0.0% |
| gpqa | icl | 16 | 3 | 38.2% | — | -6.2% |
| gpqa | icl | 64 | 2 | 38.6% | — | -7.6% |
| gpqa | icl | 256 | 2 | 39.6% | — | -6.6% |
| gpqa | lora | 16 | 1 | 31.8% | — | -19.7% |
| gpqa | lora | 64 | 1 | 20.2% | — | -31.3% |
| gpqa | lora | 256 | 1 | 38.9% | — | -12.6% |
| humaneval_python | base | 0 | 3 | 66.1% | 92.9% | 0.0% |
| humaneval_python | icl | 16 | 3 | 53.3% | 91.7% | -12.8% |
| humaneval_python | icl | 64 | 3 | 54.9% | 94.5% | -11.2% |
| humaneval_python | icl | 256 | 2 | 56.4% | 95.4% | -9.8% |
| humaneval_python | lora | 16 | 1 | 1.2% | 4.9% | -66.5% |
| humaneval_python | lora | 64 | 1 | 0.0% | 4.3% | -67.7% |
| humaneval_python | lora | 256 | 1 | 0.0% | 1.2% | -67.7% |
| humaneval_synthetic | base | 0 | 3 | 0.0% | 7.5% | 0.0% |
| humaneval_synthetic | icl | 16 | 3 | 4.5% | 30.7% | 4.5% |
| humaneval_synthetic | icl | 64 | 3 | 4.5% | 33.5% | 4.5% |
| humaneval_synthetic | icl | 256 | 2 | 6.7% | 41.2% | 6.7% |
| humaneval_synthetic | lora | 16 | 1 | 3.0% | 6.1% | 3.0% |
| humaneval_synthetic | lora | 64 | 1 | 0.0% | 0.6% | 0.0% |
| humaneval_synthetic | lora | 256 | 1 | 5.5% | 24.4% | 5.5% |

Small smoke runs verify plumbing only; they do not establish the research hypotheses.
