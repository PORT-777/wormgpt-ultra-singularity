"""Server-Sent Events formatter."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator


async def sse(events: AsyncGenerator[dict[str, Any], None]) -> AsyncGenerator[str, None]:
    async for event in events:
        yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
    yield "data: [DONE]\n\n"
