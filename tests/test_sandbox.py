"""Opt-in integration tests: RUN_SANDBOX_TESTS=1 uv run pytest tests/test_sandbox.py."""

import os
import sys
from pathlib import Path

import pytest

from final_project.scoring import execute

pytestmark = pytest.mark.skipif(
    sys.platform not in {"darwin", "linux"} or os.environ.get("RUN_SANDBOX_TESTS") != "1",
    reason="Sandbox integration tests require RUN_SANDBOX_TESTS=1",
)


def test_pass_fail_and_timeout():
    assert execute("def f(): return 1", "def check(f): assert f()==1", "f", 2)["passed"]
    assert not execute("def f(): return 2", "def check(f): assert f()==1", "f", 2)["passed"]
    assert (
        execute("def f():\n    while True: pass", "def check(f): f()", "f", 1)["status"]
        == "timeout"
    )


def test_private_files_and_network_are_denied():
    target = str(Path("pyproject.toml").resolve())
    source = f"def f():\n    return open({target!r}).read()"
    result = execute(source, "def check(f): f()", "f", 2)
    assert not result["passed"]
    assert any(error in result["stderr"] for error in ("PermissionError", "FileNotFoundError"))
    source = 'def f():\n    import socket\n    socket.socket().connect(("127.0.0.1", 9))'
    result = execute(source, "def check(f): f()", "f", 2)
    assert not result["passed"]
    assert "PermissionError" in result["stderr"]


@pytest.mark.parametrize("early_exit", ["raise SystemExit(0)", "import os; os._exit(0)"])
def test_early_exit_cannot_pass(early_exit):
    result = execute("def f(): " + early_exit, "def check(f): assert f() == 42", "f", 2)
    assert result["returncode"] == 0 and not result["passed"]


def test_stdlib_imports_in_candidate():
    source = "def f():\n    import socket, fractions, math\n    return socket.AF_INET, fractions.Fraction(1, 2), math.isqrt(9)"
    result = execute(source, "def check(f): assert f() == (2, 0.5, 3)", "f", 2)
    assert result["passed"], result
