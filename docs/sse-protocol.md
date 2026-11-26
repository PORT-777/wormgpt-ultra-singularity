# SSE Protocol

Endpoint: `GET /api/internal/stream/sse/{session_id}?prompt=...&model=...`
Header: `x-internal-key: <INTERNAL_API_KEY>`

Every event is a line of `data: {json}\n\n`. The stream ends with `data: [DONE]\n\n`.

| `type` | Payload |
|---|---|
| `session_start` | `{"session_id": "..."}` |
| `token` | `{"content": "..."}` |
| `done` | `{"tokens_used": 123}` |
| `error` | `{"message": "..."}` |

No frontend file consumes this stream yet — the contract is prepared only.
