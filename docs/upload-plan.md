# Chunked GitHub upload plan

## Observed state (2026-11-27)
- Authenticated identity: `PORT-777` (verified via `GET /user`, HTTP 200).
- Token scopes include `repo` (full private-repo access).
- Repository created: `PORT-777/wormgpt-ultra-singularity`, **private**, empty.
- `.gitignore` verified; no `.env` or key files are tracked. Tracked secret scan: clean.
- History was rewritten with `git filter-repo` to remove a 168 MB build artifact.
  Repack size dropped from 201.68 MiB to **32.08 MiB**; no tracked file exceeds 100 MB.
- First full push failed **before** this cleanup (GH001, 168 MB file). A second full
  push was started in the background and has not yet reported completion.

## Chunk plan (fallback if the full push fails again)

Each chunk is pushed as its own commit so a failure is isolated. Use one shell
command per step; set the token only inside that command and reset `origin` to
the clean URL immediately afterwards.

Template (replace `<STEP>` and `<MSG>`):

```powershell
$env:GH_PAT='<TOKEN>'
$env:GIT_TERMINAL_PROMPT='0'
git remote set-url origin "https://$env:GH_PAT@github.com/PORT-777/wormgpt-ultra-singularity.git"
git -c credential.helper= push origin <BRANCH>
git remote set-url origin 'https://github.com/PORT-777/wormgpt-ultra-singularity.git'
```

| Step | Content | Approx. size | Check after step |
|---|---|---|---|
| C0 | Preflight: identity, scopes, repo, ignore rules, history, size | — | `git count-objects -vH` < 100 MB |
| C1 | Root config + docs + scripts + small dirs (`docs/`, `scripts/`, `.github/`, `*.md`, `Dockerfile`, `*.yaml`) | < 1 MB | `git ls-files` subset present on remote |
| C2 | `frontend/` (source, tests, shadcn UI) | 1.3 MB | build/typecheck unchanged |
| C3 | `backend/` source excluding generated build output | ~30 MB | no file > 100 MB |
| C4 | Remaining small dirs (`plugins/`, `core/`, `config/`, `mcp-server/`, `tests/`, `vendor/`, `workspace`) | < 1 MB | full tree matches local |
| C5 | Verification: `git status`, remote branch, API repo metadata; strip token from config | — | no credentials in `.git/config` |

## Cleanup rules
- Never persist the token in `.git/config`, `.env`, or any tracked file.
- After every push, reset `origin` to the clean HTTPS URL.
- The token was pasted in chat and used in shell commands; rotate it after the upload.
