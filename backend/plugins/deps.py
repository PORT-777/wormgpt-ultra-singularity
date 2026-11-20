"""Compatibility shim for backend.plugins.deps."""
from plugins_system.deps import (  # noqa: F401
    encryption,
    get_manager,
    get_runtime,
    get_store,
    manager,
    runtime,
    store,
)

__all__ = ["encryption", "get_manager", "get_runtime", "get_store", "manager", "runtime", "store"]
