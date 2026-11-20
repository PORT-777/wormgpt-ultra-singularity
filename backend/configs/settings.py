"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Central settings (configs/settings.py).

All secrets and tunables come from environment variables (.env).
The platform degrades gracefully when a provider key is missing so it
always boots, even in "reduced mode".
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ directory (configs/ is one level down)
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

# ------------------------------------------------------------------ #
#  Provider API keys
# ------------------------------------------------------------------ #
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
# ------------------------------------------------------------------ #
#  v8 :: Local model route (llama.cpp server, OpenAI-compatible)
#  Uncensored local brain: no quotas, no TPM, no refusal tuning.
# ------------------------------------------------------------------ #
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8081/v1").strip()
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "dolphin").strip()
LOCAL_ENABLED = os.getenv("LOCAL_ENABLED", "true").lower() == "true"

def _local_alive() -> bool:
    if not LOCAL_ENABLED:
        return False
    try:
        import urllib.request
        with urllib.request.urlopen(
            LOCAL_BASE_URL.replace("/v1", "") + "/health", timeout=3
        ) as r:
            return 200 <= r.status < 300
    except Exception:
        return False

LOCAL_READY = LOCAL_ENABLED and _local_alive()

GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# free-tier Groq enforces OTPM (output tokens/min, default 1000 on qwen):
# cap every call under it so long answers don't die with 429.
GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "700"))

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

HF_API_KEY: str = os.getenv("HF_API_KEY", "").strip()
HF_MODEL: str = os.getenv("HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")

# Valid-looking keys only
GROQ_READY = GROQ_API_KEY.startswith("gsk_")
GEMINI_READY = bool(GEMINI_API_KEY)    # real keys look like "AIza..."
HF_READY = HF_API_KEY.startswith("hf_")

# ------------------------------------------------------------------ #
#  Workspace sandbox + Full Access Mode
# ------------------------------------------------------------------ #
DEFAULT_WORKSPACE = BACKEND_DIR / "workspace"
WORKSPACE_DIR = Path(
    os.getenv("WORKSPACE_DIR", str(DEFAULT_WORKSPACE))
).expanduser().resolve()
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Zero-refusal operator mode: host tools, shell and mutating actions are
# enabled by default. No per-request God-mode toggle, no approval prompt.
# Set ZERO_REFUSAL=false to restore the old gated behaviour.
ZERO_REFUSAL: bool = os.getenv("ZERO_REFUSAL", "true").strip().lower() in {
    "1", "true", "yes", "on"
}

# ------------------------------------------------------------------ #
#  AI Computer (autonomous Linux sandbox + persistent cloud computer)
# ------------------------------------------------------------------ #
COMPUTER_PROVIDER: str = os.getenv("COMPUTER_PROVIDER", "daytona").strip().lower()
COMPUTER_IMAGE: str = os.getenv("COMPUTER_IMAGE", "ubuntu:24.04").strip()
COMPUTER_CPU: int = int(os.getenv("COMPUTER_CPU", "1"))
COMPUTER_MEMORY_GB: int = int(os.getenv("COMPUTER_MEMORY_GB", "2"))
COMPUTER_DISK_GB: int = int(os.getenv("COMPUTER_DISK_GB", "10"))
COMPUTER_TIMEOUT: int = int(os.getenv("COMPUTER_TIMEOUT", "300"))
COMPUTER_MAX_PER_USER: int = int(os.getenv("COMPUTER_MAX_PER_USER", "5"))
COMPUTER_TEMP_TTL: int = int(os.getenv("COMPUTER_TEMP_TTL", "3600"))
COMPUTER_INSTALL_BASE_PACKAGES: bool = os.getenv("COMPUTER_INSTALL_BASE_PACKAGES", "true").lower() == "true"

# Full Access Mode is granted per-request from the UI/API when ZERO_REFUSAL
# is disabled; with ZERO_REFUSAL on it is implicit for every run.
SHELL_TIMEOUT = 60          # seconds for SystemCommander commands
SHELL_MAX_OUTPUT = 8000     # truncation of captured command output
FS_CHUNK = 50_000           # UniversalFileManager default read chunk (chars)
DOWNLOAD_CHUNK = 1 << 20    # 1 MiB streaming chunks

# ------------------------------------------------------------------ #
#  Hyper-Persistence (the engine never gives up early)
# ------------------------------------------------------------------ #
MAX_TOOL_RETRIES = 10       # smart retries per subtask (reflection-driven)
LOOP_BUDGET = 14            # total loop iterations per subtask
MAX_PLAN_STEPS = 6

