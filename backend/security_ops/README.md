# CyberOps toolkit (`backend/security_ops`)

Deterministic, offline security and reverse-engineering toolkit exposed to the
agent as the `CyberOps` tool and to HTTP clients under `/api/security`.

- **96 actions** across 9 categories.
- **Stdlib-first**: every action works without third-party packages; optional
  parsers (pefile, capstone, yara-python, scapy, pyelftools, Pillow,
  cryptography, …) improve accuracy when installed.
- **Local only**: no analysis result or artifact leaves the machine.

## Categories

| Category | Count | Highlights |
| --- | --- | --- |
| `triage` | 7 | file type, hashes, strings, entropy, IOC extract/export, hexdump |
| `binary` | 12 | PE, ELF, Mach-O, shellcode, ROP, crypto constants, XOR, anti-analysis, intent, family, behaviour DNA, sample similarity |
| `detection` | 13 | MITRE mapping/navigator, coverage, defense gaps, YARA gen/scan, Sigma gen/convert/validate/test, query build/translate, hunt plan |
| `logs` | 7 | Windows/Sysmon/auth/web/Suricata/Zeek/cloud logs, timeline, beaconing, lateral movement, email, LOLBins, persistence |
| `network` | 5 | PCAP flows/DNS/HTTP/TLS, infrastructure clustering, TCP/UDP payload decode, packet crafting |
| `forensics` | 19 | LNK, prefetch, registry, browser DB, MFT, shellbags, jumplist, hibernation, stego/LSB, firmware, APK, IPA, bootkit, secrets, IaC, fileless, supply chain |
| `encoding` | 13 | layered auto-decode, all decoders, encoders, JWT decode/crack, certificates, hash ID, wordlists, C2 decryption, hexdump decode, Caesar, frequency, encoding ID |
| `advisory` | 15 | actor attribution, kill chain, Diamond Model, severity/SLA, STRIDE/PASTA/LINDDUN, attack surface, posture, FP tuning, anomaly explanation, zero-day, vuln chaining, patch priority, crisis comms, compliance mapping |
| `report` | 5 | technical/executive/board/hunt/lessons/compliance reports, incident narrative, chain of custody |

## Calling actions

```python
from security_ops import run_action, list_actions, capabilities

run_action("iocs", text="c2 at https://evil.example.com and 8.8.8.8")
run_action("pe", path="samples/unknown.exe")          # path/hex/base64/data
run_action("report", kind="executive", subject="INC-42",
           findings=[{"severity": "high", "finding": "beaconing"}])
list_actions()        # catalogue
capabilities()        # categories + optional dependency status
```

File-driven actions accept any of `path`, `hex`, `base64`, `text`, `data`.
Text-driven actions accept `path`, `text`, `content`. List parameters accept
JSON arrays or comma-separated strings. Alias lookup is case-insensitive and
accepts `-` or `_`; unknown actions raise `ValueError`.

## Sandbox model

- Relative paths resolve under `config.WORKSPACE_DIR` (`backend/workspace`).
- `allow_host=False` (default, and **always** for the HTTP API) rejects absolute
  paths that escape the workspace.
- `allow_host=True` is set only by the in-process agent tool, and only while the
  run has **Full Access** enabled.
- Generated artifacts are written under `workspace/{reports,iocs,...}` unless
  host access is explicitly allowed.

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/security/capabilities` | toolkit metadata, categories, action catalogue, optional deps |
| `GET` | `/api/security/actions` | action catalogue only |
| `POST` | `/api/security/run` | run one action: `{"action": "...", "params": {...}}` (flattened keys also accepted) |
| `GET` | `/api/security/health` | liveness + action count |

Errors map to HTTP: sandbox escape → `400`, missing file → `404`,
permission → `403`, unknown action → `400`.

## Agent integration

`backend/tools/cyber_ops.py` auto-registers the `CyberOps` tool. The
`cyber-ops-edition` skill pack routes malware/DFIR/detection tasks to it. Use
`{"action": "list"}` to discover actions from inside a run.

## Tests

```bash
cd backend
python -m pytest tests/test_cyber_ops.py -q
```

## Safety notes

Results are heuristics meant to structure analyst judgement. Never execute
untrusted samples; attribute actors only with corroborating evidence; preserve
evidence before destructive containment; redact secrets in reports unless the
operator explicitly needs raw values.
