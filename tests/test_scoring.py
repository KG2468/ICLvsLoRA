import pytest

from final_project.language import Language
from final_project.scoring import answer, extract_code, score


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ANSWER: 007", "7"),
        ("Work: 51. ANSWER: 12", "12"),
        (r"\boxed{999}", "999"),
        ("ANSWER: 1000", None),
        ("The intermediate result is 12", None),
        ("<think>ANSWER: 5", None),
        ("<think>ANSWER: 5</think>ANSWER: 17", "17"),
        ("0", "0"),
    ],
)
def test_math_answers(text, expected):
    assert answer(text, "aime2024") == expected


def test_code_and_qa():
    assert extract_code("```python\ndef f(): return 1\n```") == "def f(): return 1"
    assert answer("ANSWER: c", "gpqa") == "C"
    assert answer("Possibly A or B", "gpqa") is None


def test_wrong_language_rejected():
    result = score("def f(): return 1", {"entry_point": "f"}, "humaneval_synthetic", Language(), 1)
    assert result["status"] == "parse_error"
    assert not result["passed"]


def test_score_survives_deeply_nested_expression():
    # A model output with a pathological left-nested expression once raised
    # RecursionError inside ast.unparse and killed the whole run.
    lang = Language()
    depth = 400
    code = "def f(x):\n    return " + "(" * depth + "x" + ")" * depth + "\n"
    task = {"entry_point": "f", "test": "def check(c): pass"}
    result = score(code, task, "humaneval_synthetic", lang, 5)
    assert result["status"] in {"parse_error", "entry_point_missing", "failed", "passed"}
    assert not result["passed"]


def test_answer_boundaries():
    assert answer("ANSWER: 1.5", "aime2024") is None
    assert answer("ANSWER: 1,000", "aime2024") is None
    assert answer("ANSWER: CAT", "gpqa") is None
    assert answer("ANSWER: 12.", "aime2024") == "12"
