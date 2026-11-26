# 🔥😈 PORT 777 EVIL ☠️🔥👹 v6 :: Universal Files + Intelligence Inputs Protocol

v5 (crew, deep RAG, scoped god-mode, voice, scheduler, audit, docker) +
**v6 additions** â€” implemented per the 5-phase plan:

| Phase | Status in v6 |
|---|---|
| 1. Structure | `/backend` (configs/, memory/, tools/, tests/, data/, workspace/) + `/frontend` â€” already the required modular tree |
| 2. ReAct engine | self-correction with failure ledger, up to 10 smart retries, salvage mode, crew review â€” **shipped since v5** |
| 3. Tool factory | **CppCodeExpert** (generate/optimize/review/debug + 2nd-pass internal verification), **MemoryLogicCalculator** (pointer chains/struct layout, pure math, unit-tested), **ReverseEngineeringAnalyzer** (educational breakdown, analysis-only) |
| 4. UniversalFileManager + SystemCommander | **NEW**: `search` (regex across text files, line numbers, junk-dir skip), **`extract`** (zip/tar with zip-slip guard; .rar â†’ convert-to-zip message), **`hex`** (debugger-style hexdump slice: addr + hex + ASCII); file chunking/streaming already handles huge binaries. Upload endpoint: `POST /api/files/upload` (200MB cap, instant type/size/preview profile = "Intelligence Inputs protocol"). Sidebar `ï¼‹ upload` button. |
| 5. Dashboard | real-time ReAct trace (SSE), dual Chat/Terminal UI, tech-console highlight + copy button for the three specialist tools |

**v6.1 :: self-extension layer (human-in-the-loop)**

| Feature | What it does |
|---|---|
| **Citation Gate** | engine-level anti-hallucination rule: any raw address/offset (hex) in a Final Answer WITHOUT tool evidence from this run triggers a corrective round, then an explicit `âš  Citation gate` warning is appended (never silently guesses). |
| **IntegrityGuard** (tool) | hardening suite for the user's OWN builds: `checksum` (SHA-256 + CRC32), `create_baseline` / `verify_baseline` (per-file SHA-256 + 4KB block hashes) â€” tamper verify reports the **first divergent block offset in hex** per changed file. Read-only; manifests live in `workspace/integrity/`. |
| **YAML Skill Packs** | `backend/skills_packs/*.yaml` add PLAYBOOK instructions to the system prompt at runtime (no code, no restart). Starter pack: `offset_forensics_playbook` (evidence-ladder for offsets/structs). Agent GAINS skills by ingesting packs â€” but can never inject code into itself. |
| **ProposalChange** (tool + API) | the agent's ONLY route to change itself: submits `{title, target_path, rationale, content}` â†’ stored in SQLite + reviewable `.md` under `workspace/proposals/pending/`. UI panel lists pending proposals with approve/reject. Approve applies workspace-relative and `@backend/...` (agent's own tree) targets; absolute host paths are NEVER auto-written â€” content is exported under `proposals/imported/` for manual apply. |
| **Engine bugs fixed** | `step_final` tuple leak into crew results, `sessions` insert schema mismatch. (40 tests green.) |

Ownership boundary (context, not an enforced gate): the agent helps you build +
debug **your own** software and analyze/learn from code and binaries you
own or are licensed to. This is a statement of intended use; nothing in the
shipped build enforces it. The authoritative description of what the code
actually does is the **ZERO_REFUSAL behavior matrix** below. In particular the
single prompt source `backend/prompts/system_prompt.txt` contains a
"Technical precision" block that frames offensive-sounding requests in
engineering terms and relabels colloquial terms silently.

---

## Claude-compatible plugins

Two publishable plugin bundles with MCP connectors, skills, commands and UI
metadata live under `plugins/`. See [`docs/PLUGINS.md`](docs/PLUGINS.md) for
the layout, local MCP server, validation and publishing checklist.

## Vendor hub (repos → tools / plugins / MCP / skills)

All vendored repositories are indexed by `backend/vendor_hub.py` and exposed
automatically on every message through:

- `VendorTool` (agent tool, actions: `repos`, `info`, `skills`, `skill`, `search`, `files`, `read`, `plugins`)
- MCP tools `vendor_*` on the `wormgpt-local` server
- plugins `vendor_<repo_id>` in `backend/plugins_catalog/vendor/`
- the always-on skill pack `backend/skills_packs/vendor-hub.md`