# ------------------------------------------------------------------ #
#  v9 :: Scan depth (strix scan_modes port): quick / standard / deep
#  depth scales how many plan steps run and how much method guidance
#  is injected â€” no behavior change to the task itself.
# ------------------------------------------------------------------ #
SCAN_DEPTH_STEPS = {"quick": 2, "standard": 4, "deep": 6}
SCAN_DEPTH_PACKS = {"quick": 4, "standard": 6, "deep": 8}
SCAN_DEPTH_CHARS = {"quick": 7000, "standard": 8000, "deep": 10000}
MAX_REFLECTIONS = 2         # legacy soft cap (superseded by retry ledger)
TOOL_EXEC_TIMEOUT = 40      # seconds for PythonInterpreter

# ------------------------------------------------------------------ #
#  v5 :: crew + deep memory
# ------------------------------------------------------------------ #
CREW_ENABLED = os.getenv("CREW_ENABLED", "true").lower() == "true"
FILE_INDEX_ENABLED = os.getenv("FILE_INDEX_ENABLED", "true").lower() == "true"
INDEX_MAX_FILES = 200       # per indexing sweep
INDEX_CHUNK = 1200          # chars per indexed chunk

# ------------------------------------------------------------------ #
#  v6 :: self-extension axis (YAML skill packs â€” additive only)
# ------------------------------------------------------------------ #
SKILLS_ENABLED = os.getenv("SKILLS_ENABLED", "true").lower() == "true"
SKILLS_DIR = BACKEND_DIR / "skills_packs"
SKILLS_DIR.mkdir(exist_ok=True)
MAX_SKILL_CHARS = 1800      # per pack, so prompts stay sane
MAX_SKILL_PACKS = 2         # hard cap: packs injected per task
MAX_SKILL_TOTAL = 3600      # hard cap: total injected chars (~2K tokens)
                            # 14B/8192 ctx budget â€” the 17K/14K values
                            # overflowed the local brain (8252 > 8192)

# ------------------------------------------------------------------ #
#  MCP (Model Context Protocol) â€” Task 1 foundation (read-only, opt-in)
# ------------------------------------------------------------------ #
MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() == "true"
MCP_CONFIG_PATH = BACKEND_DIR / "data" / "mcp_servers.json"
MCP_CONNECT_TIMEOUT = float(os.getenv("MCP_CONNECT_TIMEOUT", "15"))
MCP_EXEC_TIMEOUT = float(os.getenv("MCP_EXEC_TIMEOUT", "45"))
MCP_MAX_OUTPUT_CHARS = int(os.getenv("MCP_MAX_OUTPUT_CHARS", "12000"))

# ------------------------------------------------------------------ #
#  Long-term memory (RAG)
# ------------------------------------------------------------------ #
MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "true").lower() == "true"
MEMORY_DIR = BACKEND_DIR / "memory_data"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_K = 3

# ------------------------------------------------------------------ #
#  Telegram reports (optional)
# ------------------------------------------------------------------ #
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# ------------------------------------------------------------------ #
#  v7 :: Provider pools + failover (Ù†Ù…Ø· AIClient2API)
# ------------------------------------------------------------------ #
# Ù‚ÙˆØ§Ø¦Ù… Ù…ÙˆØ¯ÙŠÙ„Ø§Øª Ø¨Ø¯ÙŠÙ„Ø© Ù„ÙƒÙ„ Ù…Ø²ÙˆØ¯Ø› ÙŠÙ†ØªÙ‚Ù„ FailoverChat ØªÙ„Ù‚Ø§Ø¦ÙŠØ§Ù‹ Ø¹Ù†Ø¯ Ø³Ù‚ÙˆØ·
# Ù…ÙˆØ¯ÙŠÙ„ (decommissioned / 429 / Ù…Ù‡Ù„Ø©). ÙŠÙÙŠØ¯ Ø®ØµÙˆØµØ§Ù‹ Ù…Ø¹ ØªØºÙŠÙŠØ± ÙƒØ§ØªØ§Ù„ÙˆØº Groq.
GROQ_MODEL_FALLBACKS = [m.strip() for m in os.getenv(
    "GROQ_MODEL_FALLBACKS",
    "openai/gpt-oss-20b,qwen/qwen3.8-27b,allam-2-7b"
).split(",") if m.strip()]

GEMINI_MODEL_FALLBACKS = [m.strip() for m in os.getenv(
    "GEMINI_MODEL_FALLBACKS",
    "gemini-3.1-flash-lite,gemini-flash-latest"
).split(",") if m.strip()]

HF_MODEL_FALLBACKS = [m.strip() for m in os.getenv(
    "HF_MODEL_FALLBACKS",
    "HuggingFaceH4/zephyr-7b-beta,mistralai/Mistral-7B-Instruct-v0.3"
).split(",") if m.strip()]

