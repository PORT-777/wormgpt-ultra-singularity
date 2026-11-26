"""Enrich a prompt with registry status and retrieved context."""
from __future__ import annotations


async def enrich(user_message: str, user_id: str = "default"):
    from ..rag.pipeline import query as rag_query
    from ..registry import registry
    context = await rag_query(user_message, top_k=3)
    return {"prompt": user_message, "context": context,
            "user_id": user_id, "services": len(registry.all())}
