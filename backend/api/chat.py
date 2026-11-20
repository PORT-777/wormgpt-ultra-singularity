import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.plugins.deps import get_runtime
from backend.plugins.runtime import PluginExecutionError

logger = logging.getLogger("ChatAPI")
router = APIRouter()


def language_instruction(text: str) -> str:
    """Force the model to mirror the language of the operator's latest message."""
    if re.search(r"[\u0600-\u06FF]", str(text or "")):
        return "Reply entirely in Arabic (العربية), matching the user's language. Do not switch to English."
    return "Reply in the same language as the user's latest message. Match it exactly; do not switch languages."


# --------------------------------------------------------------------- schemas

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = True
    model: Optional[str] = None


# --------------------------------------------------------------- agent bridge

# Replace with your real LLM client. Interface: async generator yielding dicts
# of shape {"type": "text", "content": ...} or
# {"type": "tool_use", "tool_name": ..., "parameters": {...}, "id": ...}
from backend.ai.client import ai_client  # noqa: E402


BUILT_IN_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Return basic host information for context.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _system_prompt(user_id: str, tool_count: int) -> str:
    return (
        "You are a cybersecurity AI agent. "
        f"You currently have {tool_count} tools available, including any plugins "
        "the user has installed and enabled. Use plugin tools when they fit the task; "
        "call them by their fully-qualified name (e.g. virustotal.lookupHash)."
    )


async def _execute_builtin(tool_name: str, parameters: Dict[str, Any]) -> Any:
    if tool_name == "system_info":
        import platform
        import sys

        return {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "machine": platform.machine(),
        }
    raise ValueError(f"Unknown built-in tool: {tool_name}")


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest, x_user_id: Optional[str] = Header(None)) -> Any:
    """
    Streams the agent's reply while resolving tool calls against plugin runtime.
    Plugin failures are surfaced as tool_result payloads, never as stream crashes.
    """
    from fastapi.responses import StreamingResponse

    user_id = x_user_id or "default_user"
    runtime = get_runtime()

    async def event_source() -> AsyncGenerator[str, None]:
        try:
            plugin_tools = await runtime.get_user_tools(user_id)
        except Exception as exc:
            logger.error("Tool discovery failed: %s", exc)
            plugin_tools = []

        all_tools = BUILT_IN_TOOLS + plugin_tools

        try:
            async for chunk in ai_client.stream(
                messages=[m.model_dump() for m in request.messages],
                system=_system_prompt(user_id, len(all_tools)) + "\n\n" + language_instruction(
                    next((m.content for m in reversed(request.messages) if m.role == "user"), "")
                ),
                tools=all_tools,
            ):
                if chunk.get("type") == "tool_use":
                    tool_name = chunk["tool_name"]
                    params = chunk.get("parameters", {})
                    call_id = chunk.get("id", tool_name)

                    try:
                        if "." in tool_name:
                            result = await runtime.execute_tool(user_id, tool_name, params)
                        else:
                            result = await _execute_builtin(tool_name, params)

                        payload = {
                            "type": "tool_result",
                            "tool_call_id": call_id,
                            "tool_name": tool_name,
                            "status": "ok",
                            "result": result,
                        }
                    except PluginExecutionError as exc:
                        payload = {
                            "type": "tool_result",
                            "tool_call_id": call_id,
                            "tool_name": tool_name,
                            "status": "error",
                            "error": exc.message,
                        }
                    except Exception as exc:
                        logger.exception("Tool execution crashed: %s", tool_name)
                        payload = {
                            "type": "tool_result",
                            "tool_call_id": call_id,
                            "tool_name": tool_name,
                            "status": "error",
                            "error": str(exc),
                        }

                    yield f"data: {json.dumps(payload)}\n\n"
                else:
                    yield f"data: {json.dumps(chunk)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.exception("Stream failure")
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    if not request.stream:
        # Non-streaming path — collect then return
        buffer: List[str] = []
        async for line in event_source():
            buffer.append(line)
        return {"raw": "".join(buffer)}

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.get("/chat/tools")
async def list_active_tools(x_user_id: Optional[str] = Header(None)):
    """What the agent can call right now — used by the chat plugin badge."""
    runtime = get_runtime()
    tools = await runtime.get_user_tools(x_user_id or "default_user")
    return {"count": len(tools), "tools": tools}

