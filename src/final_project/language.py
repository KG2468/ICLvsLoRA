"""Seeded, token-aware syntax substitution. Never modify literal/comment contents.

Version keywords-v3 retains Python operators, punctuation, indentation,
imports and literal words. Other hard keywords become short pseudo-words.
AST equivalence is checked when encoding programs.
"""

from __future__ import annotations

import ast
import builtins
import io
import keyword
import random
import tokenize
from dataclasses import dataclass

PRESERVED_WORDS = frozenset({"import", "from", "as", "True", "False", "None"})


@dataclass(frozen=True)
class Language:
    seed: int = 182
    version = "keywords-v3"

    @property
    def mapping(self) -> dict[str, str]:
        rng = random.Random(self.seed)
        symbols = sorted(keyword.kwlist)
        names = set(keyword.kwlist) | set(keyword.softkwlist) | set(dir(builtins)) | {"wert"}
        result = {}
        for symbol in symbols:
            if symbol == "return":
                result[symbol] = "wert"
                continue
            while True:
                length = min(len(symbol), 5)
                name = "".join(
                    rng.choice("bcdfghjklmnprstvwz" if i % 2 == 0 else "aeiou")
                    for i in range(length)
                )
                if symbol[0].isupper():
                    name = name.capitalize()
                if name not in names:
                    break
            names.add(name)
            result[symbol] = name
        return {key: value for key, value in result.items() if key not in PRESERVED_WORDS}

    def _translate(self, source: str, reverse: bool) -> str:
        mapping = self.mapping
        if reverse:
            mapping = {v: k for k, v in mapping.items()}
        # Token positions preserve whitespace, literals, comments, and f-strings.
        lines = source.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        edits = []
        fstring_depth = 0
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.FSTRING_START:
                fstring_depth += 1
            if fstring_depth:
                if tok.type == tokenize.FSTRING_END:
                    fstring_depth -= 1
                continue
            if tok.type not in (tokenize.NAME, tokenize.OP):
                continue
            if not reverse and tok.type == tokenize.NAME and tok.string in self.mapping.values():
                raise ValueError(f"Identifier collides with reserved synthetic token: {tok.string}")
            if reverse and tok.type == tokenize.NAME and tok.string in self.mapping:
                raise ValueError(f"Untranslated Python syntax in synthetic output: {tok.string}")
            if tok.string in mapping:
                start = offsets[tok.start[0] - 1] + tok.start[1]
                end = offsets[tok.end[0] - 1] + tok.end[1]
                value = mapping[tok.string]
                edits.append((start, end, value))
        for start, end, value in reversed(edits):
            source = source[:start] + value + source[end:]
        return source

    def encode(self, source: str) -> str:
        # Canonical source removes unusual continuation indentation, and normalizes
        # f-strings into a representation the token layer can handle consistently.
        tree = ast.parse(source)
        canonical = ast.unparse(tree) + "\n"
        encoded = self._translate(canonical, False)
        # Do not trust a reversible-looking mapping without semantic validation.
        decoded = self.decode(encoded)
        if ast.dump(tree) != ast.dump(ast.parse(decoded)):
            raise ValueError("Transpilation changed the program AST")
        return encoded

    def decode(self, source: str) -> str:
        translated = self._translate(source, True)
        return ast.unparse(ast.parse(translated)) + "\n"

    def header(self) -> str:
        pairs = "; ".join(f"{key!r} -> {value}" for key, value in self.mapping.items())
        return (
            "Synthetic Python uses Python semantics, indentation, identifiers and literals. "
            "Replace only the Python keywords in this map with their short pseudo-words. "
            "Keep ALL punctuation and operators unchanged, including (), [], {}, :, ., =, *= and +. "
            "Keep import, from, as, True, False and None unchanged. "
            "Keep function names, variable names, builtins, string contents and complete f-string literals unchanged. "
            "Return a complete program, not just a function body. No Markdown or explanation.\n"
            + pairs
        )
