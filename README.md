# LoRA vs persistent in-context learning, locally on MLX

For Google Colab, open [Full_Sweep.ipynb](Full_Sweep.ipynb) with the project checkout available to the runtime. Select a GPU, set `PROJECT_DIR` if the working directory is outside the checkout, and run all cells. The notebook imports the project source from that checkout, manages Python with uv, handles Hugging Face login, and persists the sweep to Google Drive.


A reproducible CS182 experiment comparing **base**, **persistent ICL**, and **LoRA** on a synthetic Python language, followed by interference measurements on ordinary Python, math, and QA. Designed for Apple Silicon; the default model is Qwen3.5-2B converted to **FP16**, with separate **MXFP8** and **INT8** configurations.

Python is pinned to 3.12 and managed with **uv**. `uv.lock` pins dependencies. Run commands from this repository's root.

## Quick start

```sh
uv sync
uv run final-project model --config configs/smoke.toml
uv run final-project prepare --config configs/smoke.toml
uv run final-project plan --config configs/smoke.toml
uv run final-project run --config configs/smoke.toml
```

The smoke experiment uses **two MBPP examples, one seed, two LoRA updates, and one held-out HumanEval task in each output language**. It runs all three conditions (six generations total). It tests the pipeline, not the research hypotheses. Model conversion initially downloads the original weights; subsequent runs are local. Allow approximately 10 GB for the original and converted FP16 weights, plus caches and results.

`run` checks the complete prompt and training-token budgets before loading a model for evaluation. The run includes actual gradient-based LoRA training and sandboxed code execution. It does not execute the full experiment automatically.

## Full experiment

```sh
# GPQA requires accepting its access terms in your own Hugging Face account:
# https://huggingface.co/datasets/Idavidrein/gpqa
uv run hf auth login
uv run final-project prepare --config configs/full.toml
uv run final-project plan --config configs/full.toml
uv run final-project preflight --config configs/full.toml
uv run final-project run --config configs/full.toml
```

The runner completes every ICL evaluation first, then trains/evaluates every LoRA adapter, then runs base comparisons. Use `run --stage icl`, `run --stage lora`, or `run --stage base` to execute only one stage in the same experiment directory.

The full configuration uses N = 16, 64, 256 and seeds 0, 1, 2. It evaluates 164 HumanEval tasks in each language, 30 AIME 2024 tasks, 30 AIME 2025 tasks, and 198 GPQA Diamond questions. That is **12,306 generations and nine trained adapters**. Base runs once per seed/benchmark; the same baseline is compared to each N. There is no automatic reduction of N, substitution for GPQA, or truncation of examples. Full execution may take many hours or days, especially for long ICL prefixes. Measure the smoke run and a small pilot before committing to the matrix.

If GPQA access is unavailable, `prepare` preserves the other downloads and explains how to authenticate. To intentionally exclude a benchmark or change N, edit a copy of the TOML and choose a new `experiment.name`.

## Model precision

```sh
# Default: floating-point 16-bit weights
uv run final-project model --config configs/smoke.toml

# Alternative: microscaled floating-point 8-bit weight quantization
uv run final-project model --config configs/smoke.toml --precision fp8
uv run final-project run --config configs/smoke.toml --precision fp8

# Optional alternative: affine integer 8-bit weights, explicitly distinguished
uv run final-project model --config configs/smoke.toml --precision int8
uv run final-project run --config configs/smoke.toml --precision int8
```

Models live in separate `models/qwen3.5-2b/{fp16,fp8,int8}` directories. The CLI precision override also gives the experiment a separate output name. **`fp8` means MLX MXFP8 weight quantization, not FP8 activations or an all-FP8 training pipeline.** Unsupported MLX kernels fail explicitly; there is no silent fallback to INT8. FP16 and MXFP8 conversion, generation, and LoRA training have all been verified on the target Mac. LoRA adapters are trained separately for each weight format. FP16 is the requested initial working precision (not FP32); the original checkpoint's BF16 weights are converted to FP16.

MLX uses Metal, one resident model per evaluation condition, chunked prompt prefill, and an optional reusable ICL prefix cache. Each task gets a copy of the cached recurrent and attention state, preventing generated answers from contaminating later tasks. Training runs in a fresh subprocess to release optimizer memory and isolate MLX's gradient-checkpointing changes. `generation.max_context`, `prefill_step_size`, `max_tokens`, and `training.max_seq_length` are configurable. No sliding-window cache is used: it would change the persistent-ICL condition.

