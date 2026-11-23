from __future__ import annotations

from .language import Language


def demonstration(row: dict) -> list[dict]:
    return [
        {"role": "user", "content": "Write a complete synthetic Python program.\n" + row["prompt"]},
        {"role": "assistant", "content": row["synthetic"]},
    ]


def prefix(lang: Language, condition: str, examples: list[dict], synthetic: bool) -> list[dict]:
    system = lang.header() if synthetic else "You are a helpful assistant."
    messages = [{"role": "system", "content": system}]
    if condition == "icl":
        for row in examples:
            messages.extend(demonstration(row))
    return messages


def query(task: dict, benchmark: str, lang: Language | None = None) -> dict:
    if benchmark.startswith("humaneval"):
        if benchmark.endswith("synthetic"):
            lang = lang or Language()
            text = (
                "Complete this function in the synthetic language from the demonstrations. "
                "Use the mapped keywords throughout your functions, loops, conditions and returns. "
                "Keep import, from, as, True, False and None unchanged. "
                "Do not switch mapped keywords back to their Python spelling. "
                f"In particular: def -> {lang.mapping['def']}, return -> {lang.mapping['return']}. "
                "All punctuation, operators, identifiers and builtins remain unchanged. "
                "Return the complete program with the same function name and arguments. "
                "No Markdown or explanation. The signature and docstring below specify the task "
                "and already use the synthetic syntax:\n" + lang.encode(task["prompt"])
            )
            return {"role": "user", "content": text}
        language = "synthetic Python" if benchmark.endswith("synthetic") else "standard Python"
        text = (
            f"Now solve this task in {language}. Return the complete function and any imports, "
            "preserving the function name and argument names. No explanation or Markdown. "
            "The Python signature/docstring below specifies the task; translate syntax if requested.\n"
            + task["prompt"]
        )
    elif benchmark.startswith("aime"):
        text = "Now solve this math problem. End with 'ANSWER: <integer>'.\n" + task["prompt"]
    else:
        text = "Now answer this question. End with 'ANSWER: <A, B, C, or D>'.\n" + task["prompt"]
    return {"role": "user", "content": text}


def training_messages(lang: Language, row: dict) -> list[dict]:
    return [{"role": "system", "content": lang.header()}] + demonstration(row)
