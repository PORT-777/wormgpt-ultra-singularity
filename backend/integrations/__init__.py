"""
WormGPT Ultra :: OAuth 2.0 / OIDC integration subsystem.

Everything in this package is server-side only:

  providers.py  - real, official authorization-server descriptors per plugin
  store.py      - encrypted connection + authorization-session persistence
  service.py    - authorization-code + PKCE flow, refresh, revocation
  api.py        - FastAPI router consumed by the Extensions & Integrations UI
  deps.py       - process singletons

Tokens are never returned to the browser, written to logs, or placed in a URL.
"""

from integrations.providers import PROVIDERS, get_provider, provider_catalog

__all__ = ["PROVIDERS", "get_provider", "provider_catalog"]
