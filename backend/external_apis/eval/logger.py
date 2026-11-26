"""Structured interaction logger."""
from __future__ import annotations

import json, logging


log = logging.getLogger("ai_interactions")


def log_interaction(user_id: str, service: str, ok: bool):
    log.info(json.dumps({"user": user_id, "service": service, "ok": ok}))
