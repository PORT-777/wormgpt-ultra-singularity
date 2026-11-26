"""Trace every LLM call with cost, tokens, latency and previews."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable


@dataclass
class Trace:
    id: str
    timestamp: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    input_preview: str = ""
    output_preview: str = ""
    success: bool = True
    error: str = ""
    session_id: str = ""
    user_id: str = ""
    trace_type: str = "llm_call"


@dataclass
class TraceResult:
    value: Any
    trace: Trace


class LLMTracer:
    def __init__(self, path: str = "data/traces.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer: list[Trace] = []

    @staticmethod
    def _cost(model: str, tokens_in: int, tokens_out: int) -> float:
        try:
            from models.registry import MODEL_CATALOG
            spec = MODEL_CATALOG.get(model)
            if spec:
                return round(tokens_in / 1000 * spec.cost_per_1k_in +
                             tokens_out / 1000 * spec.cost_per_1k_out, 8)
        except Exception:
            pass
        return 0.0

    async def _store_trace(self, trace: Trace) -> None:
        self._buffer.append(trace)
        if len(self._buffer) >= 20:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        with self.path.open("a", encoding="utf-8") as fh:
            for t in self._buffer:
                fh.write(json.dumps(asdict(t), ensure_ascii=False) + "\n")
        self._buffer.clear()

    async def trace(self, fn: Callable[..., Awaitable[Any]], **kwargs) -> TraceResult:
        from datetime import datetime, timezone
        trace_id = str(uuid.uuid4())
        start = time.perf_counter()
        try:
            result = await fn(**kwargs)
            usage = getattr(result, "usage", None)
            tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
            tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
            content = getattr(result, "content", "")
            model = str(kwargs.get("model", ""))
            trace = Trace(
                id=trace_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                model=model, prompt_tokens=tokens_in, completion_tokens=tokens_out,
                total_tokens=tokens_in + tokens_out,
                latency_ms=int((time.perf_counter() - start) * 1000),
                cost_usd=self._cost(model, tokens_in, tokens_out),
                input_preview=str(kwargs.get("prompt", ""))[:200],
                output_preview=str(content)[:200], success=True,
                session_id=str(kwargs.get("session_id", "")),
                user_id=str(kwargs.get("user_id", "")),
                trace_type=str(kwargs.get("trace_type", "llm_call")))
            await self._store_trace(trace)
            return TraceResult(result, trace)
        except Exception as exc:
            trace = Trace(
                id=trace_id, timestamp=datetime.now(timezone.utc).isoformat(),
                model=str(kwargs.get("model", "")),
                latency_ms=int((time.perf_counter() - start) * 1000),
                success=False, error=str(exc)[:300])
            await self._store_trace(trace)
            raise


tracer = LLMTracer()
