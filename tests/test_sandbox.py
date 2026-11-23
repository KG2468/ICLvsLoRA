"""Opt-in integration tests: RUN_SANDBOX_TESTS=1 uv run pytest tests/test_sandbox.py."""

import os
import sys
from pathlib import Path

import pytest

from final_project.scoring import execute

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("RUN_SANDBOX_TESTS") != "1",
    reason="macOS sandbox integration tests require RUN_SANDBOX_TESTS=1",
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
    assert "PermissionError" in result["stderr"]
    source = 'def f():\n    import socket\n    socket.create_connection(("1.1.1.1", 80), timeout=1)'
    result = execute(source, "def check(f): f()", "f", 2)
    assert not result["passed"]
    assert "PermissionError" in result["stderr"]


@pytest.mark.parametrize("early_exit", ["raise SystemExit(0)", "import os; os._exit(0)"])
def test_early_exit_cannot_pass(early_exit):
    result = execute("def f(): " + early_exit, "def check(f): assert f() == 42", "f", 2)
    assert result["returncode"] == 0 and not result["passed"]
