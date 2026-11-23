from unittest.mock import Mock

import pytest

from final_project.experiment import score_with_followup
from final_project.language import Language


@pytest.mark.parametrize(
    "benchmark,expected", [("gpqa", "D"), ("aime2024", "0"), ("aime2025", "999")]
)
def test_retry_uses_original_work_and_scores_short_answer(benchmark, expected):
    backend = Mock()
    backend.tokens.return_value = [1, 2]
    backend.generate.return_value = {"text": expected, "finish_reason": "stop"}
    prompt = [{"role": "user", "content": "question"}]
    first = {"text": "unfinished work", "finish_reason": "length"}
    cfg = {"evaluation": {"timeout": 2}, "generation": {"max_context": 128}}
    result = score_with_followup(
        backend, prompt, first, {"answer": expected}, benchmark, Language(), 1, cfg
    )
    assert result["passed"] and result["initial_score"]["status"] == "answer_missing"
    turns = backend.generate.call_args.args[0]
    assert turns[:-2] == prompt and turns[-2]["content"] == first["text"]
    assert backend.generate.call_args.kwargs == {"max_tokens": 25, "thinking": False}
    assert result["followup"]["text"] == expected


@pytest.mark.parametrize(
    "reason,text,benchmark",
    [
        ("length", "ANSWER: A", "gpqa"),
        ("stop", "unfinished", "gpqa"),
        ("length", "def f(", "humaneval_python"),
    ],
)
def test_no_second_guess_or_code_retry(reason, text, benchmark):
    backend = Mock()
    result = score_with_followup(
        backend,
        [],
        {"text": text, "finish_reason": reason},
        {"answer": "D"},
        benchmark,
        Language(),
        1,
        {"evaluation": {"timeout": 2}},
    )
    backend.generate.assert_not_called()
    assert not result["passed"] and "followup" not in result
