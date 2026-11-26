"""Optional Langfuse trace export."""
from __future__ import annotations

import os
from typing import Any


def langfuse_configured() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


async def export_trace(trace: Any) -> bool:
    if not langfuse_configured():
        return False
    try:
        from langfuse import Langfuse
        client = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))
        client.trace(
            id=trace.id, name=trace.trace_type,
            input=trace.input_preview, output=trace.output_preview,
            metadata={"model": trace.model, "cost": trace.cost_usd,
                      "latency_ms": trace.latency_ms},
            user_id=trace.user_id or None, session_id=trace.session_id or None)
        return True
    except Exception:
        return False
