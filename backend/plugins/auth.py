import json
import logging
import os
from typing import Dict

from cryptography.fernet import Fernet

logger = logging.getLogger("PluginCrypto")


class CredentialEncryption:
    """
    AES-256 (Fernet) encryption for plugin credentials.

    Key resolution order:
      1. PLUGIN_ENCRYPTION_KEY environment variable
      2. A persisted local dev key file (.plugin_key) so restarts don't orphan credentials
      3. Generate one and persist it (dev only, logged loudly)

    Never commit the generated key. In production, inject it from a secrets manager.
    """

    DEV_KEY_PATH = ".plugin_key"

    def __init__(self, key: str | None = None) -> None:
        self.key = key or os.environ.get("PLUGIN_ENCRYPTION_KEY")
        if not self.key:
            self.key = self._load_or_create_dev_key()
            logger.warning(
                "PLUGIN_ENCRYPTION_KEY not set — using local dev key at %s. "
                "Set this variable from a secrets manager in production.",
                self.DEV_KEY_PATH,
            )
        self.fernet = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)

    def _load_or_create_dev_key(self) -> str:
        if os.path.exists(self.DEV_KEY_PATH):
            with open(self.DEV_KEY_PATH, "rb") as fh:
                return fh.read().decode().strip()
        generated = Fernet.generate_key().decode()
        with open(self.DEV_KEY_PATH, "wb") as fh:
            fh.write(generated.encode())
        try:
            os.chmod(self.DEV_KEY_PATH, 0o600)
        except OSError:
            pass
        return generated

    def encrypt(self, credentials: Dict) -> bytes:
        return self.fernet.encrypt(json.dumps(credentials).encode())

    def decrypt(self, encrypted: bytes) -> Dict:
        return json.loads(self.fernet.decrypt(encrypted).decode())


def generate_key() -> str:
    """Utility: print a fresh Fernet key for use as PLUGIN_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode()