## Experimental protocol

- **Training:** official MBPP `full/train`; validation from `validation`, excluding normalized solutions duplicated in training. Each seed creates a shuffled ordering; N=16 is a prefix of N=64 and N=256. LoRA and ICL use exactly the same N problem/solution examples. HumanEval solutions are never used for training.
- **Synthetic language (`keywords-v4`):** a seeded bijection replaces Python hard keywords except `import`, `from`, `as`, `True`, `False`, and `None` with short, pronounceable pseudo-words (2–5 letters, never longer than the original keyword). The configured `language_seed` determines every replacement, including those for `def` and `return`. All punctuation and operators, including `*=`, `()`, `[]`, `:`, `.`, and `+`, remain unchanged. Indentation, identifiers, numbers, strings, and complete f-string literals remain Python-like. Soft keywords (`match`, `case`, `_`, `type`) remain unchanged. AST normalization removes comments and formatting; round trips preserve the AST, not source bytes. Every prepared training program is checked for AST equivalence. Reserved-name collisions fail explicitly.
- **Intentional scope change:** this is token substitution, as requested. It does not implement the proposal's postfix expressions, explicit block markers, or special `#` attributes. Remapping syntax does not remove possible pretraining contamination of the underlying benchmark problems.
- **Targeted task:** the function signature/imports are translated to synthetic syntax; the docstring remains unchanged. The model is asked for a complete program in the same syntax. This avoids presenting an ordinary-Python signature that encourages copying Python keywords. The grammar header is supplied to all three targeted conditions. Raw Python output is rejected as invalid synthetic syntax.
- **Interference:** ICL retains its grammar and N demonstrations before the unrelated task; base and active LoRA receive a clean general system prompt. The task explicitly requests standard Python, a math integer, or a QA option. All tasks are independent; previous evaluation answers never enter later contexts.
- **LoRA:** rank 8, alpha 16, three epochs in the full configuration, last 16 transformer layers, adapter dropout 0, learning rate 1e-4, batch size 1, gradient checkpointing. MLX's actual multiplier is `alpha / rank = 2`, not 16. Training loss covers only the answer and EOS. Validation is disjoint from demonstrations and is not used for early stopping/model selection. These optimizer/epoch/layer defaults fill details not specified in the proposal; change them in TOML for a new run.
- **Generation:** temperature 0.6, top-p 0.95, top-k 20, min-p 0, no presence/repetition penalties, thinking disabled. Generation seeds are derived from the experiment seed and task identity and are matched across conditions. One completion per task gives sampled pass@1. Numerical reproducibility across MLX/macOS versions is not guaranteed; versions and weights are recorded.
- **Scoring:** synthetic code is decoded, parsed, and run against HumanEval tests; ordinary Python uses the same evaluator. Parse validity, missing entry points, test failures, and timeouts are separate outcomes. AIME uses strict final integer extraction (`ANSWER: 123` or a boxed integer); GPQA uses final A/B/C/D. The GPQA option order is fixed and seeded, so the correct option is not always A. Unfinished thinking or missing final answers fail scoring.

## Results, resume, and inspection

Outputs go to `runs/<experiment.name>/`:

| File | Contents |
|---|---|
| `manifest.json` | Exact configuration, input/model hashes, library versions, language map, context preflight, expected run size |
| `selection-seed*-n*.json` | Training and validation task IDs |
| `adapters/seed*-n*/` | Training examples, adapter weights/config, loss log, completion marker |
| `results.jsonl` | Every prompt, raw output, token/time/memory measurements, decoded code, score, and generation seed |
| `summary.csv`, `summary.json` | Accuracy/pass@1, parse validity, seed standard deviation, and change from base |
| `report.md`, `accuracy.png` | Readable results and comparison chart |

```sh
# Same command resumes completed evaluations/adapters without duplicating them.
uv run final-project run --config configs/smoke.toml
# Regenerate a report (also works for a partial results log).
uv run final-project report runs/smoke-keywords-v4
# Inspect the language directly.
uv run final-project transpile example.py > example.synthetic
uv run final-project transpile example.synthetic --decode
```

A failed/incomplete training job restarts from scratch; completed adapters and evaluations are reused. Changing code, weights, dependencies, configuration, or data requires a new experiment name, so incompatible results cannot be silently combined. A torn final log append is archived and recovered on resume; corruption in earlier records is rejected. Only one writer can run an experiment at a time. Positive accuracy delta means improvement over base; negative delta means interference. Error bars are across-seed standard deviations, not confidence intervals. Reports mark incomplete matrices as partial and only compute baseline deltas for matched task sets.

