import ast
import io
import keyword
import tokenize

import pytest

from final_project.language import PRESERVED_WORDS, Language


@pytest.mark.parametrize(
    "source",
    [
        "def f(x):\n    return x + 1\n",
        "def f(xs):\n    return [x ** 2 for x in xs if x >= 0]\n",
        "class A:\n    def f(self):\n        return self.x[1:3]\n",
        's = "return + def :"\nx = {"a": (1, 2), "b": None}\n',
        "def f(x):\n    try:\n        return 1 / x\n    except ZeroDivisionError:\n        return -1\n",
        "x = 1.3e-4\ny = ...\nz = x if x else 0\n",
        'def f(x):\n    return f"answer {x + 1} {x=}"\n',
        "@staticmethod\ndef f(x: int = 1) -> int:\n    return x\n",
        's = """multi\n    line + def\nstring"""\n',
        "match x:\n    case 0:\n        y = 1\n    case _:\n        y = 2\n",
    ],
)
def test_round_trip(source):
    lang = Language()
    encoded = lang.encode(source)
    assert ast.dump(ast.parse(lang.decode(encoded))) == ast.dump(ast.parse(source))


def test_mapping_seed_and_literals():
    assert Language(1).mapping == Language(1).mapping
    assert Language(1).mapping != Language(2).mapping
    assert len(set(Language().mapping.values())) == len(Language().mapping)
    assert "'return + def'" in Language().encode("s = 'return + def'")


def test_collision_and_invalid_syntax():
    reserved = next(iter(Language().mapping.values()))
    with pytest.raises(ValueError, match="collides"):
        Language().encode(f"{reserved} = 1")
    with pytest.raises(ValueError, match="Untranslated"):
        Language().decode("def f():\n    return 1")


def test_keywords_are_short_and_operators_are_unchanged():
    lang = Language()
    assert set(lang.mapping) == set(keyword.kwlist) - PRESERVED_WORDS
    assert lang.mapping["return"] == "wert"
    assert all(2 <= len(value) <= len(key) for key, value in lang.mapping.items())
    source = "def f(x):\n    x *= 2\n    return x[0] + x.real ** 2 != 1\n"
    canonical = ast.unparse(ast.parse(source)) + "\n"
    encoded = lang.encode(source)

    def operators(code):
        return [
            t.string
            for t in tokenize.generate_tokens(io.StringIO(code).readline)
            if t.type == tokenize.OP
        ]

    assert operators(encoded) == operators(canonical)
    assert "x *= 2" in encoded
    assert "wert x[0] + x.real ** 2 != 1" in encoded


def test_imports_and_literal_words_are_preserved():
    source = "from typing import List as L\nimport math\ndef f(x):\n    if x is None:\n        return False\n    return True\n"
    lang = Language()
    encoded = lang.encode(source)
    assert "from typing import List as L" in encoded
    assert "import math" in encoded
    for word in ("None", "False", "True"):
        assert word in encoded
    assert ast.dump(ast.parse(lang.decode(encoded))) == ast.dump(ast.parse(source))
