"""Strict answer extraction and isolated generated-code execution."""

from __future__ import annotations

import ast
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path

from .language import Language


def final_text(text: str) -> str:
    # Qwen thinking must never be mistaken for the final answer.
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    elif "<think>" in text:
        return ""
    return text.strip()


def extract_code(text: str) -> str:
    text = final_text(text)
    blocks = re.findall(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)
    return blocks[-1].strip() if blocks else text


def answer(text: str, benchmark: str) -> str | None:
    text = final_text(text)
    token = r"[A-D]" if benchmark == "gpqa" else r"[0-9]{1,3}"
    # A marked or standalone answer must consume the rest of its line.
    value = rf"(?:\*\*({token})\*\*|\(({token})\)|({token}))[.]?"
    marked = rf"\bANSWER[ \t]*:[ \t]*{value}[ \t]*$|\\boxed\{{({token})\}}"
    matches = list(re.finditer(marked, text, re.IGNORECASE | re.MULTILINE))
    match = matches[-1] if matches else re.fullmatch(value, text, re.IGNORECASE)
    if match is None:
        return None
    extracted = next(group for group in match.groups() if group is not None)
    return extracted.upper() if benchmark == "gpqa" else str(int(extracted))


def sandbox_command(directory: Path, timeout: int, marker: str) -> list[str]:
    if sys.platform == "linux":
        import shutil
        import sysconfig

        # Ephemeral, root-owned jail on the VM. Never put credentials or Drive here.
        root = Path(sys.base_prefix) / "cs182-scoring-root"
        if os.geteuid() != 0:
            raise RuntimeError("Linux scoring requires Colab root privileges")
        if not (root / "stdlib").exists():
            root.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=root) as staging:
                stdlib = Path(staging) / "stdlib"
                shutil.copytree(
                    sysconfig.get_path("stdlib"),
                    stdlib,
                    ignore=shutil.ignore_patterns("site-packages", "__pycache__", "test", "tests"),
                )
                stdlib.rename(root / "stdlib")
        return [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(Path(__file__).with_name("linux_jail.py")),
            str(root),
            str(directory / "candidate.py"),
            str(timeout),
            marker,
        ]
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").exists():
        raise RuntimeError(
            "Code scoring requires macOS sandbox-exec; no unsafe fallback is enabled"
        )
    # Default-deny Seatbelt profile. No access to the user's home, credentials,
    # network, or project. Only the interpreter, OS libraries and scratch directory.
    readable = {
        "/System",
        "/usr",
        "/bin",
        "/Library",
        "/private/var/db/dyld",
        str(Path(sys.base_prefix).resolve()),
        str(Path(sys.executable).resolve().parent.parent),
        str(directory.resolve()),
    }
    rules = "\n".join(f"(subpath {json.dumps(p)})" for p in sorted(readable))
    profile = f"""(version 1)
(deny default)
(allow file-read-metadata)
(allow file-map-executable)
(allow process-exec)
(allow process-fork)
(allow signal (target self))
(allow sysctl-read)
(allow mach-lookup)
(allow file-read* {rules} (literal "/") (literal "/dev/urandom") (literal "/dev/null"))
(allow file-write* (subpath {json.dumps(str(directory.resolve()))}) (literal "/dev/null"))
"""
    (directory / "sandbox.sb").write_text(profile)
    runner = """import os, resource, runpy, sys
resource.setrlimit(resource.RLIMIT_CPU, (__TIMEOUT__, __TIMEOUT__))
resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
completed = sys.argv.pop().encode("ascii")
write = os.write
runpy.run_path(sys.argv[1], run_name="__main__")
write(1, completed)
""".replace("__TIMEOUT__", str(max(1, int(timeout))))
    return [
        "/usr/bin/sandbox-exec",
        "-f",
        str(directory / "sandbox.sb"),
        str(Path(sys.executable).resolve()),
        "-I",
        "-B",
        "-c",
        runner,
        str(directory / "candidate.py"),
        marker,
    ]


def execute(source: str, tests: str, entry_point: str, timeout: int) -> dict:
    if not entry_point.isidentifier():
        raise ValueError("Invalid entry point")
    with tempfile.TemporaryDirectory(prefix="cs182-score-") as tmp:
        directory = Path(tmp)
        marker = secrets.token_hex(24)
        (directory / "candidate.py").write_text(source + "\n" + tests + f"\ncheck({entry_point})\n")
        command = sandbox_command(directory, timeout, marker)
        # Output goes to bounded files, not an unbounded subprocess PIPE.
        with (directory / "stdout").open("w+b") as out, (directory / "stderr").open("w+") as err:
            process = subprocess.Popen(
                command,
                cwd=directory,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                env={"PATH": "/usr/bin:/bin", "HOME": tmp, "TMPDIR": tmp},
                start_new_session=True,
            )
            try:
                process.wait(timeout=timeout + 2)
                out.seek(0)
                completed = marker.encode("ascii") in out.read(1048576)
                status = (
                    "passed"
                    if process.returncode == 0 and completed
                    else (
                        "timeout"
                        if process.returncode in (-signal.SIGXCPU, -signal.SIGKILL)
                        else "failed"
                    )
                )
            except subprocess.TimeoutExpired:
                status = "timeout"
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            err.seek(0)
            detail = err.read(4000)
            if "sandbox-exec:" in detail or "sandbox_apply" in detail:
                raise RuntimeError(f"Code sandbox unavailable: {detail}")
        return {
            "passed": status == "passed",
            "status": status,
            "stderr": detail,
            "returncode": process.returncode,
        }


def score(text: str, task: dict, benchmark: str, lang: Language, timeout: int) -> dict:
    if not benchmark.startswith("humaneval"):
        extracted = answer(text, benchmark)
        return {
            "passed": extracted == task["answer"],
            "answer": extracted,
            "expected": task["answer"],
            "status": "scored" if extracted else "answer_missing",
        }
    code = extract_code(text)
    try:
        if benchmark.endswith("synthetic"):
            code = lang.decode(code)
        tree = ast.parse(code)
        if not any(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == task["entry_point"]
            for n in tree.body
        ):
            return {"passed": False, "parse_valid": False, "status": "entry_point_missing"}
    except (
        SyntaxError,
        ValueError,
        IndentationError,
        tokenize.TokenError,
        RecursionError,
    ) as exc:
        # Deeply nested generated expressions can exhaust the interpreter stack
        # inside ast.parse/ast.unparse; that is a model failure, not a runner crash.
        return {"passed": False, "parse_valid": False, "status": "parse_error", "error": str(exc)}
    result = execute(code, task["test"], task["entry_point"], timeout)
    return dict(result, parse_valid=True, decoded_code=code)
