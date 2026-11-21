# Claude-compatible plugins for PORT 777 AI

The project ships two plugin bundles that follow the Claude plugin layout:

```
plugins/<plugin-name>/
├── .claude-plugin/plugin.json   manifest (name is permanent)
├── skills/<skill>/SKILL.md      model-invoked playbook
├── commands/<command>.md        slash command / chat skill
├── .mcp.json                    remote MCP server (NO secrets)
├── README.md                   40+ words
└── LICENSE                     MIT
```

- `plugins/port777-ai` — platform health, model catalog, vendor skill search and real isolated Linux computers.
- `plugins/port777-task-manager` — persistent tasks created from the conversation.

The shared MCP server lives in `mcp-server/server.mjs`. It is stateless
(Streamable HTTP, MCP 2.0 style): a fresh server is built per request, no
sessions, no credentials in `.mcp.json`. It talks to the real backend through
`PORT777_BACKEND_URL` (default `http://127.0.0.1:7777`) and an optional
`PORT777_API_TOKEN` held only in the server environment.

## Run and test locally

```bash
cd mcp-server
npm install
PORT=3000 npm start
```

```bash
curl -sS -X POST http://127.0.0.1:3000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Claude Code:

```bash
claude --plugin-dir ./plugins/port777-task-manager
claude plugin validate ./plugins/port777-ai
claude mcp add --transport http port777 http://127.0.0.1:3000/mcp
```

Before publishing, replace the local URL in each `.mcp.json` with the real
production URL — the bundles already ship `https://mcp.port777.ai/mcp`, which
must be deployed before publishing. For local development, run the server on
`127.0.0.1:3000` and point your Claude config at it temporarily; never commit
that override. Set `MCP_SERVER_URL` in the deployment environment to keep the
MCP App UI domain consistent.

## Validation

```powershell
powershell -File scripts/validate_plugins.ps1
```

Checks manifest name, license, README word count, skill frontmatter, secret-free
`.mcp.json`, publish-blocking files, and marketplace paths.

## Rules

1. No API keys, tokens or passwords in `.mcp.json` — every installer receives it.
2. `name` never changes after publishing; change `displayName` instead.
3. `SKILL.md` `description` describes *when* the skill fires, not what the file is.
4. README is at least 40 words (code does not count).
5. LICENSE must exist (or be declared in `plugin.json`).
6. No `.DS_Store`, `Thumbs.db`, `__MACOSX`.
7. MCP App domain = first 32 hex chars of SHA-256(server URL) + `.claudemcpcontent.com`.
8. Stateless MCP: new server per request, no sessions.
9. Same URL in `.mcp.json` and the directory to avoid duplicate tools.
10. Validate every surface: Claude Code, then claude.ai, then Cowork.

## Publishing (requires your approval)

GitHub repository must be public and contain only source, migrations and
plugin bundles — never `.env`, real keys, database dumps or user files.
Submit at `claude.ai/directory/manage` after `claude plugin validate` passes.
Nothing is pushed or published automatically.
