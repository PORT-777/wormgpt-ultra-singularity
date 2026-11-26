# WebSocket Chat Protocol

Connect: `ws://host/ws/chat/{session_id}`

## Client → Server

| Message | Meaning |
|---|---|
| `{"type":"message","content":"...","mode":"chat\|rag\|agent"}` | Send a user message |
| `{"type":"interrupt"}` | Stop current generation |
| `{"type":"ping"}` | Keepalive |

## Server → Client

| Message | Meaning |
|---|---|
| `{"type":"token","content":"..."}` | Streamed token |
| `{"type":"step","content":"...","agent":"researcher"}` | Agent reasoning step |
| `{"type":"source","url":"...","title":"..."}` | RAG source |
| `{"type":"tool_call","tool":"web_search","args":{}}` | Tool invocation |
| `{"type":"tool_result","tool":"...","result":{}}` | Tool result |
| `{"type":"done","tokens":123,"cost":0.002}` | Generation complete |
| `{"type":"error","message":"..."}` | Failure |
| `{"type":"pong"}` | Keepalive response |

All messages are JSON. The connection stays open until the client disconnects.
No frontend file consumes this socket yet — the contract is prepared only.
