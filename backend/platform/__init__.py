"""Central platform patterns (workflow, sessions, workspaces, code).

Compatibility: this package name shadows the Python standard-library `platform`
module when `backend/` is on sys.path. We explicitly load the real stdlib module
from its file path and proxy its attributes, so third-party packages (e.g.
zstandard) that call `platform.python_implementation()` keep working.
"""
from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path

_stdlib_file = Path(sysconfig.get_paths()["stdlib"]) / "platform.py"
if _stdlib_file.exists():
    _spec = importlib.util.spec_from_file_location("_stdlib_platform", _stdlib_file)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules.setdefault("_stdlib_platform", _mod)
        _spec.loader.exec_module(_mod)
        for _name in dir(_mod):
            if not _name.startswith("__"):
                globals()[_name] = getattr(_mod, _name)
