# Internal API routes (`/api/internal/*`)

All routes are backend-only. No frontend file calls them.

Authentication: header `x-internal-key` must equal `INTERNAL_API_KEY`. When the
key is unset, every route returns **503** (fail closed). Rate limit: 100 req/min
per service (`EXTERNAL_RATE_LIMIT`). Every route returns `{available:false, reason}`
on provider failure — external errors never crash the platform.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/internal/services` | List all registered integrations with availability |
| GET | `/api/internal/health/all` | Health dashboard across every integration |
| GET | `/api/internal/services/{service}/health` | Health of one integration |
| POST | `/api/internal/services/{service}/query` | Call an action: `{action, payload, use_cache}` |

Services are addressed by their registry name (44 declared): `openai`, `anthropic`,
`cohere`, `huggingface`, `nlpcloud`, `witai`, `dialogflow`, `cloudmersive-nlp`,
`perspective`, `wolfram`, `clarifai`, `imagga`, `skybiometry`, `roboflow`, `irisnet`,
`inferdo`, `google-stt`, `gladia`, `assemblyai`, `gandr`, `wavespeed`, `openrouter`,
`aimlapi`, `xiurouter`, `unorouter`, `edenai`, `spamhunter`, `summarize-ai`,
`customgpt`, `ai-learning-engine`, `limitreset`, `openrouter-models`, `pollinations`,
`serpapi`, `crawl4ai`, `snaprender`, `github`, `transcriptfetch`, `finsignals`,
`openweathermap`, `restcountries`, `newsapi`, `coingecko`, `nasa`.

Internal capability modules (imported directly by the backend, not separate HTTP
services): `external_apis/rag/*`, `agents/*`, `documents/*`, `models/*`, `eval/*`,
`streaming/*`, `platform/*`. Their entry points are used by the orchestration layer
in `external_apis/platform/router.py` and `enricher.py`.
