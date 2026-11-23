"""MLX loading, bounded generation, and reusable immutable prefix caches."""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path

from .config import model_path


def convert(cfg: dict):
    destination = model_path(cfg)
    if destination.exists():
        verify_model(cfg)
        print(f"Using {destination}")
        return
    precision = cfg["model"]["precision"]
    # Conversion accepts a revision through its Python API, not every CLI release.
    from mlx_lm.convert import convert as mlx_convert

    options = {
        "hf_path": cfg["model"]["source"],
        "mlx_path": str(destination),
        "dtype": "float16",
        "revision": cfg["model"].get("revision", "main"),
    }
    if precision == "fp8":
        options.update(quantize=True, q_mode="mxfp8", q_bits=8, q_group_size=32)
    elif precision == "int8":
        options.update(quantize=True, q_mode="affine", q_bits=8, q_group_size=64)
    print(f"Converting {options}", flush=True)
    mlx_convert(**options)
    (destination / "experiment_model.json").write_text(
        json.dumps(
            {
                "source": cfg["model"]["source"],
                "revision": cfg["model"].get("revision", "main"),
                "precision": precision,
                "conversion": options,
            },
            indent=2,
        )
        + "\n"
    )
    verify_model(cfg)


def verify_model(cfg: dict):
    path = model_path(cfg)
    provenance = path / "experiment_model.json"
    if provenance.exists():
        origin = json.loads(provenance.read_text())
        if origin["source"] != cfg["model"]["source"] or origin["revision"] != cfg["model"].get(
            "revision", "main"
        ):
            raise ValueError("Converted model source/revision changed; use a new model.directory")
    metadata = json.loads((path / "config.json").read_text())
    quant = metadata.get("quantization") or metadata.get("quantization_config")
    precision = cfg["model"]["precision"]
    if precision == "fp16" and quant:
        raise ValueError("FP16 config points to a quantized model")
    if precision != "fp16":
        expected = "mxfp8" if precision == "fp8" else "affine"
        if not quant or quant.get("bits") != 8 or quant.get("mode", "affine") != expected:
            raise ValueError(f"Model quantization does not match {precision}")
    if not list(path.glob("*.safetensors")):
        raise ValueError(f"No model weights in {path}")
    index_path = path / "model.safetensors.index.json"
    if index_path.exists():
        for filename in set(json.loads(index_path.read_text())["weight_map"].values()):
            if not (path / filename).is_file():
                raise ValueError(f"Missing model shard: {filename}")
    if precision == "fp16":
        from safetensors import safe_open

        dtypes = set()
        for shard in path.glob("*.safetensors"):
            with safe_open(shard, framework="numpy") as weights:
                dtypes.update(weights.get_slice(k).get_dtype() for k in weights.keys())  # noqa: SIM118
        if "F16" not in dtypes or dtypes - {"F16", "F32"}:
            raise ValueError(f"Expected FP16 weights (with FP32 stability tensors), got {dtypes}")


class MLXBackend:
    def __init__(self, cfg: dict, adapter: Path | None = None):
        import mlx.core as mx
        from mlx_lm import load

        verify_model(cfg)
        self.cfg = cfg
        self.model, self.tokenizer = load(
            str(model_path(cfg)), adapter_path=str(adapter) if adapter else None
        )
        self.model.eval()
        mx.eval(self.model.parameters())
        self.prefix_tokens: list[int] = []
        self.prefix_cache = None

    def tokens(
        self, messages: list[dict], generation: bool = True, *, thinking: bool | None = None
    ) -> list[int]:
        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            return_dict=False,
            add_generation_prompt=generation,
            enable_thinking=self.cfg["generation"]["enable_thinking"]
            if thinking is None
            else thinking,
        )

    def set_prefix(self, messages: list[dict]):
        import mlx.core as mx
        from mlx_lm.models.cache import make_prompt_cache

        self.prefix_tokens = []
        self.prefix_cache = None
        if len(messages) == 1 or not self.cfg["generation"].get("prefix_cache", True):
            return
        # Qwen renders the last assistant turn differently depending on whether
        # another user turn follows. Render a placeholder query, then cache only
        # the exact prefix preceding that query. Drop its final token to avoid
        # a BPE merge across the prefix/query boundary.
        marker = "__CS182_QUERY_BOUNDARY_897164__"
        rendered = self.tokenizer.apply_chat_template(
            messages + [{"role": "user", "content": marker}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.cfg["generation"]["enable_thinking"],
        )
        if rendered.count(marker) != 1:
            raise ValueError("Ambiguous prefix cache boundary")
        tokens = self.tokenizer.encode(rendered.split(marker)[0], add_special_tokens=False)[:-1]
        gen = self.cfg["generation"]
        if len(tokens) + gen["max_tokens"] >= gen["max_context"]:
            raise ValueError("ICL prefix exceeds context budget; no examples were truncated")
        cache = make_prompt_cache(self.model)
        step = gen["prefill_step_size"]
        start = time.monotonic()
        for i in range(0, len(tokens), step):
            self.model(mx.array(tokens[i : i + step])[None], cache=cache)
            mx.eval([c.state for c in cache])
            mx.clear_cache()
        self.prefix_tokens, self.prefix_cache = tokens, cache
        print(f"Cached {len(tokens)} prefix tokens in {time.monotonic() - start:.1f}s", flush=True)

    def generate(
        self,
        messages: list[dict],
        seed: int,
        *,
        max_tokens: int | None = None,
        thinking: bool | None = None,
    ) -> dict:
        import mlx.core as mx
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler

        gen = self.cfg["generation"]
        budget = gen["max_tokens"] if max_tokens is None else max_tokens
        tokens = self.tokens(messages, thinking=thinking)
        if len(tokens) + budget > gen["max_context"]:
            raise ValueError(
                f"Prompt ({len(tokens)} tokens) plus output exceeds context budget; "
                "no examples were truncated"
            )
        cached = 0
        cache = None
        prompt = tokens
        if (
            self.prefix_cache is not None
            and tokens[: len(self.prefix_tokens)] == self.prefix_tokens
        ):
            cached = len(self.prefix_tokens)
            prompt = tokens[cached:]
            # Hybrid Qwen has recurrent state as well as KV caches. Copy all cache
            # objects, so no generated answer can contaminate the next question.
            cache = copy.deepcopy(self.prefix_cache)
        mx.random.seed(seed)
        sampler = make_sampler(
            temp=gen["temperature"], top_p=gen["top_p"], top_k=gen["top_k"], min_p=gen["min_p"]
        )
        start = time.monotonic()
        text = ""
        last = None
        for response in stream_generate(
            self.model,
            self.tokenizer,
            prompt,
            max_tokens=budget,
            sampler=sampler,
            prompt_cache=cache,
            prefill_step_size=gen["prefill_step_size"],
        ):
            text += response.text
            last = response
        result = {
            "text": text,
            "thinking": gen["enable_thinking"] if thinking is None else thinking,
            "prompt_tokens": len(tokens),
            "cached_tokens": cached,
            "generation_tokens": last.generation_tokens if last else 0,
            "seconds": time.monotonic() - start,
            "peak_memory_gb": mx.get_peak_memory() / 1e9,
            "finish_reason": getattr(last, "finish_reason", None),
        }
        mx.clear_cache()
        return result

    def close(self):
        import gc

        import mlx.core as mx

        self.prefix_cache = None
        del self.model
        del self.tokenizer
        gc.collect()
        mx.clear_cache()
