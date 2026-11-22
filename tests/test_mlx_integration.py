"""Opt-in tests using the actual locally converted MLX models."""

import os

import pytest

from final_project.backend import MLXBackend
from final_project.config import load_config
from final_project.data import examples, tasks
from final_project.language import Language
from final_project.prompts import prefix, query

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_MLX_TESTS") != "1", reason="requires downloaded models and RUN_MLX_TESTS=1"
)


def test_cache_reuse_and_isolation():
    cfg = load_config("configs/smoke.toml")
    cfg["generation"].update(temperature=0, max_tokens=32)
    lang = Language()
    rows, _ = examples(cfg, lang, 0)
    messages = prefix(lang, "icl", rows, False)
    request = messages + [query(tasks(cfg, "humaneval_python")[0], "humaneval_python")]
    backend = MLXBackend(cfg)
    try:
        uncached = backend.generate(request, 0)
        backend.set_prefix(messages)
        cached = backend.generate(request, 0)
        repeated = backend.generate(request, 0)
        assert cached["cached_tokens"] > 0
        assert uncached["text"] == cached["text"] == repeated["text"]
    finally:
        backend.close()


def test_mxfp8_generation():
    cfg = load_config("configs/smoke.toml")
    cfg["model"]["precision"] = "fp8"
    cfg["generation"].update(temperature=0, max_tokens=16)
    backend = MLXBackend(cfg)
    try:
        result = backend.generate(
            [{"role": "user", "content": "What is 2 + 2? Answer briefly."}], 0
        )
        assert "4" in result["text"]
    finally:
        backend.close()