# -------------------------------------------------------------------------
# Main chat endpoint used by the UI. Bridges the normal conversation to the
# real AgentEngine tool loop instead of a separate execution panel.
# -------------------------------------------------------------------------
@router.post("/chat")
async def ui_chat(request: Request) -> Any:
    from fastapi.responses import JSONResponse, StreamingResponse

    try:
        req = await request.json()
    except Exception:
        req = {}
    messages = req.get("messages") or []
    user = ""
    history: List[Dict[str, str]] = []
    for item in messages:
        role = str(item.get("role", ""))
        content = str(item.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
        if role == "user" and not user:
            user = content
    if not user:
        user = str(req.get("message") or "").strip()

    sid = str(req.get("session_id") or "").strip()
    try:
        import storage

        if sid and user:
            storage.add_message(sid, "user", user)
    except Exception as exc:
        logger.error("session user-message write failed: %s", exc)

    project_path = str(req.get("project_path") or req.get("workspace_path") or "").strip()
    try:
        from tools.base import set_project

        set_project(project_path)
    except Exception:
        pass

    try:
        import configs as config

        full_access = True if getattr(config, "ZERO_REFUSAL", False) else bool(req.get("full_access", False))
    except Exception:
        full_access = bool(req.get("full_access", False))

    try:
        from backend.agent_engine import ENGINE
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": {"message": f"engine unavailable: {exc}", "type": "server_error"}})

    if ENGINE is None:
        return JSONResponse(status_code=503, content={"error": {"message": "engine unavailable", "type": "server_error"}})

    system_prompt = str(req.get("system_prompt") or req.get("systemPrompt") or "").strip() or None
    if project_path:
        system_prompt = (
            f"Active project directory: {project_path}. All file operations and "
            "CodeIntelligence tasks target this project unless the user says otherwise.\n\n"
            + (system_prompt or "")
        )
    system_prompt = (system_prompt or "") + "\n\n" + language_instruction(user)

    model_name = str(req.get("model") or "auto")
    stream = bool(req.get("stream", True))

    streamed_final: List[str] = []

    async def events():
        try:
            async for ev in ENGINE.run_stream(
                user,
                history=history or None,
                model_route=str(req.get("model_route") or "auto"),
                model_name=model_name,
                full_access=full_access,
                depth=str(req.get("depth") or "standard"),
                system_prompt=system_prompt,
            ):
                if ev.get("type") == "final" and ev.get("data"):
                    streamed_final.append(str(ev["data"]))
                yield f"data: {json.dumps(ev, default=str, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'data': f'{type(exc).__name__}: {exc}'}, ensure_ascii=False)}\n\n"
        if sid and streamed_final:
            try:
                import storage

                storage.add_message(sid, "assistant", streamed_final[-1])
            except Exception as exc:
                logger.error("session assistant-message write failed: %s", exc)
        yield "data: [DONE]\n\n"

    if stream:
        return StreamingResponse(
            events(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    parts: List[str] = []
    final = ""
    async for line in events():
        if not line.startswith("data: ") or "[DONE]" in line:
            continue
        try:
            ev = json.loads(line[6:].strip())
        except Exception:
            continue
        kind = ev.get("type", "")
        data = ev.get("data")
        if kind == "stream" and data:
            parts.append(str(data))
        elif kind == "final" and data:
            final = str(data)
    if not final:
        final = "".join(parts)
    return {"status": "ok", "final": final, "project_path": project_path}

