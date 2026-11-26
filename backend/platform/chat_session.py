"""LobeChat-inspired multi-provider chat session models."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    CHAT = "chat"
    RAG = "rag"
    AGENT = "agent"
    WORKFLOW = "workflow"


class ContentPart(BaseModel):
    type: str
    text: str = ""


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool: str
    result: Any = None


class Message(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str | list[ContentPart] = ""
    model_used: str | None = None
    tokens: int | None = None
    cost_usd: float | None = None
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default"
    model: str = "auto"
    previous_model: str = ""
    system_prompt: str = ""
    messages: list[Message] = Field(default_factory=list)
    plugins_enabled: list[str] = Field(default_factory=list)
    mode: ChatMode = ChatMode.CHAT
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def switch_model(self, model: str) -> None:
        self.previous_model = self.model
        self.model = model


SESSIONS: dict[str, ChatSession] = {}


def create_session(user_id: str = "default", model: str = "auto") -> ChatSession:
    session = ChatSession(user_id=user_id, model=model)
    SESSIONS[session.id] = session
    return session


def get_session(session_id: str) -> ChatSession | None:
    return SESSIONS.get(session_id)


def list_sessions(user_id: str | None = None) -> list[ChatSession]:
    return [s for s in SESSIONS.values() if not user_id or s.user_id == user_id]
