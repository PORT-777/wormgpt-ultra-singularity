"""Compatibility shim for backend.plugins.auth."""
from plugins_system.auth import CredentialEncryption, generate_key  # noqa: F401

__all__ = ["CredentialEncryption", "generate_key"]