Repos: AutoGPT, Claude Skills, OpenHands, ECC, Hermes Agent, Lunar Source,
DeepSeek Harness, Career Ops, Oh My Zsh, Ruflo, Agentic Awesome Skills.
Run `git submodule update --init --recursive` after cloning to fetch them.
All access is read-only and confined to `vendor/`.

## Persistent infrastructure (Supabase / Render)

All persistent records use `backend/database.py`: SQLite locally, Supabase
PostgreSQL via `DATABASE_URL` in production. Uploaded/generated files use
`backend/storage_backends.py`: local filesystem for development, Supabase
Storage (or an S3-compatible adapter) in production.

- Setup: [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md)
- Migrations and data transfer: [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md)
- Render deployment: [`docs/RENDER_DEPLOYMENT.md`](docs/RENDER_DEPLOYMENT.md)
- Health checks: `/health` (503 when the database is unreachable) and `/api/health`.
- Migration runner: `cd backend && python migrate.py` (additive only, never destructive).
- Pre-push secret scan: `powershell -File scripts/check_secrets.ps1`.

## Current deployment notes

### ZERO_REFUSAL behavior matrix

The flag is read from `ZERO_REFUSAL` in `backend/.env` (shipped value: `true`)
by `backend/configs/settings.py`. It changes runtime behaviour as follows:

| Behaviour | `ZERO_REFUSAL=true` (shipped default) | `ZERO_REFUSAL=false` (gated) |
|---|---|---|
| Host tools / shell | implicit for every run — `backend/tools/base.py::full_access` | only via per-request `full_access: true` from the UI/API |
| Ask/Plan mutating-tool guard | disabled — `backend/agent_engine.py::is_mode_blocked` | mutating tools blocked in `ask`/`plan` |
| Sensitive-operation approvals | auto-approved, `decided_by="zero_refusal"` — `backend/approvals.py` | created as `pending`, require explicit approve/reject |
| MCP execution | `execution_requires_full_access: false` — `backend/mcp_manager.py::status` | `true` |
| Per-request God-mode toggle | not required | required |

Destructive shell commands and protected OS paths remain blocked by the tool
denylist in both states; `ADMIN_PASSWORD` and a valid login token are still
required for API requests. The header shows the red FULL ACCESS pill during a
run. Tests: `backend/tests/test_zero_refusal_policy.py` exercises both columns
and asserts the shipped default.

### Refusal classifier and prompt source

- `backend/tests/refusal_corpus.py` — 38 labeled cases (21 refusals, 17 non-refusals including capability statements, quality statements and polite-but-cooperative replies).
- `cd backend && python tests/refusal_baseline.py` — standalone harness, writes `tests/refusal_baseline_report.json` and exits 0 only when every case is classified correctly; `--no-strict` records behaviour without failing.
- Measured on this build: the original 26-case corpus against the pre-narrowing regex gave TP=14 / FP=12 / TN=0 / FN=0, false-positive rate 1.0000, accuracy 0.5385, strict exit 1 (`refusal_baseline_before.json`). The current 38-case corpus against the narrowed regex gives TP=21 / FP=0 / TN=17 / FN=0, accuracy 1.0000, exit 0. It includes an observed Egyptian-dialect refusal (`مش قادر أساعدك...`) that the MSA-only Arabic rules missed; `ar_egypt_refusal` now covers it. The two runs use different corpus sizes; do not compare raw counts across them.
- The system prompt has one source of truth, `backend/prompts/system_prompt.txt` (7923 → 4580 chars, 215 → 57 lines); critical rules are first and last. `backend/tests/test_system_prompt.py` guards this.

### Agent reliability (offline diagnostics)

- `cd backend && python agent_doctor.py` prints an offline readiness report (tool count, tools that fail to instantiate, skill-pack count, always-on packs, sample task→pack selection, prompt source/size, provider readiness flags) and writes `backend/agent_doctor_report.json`. No network calls and no keys are printed.
- Measured on this build: 44 registered tools, 0 broken on init, 1174 skill packs across 8 libraries, prompt 4580 chars, 1 `{tools}` placeholder.
- Fixes made: removed a duplicated `get_schema()` in `tools/base.py`; `Action Input` now uses balanced JSON extraction (handles nested braces, arrays, single quotes and trailing prose) instead of a greedy regex; skill relevance is specificity-weighted with word boundaries and plural handling, so generic triggers like `tool` no longer make selection near-random and a greeting loads no task pack. Regression tests: `backend/tests/test_agent_reliability.py`.

