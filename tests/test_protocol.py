from final_project.config import load_config
from final_project.language import Language
from final_project.prompts import prefix, query
from final_project.report import summarize


def test_persistent_icl_and_clean_lora():
    example = {"prompt": "Return one", "synthetic": "some code"}
    icl = prefix(Language(), "icl", [example], False)
    lora = prefix(Language(), "lora", [example], False)
    assert icl[0] == lora[0] == prefix(Language(), "base", [], False)[0]
    assert len(icl) == 3
    assert icl[-1]["content"] == "some code"
    assert len(lora) == 1
    assert "map" not in lora[0]["content"]
    assert "standard Python" in query({"prompt": "task"}, "humaneval_python")["content"]


def test_report_paired_baseline():
    rows = [
        {"benchmark": "aime2024", "condition": c, "n": n, "seed": s, "passed": p}
        for c, n, s, p in [
            ("base", 0, 0, True),
            ("base", 0, 1, False),
            ("icl", 16, 0, False),
            ("icl", 16, 1, False),
        ]
    ]
    summaries = summarize(rows)
    icl = next(r for r in summaries if r["condition"] == "icl")
    assert icl["accuracy"] == 0
    assert icl["delta_from_base"] == -0.5
    assert icl["seeds"] == 2


def test_configs():
    full, smoke = [load_config(f"configs/{name}.toml") for name in ("full", "smoke")]
    assert full["experiment"]["sizes"] == [16, 64, 256]
    assert smoke["evaluation"]["limit"] == 1
    assert full["model"]["precision"] == "fp16"


def test_synthetic_query_uses_translated_signature():
    lang = Language(7)
    source = 'def f(x):\n    """Return x doubled."""\n'
    text = query({"prompt": source}, "humaneval_synthetic", lang)["content"]
    assert lang.encode(source) in text
    assert "def f(x)" not in text
    assert "f(x):" in text


def test_partial_results_do_not_compare_unmatched_tasks():
    rows = [
        {
            "benchmark": "aime2024",
            "condition": "base",
            "n": 0,
            "seed": 0,
            "passed": True,
            "task_id": "a",
        },
        {
            "benchmark": "aime2024",
            "condition": "icl",
            "n": 16,
            "seed": 0,
            "passed": False,
            "task_id": "b",
        },
    ]
    result = next(r for r in summarize(rows) if r["condition"] == "icl")
    assert result["delta_from_base"] is None
    assert result["paired_seeds"] == 0


def test_all_icl_finishes_before_lora():
    from final_project.experiment import stages

    assert stages() == ("icl", "lora", "base")
    assert stages("icl") == ("icl",)
    assert stages("lora") == ("lora",)
