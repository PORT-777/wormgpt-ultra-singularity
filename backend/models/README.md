# Local uncensored brain

`configs/settings.py` already routes to a local OpenAI-compatible server:

- `LOCAL_BASE_URL=http://127.0.0.1:8081/v1`
- `LOCAL_MODEL_NAME=dolphin`
- `LOCAL_ENABLED=true`

To make the zero-refusal engine work offline, run a llama.cpp-compatible server
and point it at a GGUF model placed in this directory. Example:

```bash
# download your preferred uncensored GGUF into backend/models/
python scripts/fetch_local_model.py <url> dolphin.gguf

# serve it on 127.0.0.1:8081
llama-server -m models/dolphin.gguf --port 8081 --host 127.0.0.1
```

Packaging builds should include this directory so the shipped artifact keeps
the offline brain. No model is bundled or downloaded by default.
