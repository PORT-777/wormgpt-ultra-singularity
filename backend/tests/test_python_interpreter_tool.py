"""Regression: PythonInterpreter must actually execute code, not NameError."""
from __future__ import annotations

import asyncio

from tools.python_interpreter import PythonInterpreter


def test_python_interpreter_runs_code():
    out = asyncio.run(PythonInterpreter().run(code="print(6 * 7)"))
    assert "42" in out
    assert "[exit code 0]" in out
    assert "NameError" not in out


def test_python_interpreter_captures_error():
    out = asyncio.run(PythonInterpreter().run(code="raise ValueError('boom')"))
    assert "boom" in out
    assert "NameError" not in out