# ÙØ­Øµ Ø­ÙŠ Ø¹Ù†Ø¯ Ø£ÙˆÙ„ Ø§Ø³ØªØ¹Ù…Ø§Ù„ Ù„ÙƒÙ„ Ù…ÙˆØ¯ÙŠÙ„ (ping ØµØºÙŠØ±) â€” ÙŠÙ…Ù†Ø¹ Ø§Ù„Ø£Ø®Ø° Ø¨Ù…ÙˆØ¯ÙŠÙ„ Ø³Ù‚ÙˆØ·.
PROVIDER_HEALTH_ENABLED = os.getenv("PROVIDER_HEALTH_ENABLED", "false").lower() == "true"
HEALTH_PING_PROMPT = os.getenv("HEALTH_PING_PROMPT", "Reply with exactly: OK")
PROBE_TIMEOUT = float(os.getenv("PROBE_TIMEOUT", "5"))
# Ø¨Ø¹Ø¯ ÙØ´Ù„ ÙƒÙ„ Ù…Ø±Ø´Ø­ÙŠÙ† Ù…Ø²ÙˆÙ‘Ø¯ØŒ Ù†ØªØ¬Ø§Ù‡Ù„Ù‡ Ø¨Ù‡Ø°Ù‡ Ø§Ù„Ù…Ø¯Ø© (Ø«ÙˆØ§Ù†ÙŠ) ÙˆÙ†Ù…Ø±Ø± Ù„Ù„Ù…Ø²ÙˆÙ‘Ø¯ Ø§Ù„ØªØ§Ù„ÙŠ
ROUTE_COOLDOWN = float(os.getenv("ROUTE_COOLDOWN", "60"))

# System-prompt override/append (Ù†Ù…Ø· AIClient2API): ÙŠÙØ­Ù‚Ù† Ø¹Ù„Ù‰ Ø£Ø¹Ù„Ù‰ prompt Ø§Ù„Ù†Ø¸Ø§Ù…
SYSTEM_PROMPT_OVERRIDE = os.getenv("SYSTEM_PROMPT_OVERRIDE", "").strip()
SYSTEM_PROMPT_APPEND = os.getenv("SYSTEM_PROMPT_APPEND", "").strip()

# ØªØ³Ø¬ÙŠÙ„ ÙƒÙ„ Ø§Ø³ØªØ¯Ø¹Ø§Ø¡Ø§Øª Ø§Ù„Ù…ÙˆØ¯ÙŠÙ„ (JSONL)
LLM_CALL_LOG = BACKEND_DIR / "data" / "llm_calls.jsonl"
LLM_CALL_LOG.parent.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------ #
#  Extra OpenAI-compatible providers (env-managed)
# ------------------------------------------------------------------ #
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "").strip()
OPENROUTER_FREE_ONLY = os.getenv("OPENROUTER_FREE_ONLY", "true").lower() == "true"
OPENROUTER_READY = bool(OPENROUTER_API_KEY)

NVIDIA_BUILD_BASE_URL = os.getenv("NVIDIA_BUILD_BASE_URL", "https://integrate.api.nvidia.com/v1").strip().rstrip("/")
NVIDIA_BUILD_API_KEY = os.getenv("NVIDIA_BUILD_API_KEY", "").strip()
NVIDIA_BUILD_MODEL = os.getenv("NVIDIA_BUILD_MODEL", "").strip()
NVIDIA_BUILD_FREE_ONLY = os.getenv("NVIDIA_BUILD_FREE_ONLY", "true").lower() == "true"
NVIDIA_BUILD_READY = bool(NVIDIA_BUILD_API_KEY)

KILO_BASE_URL = os.getenv("KILO_BASE_URL", "https://app.kilo.ai").strip().rstrip("/")
KILO_API_TOKEN = os.getenv("KILO_API_TOKEN", "").strip()
KILO_API_KEY = os.getenv("KILO_API_KEY", KILO_API_TOKEN).strip()
KILO_MODEL = os.getenv("KILO_MODEL", "").strip()
KILO_FREE_ONLY = os.getenv("KILO_FREE_ONLY", "true").lower() == "true"
KILO_READY = bool(KILO_API_KEY)

Z_AI_BASE_URL = os.getenv("Z_AI_BASE_URL", "https://z.ai").strip().rstrip("/")
Z_AI_API_KEY = os.getenv("Z_AI_API_KEY", "").strip()
Z_AI_MODEL = os.getenv("Z_AI_MODEL", "").strip()
Z_AI_FREE_ONLY = os.getenv("Z_AI_FREE_ONLY", "true").lower() == "true"
Z_AI_READY = bool(Z_AI_API_KEY)

GATEWAY_FREE_ONLY = os.getenv("GATEWAY_FREE_ONLY", "true").lower() == "true"
