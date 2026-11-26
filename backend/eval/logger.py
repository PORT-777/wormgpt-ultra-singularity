"""Structured interaction logging."""
from __future__ import annotations

import json
import logging


log = logging.getLogger("ai_interactions")


def log_interaction(user_id: str, service: str, ok: bool, **extra) -> None:
    log.info(json.dumps({"user": user_id, "service": service, "ok": ok, **extra},
                        ensure_ascii=False, default=str))