## Code execution and tests

Code scoring requires macOS `sandbox-exec`; no unrestricted fallback is enabled. Generated code gets a fresh scratch directory, a default-deny profile permitting only interpreter/system reads, no network, no project/home-file access, CPU and wall-time limits, bounded output files, and process-group cleanup. This is a local benchmark isolation boundary, not a VM for deliberately hostile programs. Infrastructure preflight failures stop the run instead of being counted as wrong answers.

```sh
uv run pytest -q
uv run ruff check src tests
# Integration checks for execution, timeout, denied files and denied network:
RUN_SANDBOX_TESTS=1 uv run pytest tests/test_sandbox.py -q
# Optional real-model tests (requires both converted fp16 and fp8 models):
RUN_MLX_TESTS=1 uv run pytest tests/test_mlx_integration.py -q
```

The repository ignores model weights, downloaded datasets, and run artifacts. Keep the lockfile and configuration with any exported report; archive the complete run directory for reproducibility.

## Keyword-language calibration

The old all-token grammar produced 0/164 passes on the first synthetic HumanEval sweep. That run was stopped and preserved in `runs/full/`. Its long keyword/operator replacements were removed in `keywords-v3`; operators, imports, and literal words now retain their Python spelling. Old results and adapters must not be combined with the new language.

```sh
uv run final-project run --config configs/pilot-keywords-v4.toml --stage icl
```

The initial calibration uses N=16 and the first 32 HumanEval tasks across three seeds (96 generations). The other 132 tasks are reserved for confirmation after the grammar/prompt are frozen. The 5–10% pass-rate goal is empirical: scoring remains strict and ordinary-Python keywords are not silently accepted. This is exploratory calibration, so report these 32 tasks separately when interpreting the later full HumanEval sweep. The pilot report marks the overall comparison partial because base and LoRA are intentionally not part of this ICL-only calibration.

The fully seeded grammar writes full runs to `runs/full-keywords-v4-final-answer/`, and the new smoke directory is `runs/smoke-keywords-v4/`. Both use ICL → LoRA → base execution order. No old run is resumed under the new grammar.

## Historical smoke runs (old grammar)

Both `runs/smoke/` (FP16) and `runs/smoke-fp8/` (MXFP8) completed all six evaluations and two LoRA updates. FP16 training peaked at approximately 20 GB; MXFP8 training peaked at approximately 31 GB in the same smoke setup. MXFP8 reduced stored model size (3.5 GB to 1.8 GB), but did not reduce training peak memory in this implementation, so FP16 remains the default. Prefix-cache equivalence and isolation were checked against uncached inference, and resuming the FP16 run reused its adapter without duplicating results. These two-example runs did **not** learn valid synthetic programs; their scores are plumbing checks, not research conclusions. These historical tests used the old grammar. GPQA access has since been configured and all 198 Diamond questions are available locally.

## Sources

- [MLX LM](https://github.com/ml-explore/mlx-lm) and its [LoRA implementation](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/tuner/lora.py)
- [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B)
- [MBPP](https://huggingface.co/datasets/google-research-datasets/mbpp) and [HumanEval](https://huggingface.co/datasets/openai/openai_humaneval)
- [AIME validation](https://huggingface.co/datasets/project-numina/aimo-validation-aime) (2024 questions selected by source URL), [AIME 2025](https://huggingface.co/datasets/yentinglin/aime_2025), and [GPQA Diamond](https://huggingface.co/datasets/Idavidrein/gpqa)

### Final-answer follow-up for AIME and GPQA

When a generation ends at its token limit and the scorer cannot extract an answer, the runner continues the conversation once. It includes the original problem, demonstrations and generated work, then requests a bare integer or option letter with thinking disabled. The follow-up has a maximum of 25 tokens and uses the remaining context window. If the window is full, the trace records `context_full`. An extractable answer is scored immediately, even if incorrect. HumanEval uses the original single completion.

In results.jsonl, `text` and the top-level token counts and timings describe the first generation. For a retry, `initial_score` records the first score and `followup` holds the instruction, second output and its generation statistics. Top-level accuracy uses the final score. Include both generations when reporting compute costs. The full configuration writes this protocol to `runs/full-keywords-v4-final-answer/`.
