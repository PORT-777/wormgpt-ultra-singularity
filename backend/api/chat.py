import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.plugins.deps import get_runtime
from backend.plugins.runtime import PluginExecutionError

logger = logging.getLogger("ChatAPI")
router = APIRouter()


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
                system=_system_prompt(user_id, len(all_tools)),
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