### Native tool calling

- `backend/native_tools.py` builds OpenAI-style function definitions from the live tool registry (introspected `run()` signatures, falling back to each tool's `example` dict), binds them with `bind_tools()` when the model supports it, reads `tool_calls` from the reply and feeds `ToolMessage` results back into the next turn.
- `NATIVE_TOOL_CALLS` in `backend/configs/settings.py` (default `true`, env-overridable) controls the path. Models without `bind_tools`, or whose call fails, automatically fall back to the existing text-ReAct loop — no behaviour loss.
- Text and native paths share one guarded execution function (`_execute_tool_call`), so audit logging and the Ask/Plan mode guard apply identically to both.
- `model_router.FailoverChat.bind_tools()` delegates binding to every candidate model and returns a cloned pool, so the router no longer hides provider tool support. A first live probe exposed a bad schema (`MemoryLogicCalculator` documented `base` but `hex2dec` reads `value`); the tool description/example and required-field inference were corrected.
- Measured: 44 definitions for 44 registered tools; offline tests in `backend/tests/test_native_tools.py` cover execution, `ToolMessage` feedback, fallback and router delegation.
- Live verification (`cd backend && python tests/live_native_tools_probe.py groq`, exit 0): provider accepted all 44 definitions, returned `{"op":"hex2dec","value":"0x10"}`, tool output `0x10 = 16 (dec)`, final answer 16. Report: `backend/tests/live_native_tools_report.json`.
- `NATIVE_TOOL_LIMIT` (default 8) caps advertised function schemas and `select_tool_names()` chooses task-relevant ones. Cause: a server run returned HTTP 413 from Groq — `Limit 8000 TPM, Requested 8456` with all 44 definitions. On a 413 the limit is halved and retried before falling back to text-ReAct.
- `ModelRouter.manager()` now orders `local, groq, gemini, hf, kilo` — Kilo's endpoint returned HTTP 404 HTML and burned two retries on every plan/reflection.
- Additional fixes from the HTTP benchmark: `PythonInterpreter` used `_active_workspace()` without importing it — every execution died with `NameError`; fixed with a regression test. `MAX_PROMPT_CHARS` caps request growth, and trimming never splits a tool_call from its ToolMessage.
- Benchmark results on a freshly started server with current code: EASY `final='42'` (222s). MEDIUM invoked `UniversalFileManager` + `PythonInterpreter` correctly after the fixes but never converged (provider `Parsing failed` / client timeout). HARD invoked `MemoryLogicCalculator` repeatedly (258 events in one run) but ended with Groq `413`/`Please reduce the length of the messages or completion`. The remaining blocker is provider-side context/completion limits on multi-step reasoning, not tool availability.

- **Vendored references:** AutoGPT, Claude Skills, OpenHands, ECC and Hermes Agent are checked out under `vendor/`. See them in the UI under Advanced tools → Vendored repos, or via `GET /api/vendor/repos`.

## Release-readiness roadmap (no builds performed)

Suggested next upstream: `tauri-apps/tauri` — one React/Vite codebase can target web, Windows `.exe` and Android `.apk`, which matches this project's stack better than Electron + Cordova.

Features to add before any build:
- PWA/service-worker shell with offline cache and installable web app.
- Responsive/touch layout and safe-area handling for Android.
- PyInstaller one-file backend spec with bundled models/keys path, plus a service wrapper.
- GitHub Actions matrix: web bundle, Windows exe, Android APK artifacts.
- Secure secret storage per platform (Credential Manager / Keystore), replacing plain `.env` writes for OAuth clients.
- Auto-update endpoint, crash reports, and signed plugin manifests.
- Local uncensored model packaging (llama.cpp) so the zero-refusal brain works offline.
- **OAuth linking:** Connect opens a new browser tab on the provider's consent page; the callback posts the result back and shows a linked message in the original page. One-time Client ID/Secret setup is handled in the inline dialog.
- **UI polish:** `frontend/src/ui/port777-polish.css` adds themed icons, hover motion and card animations; can be disabled with `prefers-reduced-motion`.
- **Tests:** `cd backend && python -m pytest -q` now works with no environment overrides — `tests/conftest.py` forces local SQLite before any project module reads `DATABASE_URL` (override with `TEST_USE_REAL_DB=1`). Measured: before this work 248 passed, 1 skipped; after **370 passed, 2 skipped, exit 0, zero warnings**. All former `datetime.utcnow()` / year-less `strptime()` deprecations were removed while preserving timestamp formats. Previously, plain `pytest -q` failed at collection with exit 4 because the shipped `.env` selects Supabase PostgreSQL and `psycopg2` is not a test dependency.

---

# 🔥😈 PORT 777 EVIL ☠️🔥👹 v5 :: Crew + Deep Memory

v4 capabilities (token streaming, SQLite, audit trail, vision loop,
scheduler, voice, auth, docker) + **v5 additions**:

| Feature | What it does |
|---|---|
| **Crew Logic** | the Planner assigns a persona per subtask â€” ðŸ”¬ researcher / ðŸ’» coder / ðŸ§ª tester / ðŸ” reviewer. After each subtask, the Manager delivers a **Quality Gate**: `pass` or `fix` with concrete numbered feedback (one revision round, streamed to the UI as `crew`/`review` events). |
| **Project-scoped memory** | task memories, workspace file chunks, and session handoffs are isolated by the configured `WORKSPACE_DIR`; one project cannot recall another project's context. ChromaDB and JSON fallback both support file recall. Changed/deleted files remove stale chunks; long files are split without dropping their tail. Manual reindex: `POST /api/memory/index`; inspect or forget individual memories in the sidebar. |
| **Live tool-aware planning** | the planner receives the current registered tool catalog at runtime instead of a stale hard-coded list; incomplete steps without a concrete detail are rejected before execution. |
| **Scoped God-mode** | Full Access now lives in a `contextvars.ContextVar` â€” concurrent chats can never leak one user's God-mode grant into another's run (previous global-flag bug fixed). |
| **SQLite WAL** | writer-reader concurrency with busy-timeout â€” scheduler + chat no longer collide. |
| **Whisper STT fallback** | browsers without Web Speech API record via MediaRecorder â†’ `POST /api/transcribe` â†’ faster-whisper returns the transcript. |
| **TTS replies** | ðŸ”ˆ voice toggle â€” final answers are spoken aloud via offline pyttsx3 (`GET /api/tts`). |
| **Browser self-healing** | "Target closed" crashes relaunch Chromium transparently once. |
| **Clickable history** | sidebar sessions load from SQLite on click; `ï¼‹ new` button. |

An autonomous **Agentic Operating System** â€” general-purpose engineering /
research / automation agent with a ReAct + Self-Correction engine,
Omniscient Memory (RAG), a modular Tool Factory, **closed-loop Vision**
(screenshot â†’ Gemini sees â†’ acts), **scheduled background tasks**,
**voice control**, dual UI (Chat â†” Terminal), and an explicit, user-granted
**Full Access Mode** for shell + host filesystem operations with a full
audit trail.

> âš ï¸ **Security & scope note:** engineering/dev/automation platform
> (DeVin/AutoGPT-class for your own machine). Not an offensive-security
> tool. Full Access Mode requires an explicit UI toggle per request, is
> denylisted against irreversibly destructive commands, **logged to
> `data/audit.jsonl` + SQLite**, and is shown as a red pill the whole run.
> API keys shared in chat were exposed: rotate.

---

## Architecture Map (v3)

```
D:\xxxGPT
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ main.py              # v4: chat SSE (+auth gate), login, tasks, audit,
â”‚   â”‚                        #     files, history (SQLite), system, memory
â”‚   â”œâ”€â”€ agent_engine.py      # v4: Memoryâ†’Planâ†’Loopâ†’Reflect(ledger)â†’Audit
â”‚   â”‚                        #     â†’Salvageâ†’Final + TOKEN STREAMING of answers
â”‚   â”œâ”€â”€ planner.py           # Manager decomposes goals â†’ JSON subtasks
â”‚   â”œâ”€â”€ model_router.py      # Groq/Gemini/HF + fallback chain + manager()
â”‚   â”œâ”€â”€ scheduler.py         # background "agent cron" (interval tasks + Telegram push)
â”‚   â”œâ”€â”€ storage.py           # SQLite: sessions/messages/scheduled_tasks/audit_log
â”‚   â”œâ”€â”€ configs/
â”‚   â”‚   â”œâ”€â”€ __init__.py      # `import configs as config`
â”‚   â”‚   â””â”€â”€ settings.py      # env, limits (MAX_TOOL_RETRIES=10), timeouts
â”‚   â”œâ”€â”€ memory/              # Omniscient Memory (RAG)
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â””â”€â”€ store.py         # ChromaDB persistent (+JSON fallback)
â”‚   â”œâ”€â”€ data/                # 🔥😈 PORT 777 EVIL ☠️🔥👹.db + audit.jsonl (gitignored)
â”‚   â”œâ”€â”€ memory_data/         # vector store (gitignored)
â”‚   â”œâ”€â”€ tests/               # pytest: engine loop, reflection, sandbox, storage
â”‚   â”œâ”€â”€ Dockerfile + pytest.ini + requirements-dev.txt
â”‚   â”œâ”€â”€ tools/               # Tool Factory (auto-discovered classes)
â”‚   â”‚   â”œâ”€â”€ base.py          # Tool ABC, sandbox, host denylist, FULL ACCESS gate
â”‚   â”‚   â”œâ”€â”€ python_interpreter.py   # sandboxed subprocess code execution
â”‚   â”‚   â”œâ”€â”€ web_search.py           # DuckDuckGo (ddgs)
â”‚   â”‚   â”œâ”€â”€ file_manager.py         # FileSystemMaster (2 scopes, chunked IO, streaming download)
â”‚   â”‚   â”œâ”€â”€ browser_tool.py         # Playwright web automation
â”‚   â”‚   â”œâ”€â”€ system_control.py       # PyAutoGUI desktop control
â”‚   â”‚   â”œâ”€â”€ shell_commander.py      # SystemCommander (God-mode + denylist)
â”‚   â”‚   â”œâ”€â”€ vision_tool.py          # Gemini vision on local images (closed-loop seeing)
â”‚   â”‚   â”œâ”€â”€ cpp_code_expert.py      # senior C++ generate/optimize/review/debug (own projects)
â”‚   â”‚   â”œâ”€â”€ memory_calc.py          # pointer/offset math (no process IO) + struct layout
â”‚   â”‚   â”œâ”€â”€ re_analyzer.py          # educational ASM/C++ logic breakdown (analysis only)
â”‚   â”‚   â””â”€â”€ telegram_tool.py        # Bot API reports
â”‚   â””â”€â”€ workspace/           # agent sandbox (auto-created)
â””â”€â”€ frontend/                # Vite + React 18 + Tailwind v4
    â””â”€â”€ src/
        â”œâ”€â”€ App.jsx          # SSE reader Â· TOKEN STREAMING bubble Â· dual UI Â·
        â”‚                    #   god-mode switch Â· login Â· auth headers
        â””â”€â”€ components/
            â”œâ”€â”€ VoiceButton.jsx # ðŸŽ¤ Web Speech API mic (ar-EG) â†’ composer
            â”œâ”€â”€ Sidebar.jsx  # files Â· memory Â· scheduled tasks Â· history
            â”œâ”€â”€ StatusBar.jsx# Planning/Thinking/Executing/Reflecting + FULL ACCESS
            â”œâ”€â”€ TraceFeed.jsx# plan checklist + thinking trace
            â””â”€â”€ Terminal.jsx # tool execution log (expandable)
```

## The two modes

| Mode | What the agent can touch |
|---|---|
| **Standard Chat** (default) | workspace-sandboxed files, code interpreter, web search/browse, Telegram |
| **Full Access (God-mode)** | + shell execution (`SystemCommander`) + any host path (`FileSystemMaster scope="host"`), with denylist guards |

In gated mode (`ZERO_REFUSAL=false`), God-mode is granted when the user clicks `ðŸ”’ sandbox â†’ âš¡ FULL ACCESS`
in the composer (confirm dialog), which flows into `POST /api/chat` as
`full_access: true` **for that request only**. With `ZERO_REFUSAL=true` — the current default in both
`backend/.env` and `backend/configs/settings.py` — host tools, shell and mutating
actions are implicit for every run and no per-request toggle or approval prompt
is required. `ADMIN_PASSWORD` must be configured and a valid login token
is required; without it, API requests cannot enable Full Access. Destructive
shell commands and protected operating-system paths remain blocked even
after login. The header shows a red `âš¡ FULL ACCESS` pill during the run so
the operator always knows the current power level.

## Hyper-Persistence engine (how "never give up" is engineered)

1. **Failure ledger** â€” every failed attempt (tool + args + error) is
   accumulated and fed to the Manager (Gemini) reflection prompt, so
   retry #5 has strictly more information than retry #2.
2. **Up to 10 smart retries** per subtask (`MAX_TOOL_RETRIES=10`) +
   loop budget of 14 iterations.
3. **Identical-attempt detection** â€” repeating the same failing tool/args
   is detected and forces a strategy change (the reflection prompt is
   injected with a forced-variety warning).
4. **Salvage mode** â€” budget exhausted? The brain still produces an
   honest best-effort answer: what succeeded, what failed and why, and
   the exact next step for the user. Silence is not an option; fake
   success is forbidden by the system prompt.
5. **Plan-level persistence** â€” a failed subtask doesn't kill the
   master goal; later steps continue with remaining context.

## Multi-model routing (roles)

| Role | Model | Responsibilities |
|---|---|---|
| Manager (strategy) | **Gemini 1.5 Pro** | planning, error-diagnosis over the ledger, long docs, screen-image vision |
| Executor (loops) | **Groq Llama-3.1-70b** | fast Thoughtâ†’Action micro-decisions |
| Specialist | **HF Inference API** | niche tasks; also the final fallback |

## Setup

```bash
# backend (Python 3.11+)
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium          # once, for WebAutomator
uvicorn main:app --reload --host 127.0.0.1 --port 7777

# frontend (Node 18+)
cd frontend
npm install
npm run dev            # http://localhost:5173 (proxies /api â†’ :7777)

# tests (no API calls â€” scripted fake brains)
pip install -r requirements-dev.txt
pytest

# production: full stack in one command
docker compose up --build
```

Docker publishes the backend and frontend on `127.0.0.1` by default, so
they are not exposed to other machines on the network. Set `BACKEND_PORT`
or `FRONTEND_PORT` to change the local port. For remote access, put the
stack behind an authenticated reverse proxy rather than binding these
services directly to every network interface.

### New in v4
| Feature | How it shows up |
|---|---|
| **Token streaming** | the Final Answer types itself live in the chat (SSE `stream` events; only post-"Final Answer:" tokens surface, actions stay parsed) |
| **SQLite persistence** | sessions/history/tasks survive restarts (`backend/data/🔥😈 PORT 777 EVIL ☠️🔥👹.db`) |
| **Audit trail** | every Full-Access tool call â†’ `GET /api/audit` + `data/audit.jsonl` |
| **Vision loop** | `SystemControl(screenshot)` â†’ `Vision(...)` â†’ Gemini describes the real screen â†’ agent acts |
| **Scheduled tasks** | sidebar "agent cron": prompt + interval â†’ backend runs it forever, pushes to Telegram |
| **Voice control** | ðŸŽ¤ mic button (Web Speech API, ar-EG) fills the composer |
| **Auth** | set `ADMIN_PASSWORD` in `.env` â†’ login required for Full Access / tasks / audit (`/api/login`, HMAC token, 12h) |
| **Docker** | `docker compose up --build` (backend + nginx frontend + volumes) |

Telegram reporting (optional): BotFather token + chat id in `.env`.

## God-mode example (safe demo)

Toggle âš¡ FULL ACCESS, then:

- *"check python version and pip list via SystemCommander, save output to system_report.md"*
- *"inventory user directories with SystemMaster (`dir /s` bounded), summarize the 5 largest folders"*
- *"clone a small git repo and run its tests"* (git â†’ build â†’ test chain with retries)

Without the toggle, those tools reply `denied â€” requires FULL ACCESS mode`.

## Production hardening roadmap

- JWT/API-key auth + rate limits in front of `/api/chat`.
- Per-session audit log (JSONL) of every shell command in God-mode.
- Docker/gVisor boxing for PythonInterpreter.
- Parallel subtask execution (asyncio.gather) for independent plan steps.
- Token-level streaming for the fastest possible UI feedback.
# WormGPT_Ultra_Singularity

Run (from the project root, backend on port 7777):
```bash
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 7777
```
Open http://127.0.0.1:7777/ . The frontend build in `frontend/dist` is served by the backend.
