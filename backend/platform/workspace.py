"""AnythingLLM-inspired isolated knowledge workspaces."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Workspace(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "default"
    description: str = ""
    vector_collection: str = ""
    documents: list[str] = Field(default_factory=list)
    llm_model: str = "auto"
    llm_temperature: float = 0.7
    system_prompt: str = ""
    similarity_threshold: float = 0.5
    top_k_docs: int = 5
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.vector_collection:
            self.vector_collection = f"ws_{self.id[:12]}"


WORKSPACES: dict[str, Workspace] = {}


def create_workspace(name: str, **kwargs) -> Workspace:
    ws = Workspace(name=name, **kwargs)
    WORKSPACES[ws.id] = ws
    return ws


def get_workspace(ws_id: str) -> Workspace | None:
    return WORKSPACES.get(ws_id)


def list_workspaces() -> list[Workspace]:
    return list(WORKSPACES.values())


async def chat(ws_id: str, message: str) -> dict[str, Any]:
    ws = get_workspace(ws_id)
    if ws is None:
        return {"error": "workspace not found"}
    from rag.pipeline import pipeline
    response = await pipeline.query(message, top_k=ws.top_k_docs)
    return {"answer": response.answer, "sources": [s.__dict__ for s in response.sources],
            "workspace": ws.name}
