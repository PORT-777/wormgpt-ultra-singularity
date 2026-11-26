"""

🔥😈 PORT 777 EVIL ☠️🔥👹 :: Multi-Model Routing System v7 â€” Pools + Live Failover.



Routing policy

--------------

  Fast chat / real-time reasoning   ->  Groq

  Deep research / long documents    ->  Gemini (giant context)

  Niche specialist tasks            ->  Hugging Face Inference API

  Fallback chain                    ->  Groq -> Gemini -> HF



Each provider is a POOL of model candidates (config.GROQ_MODEL +

GROQ_MODEL_FALLBACKS, ...). `FailoverChat` rotates candidates live:

model decommissioned / 429 / timeout -> next candidate in the pool,

validating with a tiny health ping on first use (PROVIDER_HEALTH_ENABLED).

ÙŠÙÙŠØ¯ Ø®ØµÙˆØµØ§Ù‹ Ù…Ø¹ ØªØºÙŠÙ‘Ø± ÙƒØ§ØªØ§Ù„ÙˆØº Groq Ø§Ù„Ù…ØªÙƒØ±Ø±.



Every provider is instantiated lazily and wrapped so the rest of the

engine only sees a uniform `.ainvoke(list_of_messages) -> AIMessage`

interface (LangChain's `BaseChatModel` contract).

"""

from __future__ import annotations



import asyncio

import copy

import json

import logging

import time

from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple



from fastapi import HTTPException

from langchain_core.messages import AIMessage, BaseMessage



import configs as config



log = logging.getLogger("model_router")

# in-memory per-provider cooldown (gateway integration): {provider_id:{model:cooldown_until}}

GATEWAY_COOLDOWN: Dict[str, Dict[str, float]] = {}

QUOTA_COOLDOWN_429 = 5 * 60.0

NETWORK_COOLDOWN = 60.0

PAID_ROUTE_NAMES = {"paid", "premium", "pro"}  # reserved; local pools are non-paid





def _is_quota_error(exc: BaseException) -> bool:

    t = str(exc or "").lower()

    return ("429" in t) or ("quota" in t) or ("rate limit" in t) or ("rate_limit" in t)





def _is_network_error(exc: BaseException) -> bool:

    if isinstance(exc, (ConnectionError, TimeoutError, asyncio.TimeoutError)):

        return True

    t = str(exc or "").lower()

    return any(s in t for s in (

        "timeout", "timed out", "connection", "connect", "network",

        "unavailable", "temporar", "dns", "refused", "reset",

        "502", "503", "504",

    ))





def cooldown_seconds_for(exc: BaseException | None) -> float:

    if exc is None:

        return 0.0

    if _is_quota_error(exc):

        return QUOTA_COOLDOWN_429

    if _is_network_error(exc):

        return NETWORK_COOLDOWN

    return 0.0





def mark_gateway_cooldown(provider_id: str, model: str, exc: BaseException | None = None,

                          seconds: float | None = None) -> float:

    """Set {provider_id:{model:cooldown_until}}; 429→5min, network→1min by default."""

    try:

        pid = str(provider_id or "?")

        mid = str(model or "?")

        secs = float(seconds) if seconds is not None else cooldown_seconds_for(exc)

        if secs <= 0:

            return 0.0

        until = time.time() + secs

        bucket = GATEWAY_COOLDOWN.setdefault(pid, {})

        bucket[mid] = max(float(bucket.get(mid, 0.0) or 0.0), until)

        return secs

    except Exception:

        return 0.0





def gateway_on_cooldown(provider_id: str, model: str, now: float | None = None) -> bool:

    try:

        n = time.time() if now is None else float(now)

        until = float(GATEWAY_COOLDOWN.get(str(provider_id or "?"), {}).get(str(model or "?"), 0.0) or 0.0)

        if until <= n:

            return False

        return True

    except Exception:

        return False





def clear_gateway_cooldown(provider_id: str, model: str) -> None:

    try:

        bucket = GATEWAY_COOLDOWN.get(str(provider_id or "?"))

        if bucket:

            bucket.pop(str(model or "?"), None)

    except Exception:

        pass



RouteName = Literal["groq", "gemini", "hf", "local", "auto", "none"]



# Keyword heuristics for automatic routing ------------------------------- #

LONG_TASK_HINTS = (

    "research", "long document", "long doc", "summarize the document",

    "analyze the file", "large file", "entire", "full text", "translate",

    "pdf", "history of", "comprehensive report", "deep dive",

)

NICHE_TASK_HINTS = (

    "huggingface", "hugging face", "niche model", "specialist",

    "uncensored", "image recognition", "classify", "classification",

    "vision", "embed", "sentiment",

)



_CALL_LOG = config.LLM_CALL_LOG





def _log_call(route: str, model: str, kind: str, error: str = "") -> None:

    """ØªØ³Ø¬ÙŠÙ„ ÙƒÙ„ Ø§Ø³ØªØ¯Ø¹Ø§Ø¡ Ù…ÙˆØ¯ÙŠÙ„ (JSONL) â€” Ù…Ø·Ø§Ø¨Ù‚Ø© Ù„Ø³ÙŠÙ†Ø§Ø±ÙŠÙˆ AIClient2API."""

    try:

        rec = {

            "ts": time.time(),

            "route": route,

            "model": model,

            "kind": kind,      # ping | ainvoke | astream | fail

            "error": error[:300],

        }

        with open(_CALL_LOG, "a", encoding="utf-8") as f:

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    except Exception:

        pass  # Ø§Ù„ØªØ³Ø¬ÙŠÙ„ Ù„Ø§ ÙŠØ¹Ø·Ù„ Ø§Ù„Ù…Ø³Ø§Ø± Ø£Ø¨Ø¯Ø§Ù‹





def _is_transient(exc: Exception) -> bool:

    """Ø§Ø®ØªÙŠØ§Ø±: Ù‡Ù„ Ø§Ù„Ø®Ø·Ø£ ÙŠØ³ØªØ­Ù‚ Ø§Ù„Ø§Ù†ØªÙ‚Ø§Ù„ Ù„Ù„Ù…ÙˆØ¯ÙŠÙ„ Ø§Ù„ØªØ§Ù„ÙŠ (Ø£Ùˆ Ø¥Ø¹Ø§Ø¯Ø© ÙˆØ§Ø­Ø¯Ø©)ØŸ"""

    text = str(exc).lower()

    signals = (

        "decommissioned", "not found", "unsupported", "429",

        "rate limit", "quota", "overloaded", "timeout", "timed out",

        "503", "502", "500", "model_decommissioned", "connectivity",

        "unavailable", "capacity",

        # gpt-oss Ø¹Ù„Ù‰ Groq Ø£Ø­ÙŠØ§Ù†Ø§Ù‹ ÙŠØ¨Ø¹Ø¯ tool-call native Ø¨Ø¯ÙˆÙ† Ø£Ø¯ÙˆØ§Øª Ù…Ø¹Ø±ÙØ©

        # â€” Ø¹Ø´ÙˆØ§Ø¦ÙŠ Ù„Ø§ Ù…Ù†Ø·Ù‚ÙŠØŒ ÙŠØ³ØªØ­Ù‚ Ø¥Ø¹Ø§Ø¯Ø©/Ø§Ù†ØªÙ‚Ø§Ù„:

        "tool choice is none", "tool_choice", "called a tool",

        "apierror", "connection error", "stream error", "internal server",

    )

    return any(s in text for s in signals)





class FailoverChat:

    """Ù¾Û†Ù„ Ù…ÙˆØ¯ÙŠÙ„Ø§Øª Ù„Ù…Ø²ÙˆØ¯ ÙˆØ§Ø­Ø¯ Ù…Ø¹ Ù†Ù‚Ù„ Ø­ÙŠ Ø¹Ù†Ø¯ Ø§Ù„Ø³Ù‚ÙˆØ·.



    ÙŠÙ„Ù Ù‚Ø§Ø¦Ù…Ø© factory-callables (ÙƒÙ„ ÙˆØ§Ø­Ø¯ ÙŠØ¹ÙŠØ¯ Ù†Ù…ÙˆØ°Ù„ Ù„Ø§Ù†Øº-ØªØ´ÙŠÙ† Ù…Ù„ØªØ²Ù…Ù‹Ø§

    Ø¨Ù€ contract Ø§Ù„Ù…Ø­Ø±Ùƒ): ainvoke / astream / bind.

    """



    def __init__(self, route: str,

                 factories: List[Tuple[str, Callable[[], Any]]]):

        self.route = route

        self._factories = factories           # [(model_name, factory), ...]

        self._instances: List[Optional[Any]] = [None] * len(factories)

        self._healthy = [False] * len(factories)

        self._down_until = 0.0                # cooldown Ø¹Ù†Ø¯ Ø³Ù‚ÙˆØ· ÙƒÙ„ Ø§Ù„Ù…Ø±Ø´Ø­ÙŠÙ†

        self.active_model: Optional[str] = None



    @property

    def down(self) -> bool:

        return time.time() < self._down_until



    # ----------------- instance management ------------------- #

    def _instance(self, i: int):

        if self._instances[i] is None:

            self._instances[i] = self._factories[i][1]()

        return self._instances[i]



    # ----------------- liveness probe ------------------------ #

    async def _probe(self, model) -> bool:

        try:

            await asyncio.wait_for(

                model.ainvoke([AIMessage(content=config.HEALTH_PING_PROMPT)]),

                timeout=config.PROBE_TIMEOUT,

            )

            return True

        except Exception:

            log.warning("[probe %s] failed", self.route)

            return False



    # ----------------- public LangChain contract ------------- #

    def bind(self, **_: Any) -> "FailoverChat":

        return self


    def bind_tools(self, tools: List[Dict[str, Any]],
                   **kwargs: Any) -> "FailoverChat":
        """Bind function definitions on every candidate, keeping failover.

        A candidate whose provider lacks tool support is left unbound (None
        forces a fresh instance), so the engine's text-ReAct path still works.
        """
        cloned = copy.copy(self)
        bound_instances = []
        for i, (_name, _factory) in enumerate(self._factories):
            try:
                model = self._instance(i)
                binder = getattr(model, "bind_tools", None)
                bound_instances.append(
                    binder(tools, **kwargs) if callable(binder) else model
                )
            except Exception as exc:
                log.warning("[bind_tools %s] candidate %d: %s",
                            self.route, i, exc)
                bound_instances.append(None)
        cloned._instances = bound_instances
        return cloned


    async def ainvoke(self, messages: List[BaseMessage], **kw: Any) -> AIMessage:

        if self.down:

            raise RuntimeError(f"{self.route} pool cooling down "

                               f"({self._down_until - time.time():.0f}s left)")

        last: Optional[Exception] = None

        for i, (name, _) in enumerate(self._factories):

            # Ø¥Ø¹Ø§Ø¯ØªØ§Ù† Ù„ÙƒÙ„ Ù…Ø±Ø´Ø­ (gpt-osc quirk Ø¹Ø´ÙˆØ§Ø¦ÙŠ ÙŠØ´ÙÙ‰ Ø¨Ù…Ø­Ø§ÙˆÙ„Ø© Ø«Ø§Ù†ÙŠØ©)

            for attempt in (1, 2):

                try:

                    model = self._instance(i)

                    if config.PROVIDER_HEALTH_ENABLED and not self._healthy[i]:

                        ok = await self._probe(model)

                        self._healthy[i] = ok

                        _log_call(self.route, name, "ping", "" if ok else "probe failed")

                        if not ok:

                            self._instances[i] = None

                            break

                        self.active_model = name

                        self._down_until = 0.0

                    _log_call(self.route, name, "ainvoke", f"attempt={attempt}")

                    result = await model.ainvoke(messages, **kw)

                    self._down_until = 0.0

                    return result

                except Exception as exc:

                    last = exc

                    self._healthy[i] = False

                    self._instances[i] = None

                    _log_call(self.route, name, "fail", f"attempt={attempt} {exc}")

                    if not _is_transient(exc):

                        # Ø®Ø·Ø£ Ù…Ù†Ø·Ù‚ÙŠ (Ø³Ø¤Ø§Ù„ Ø®Ø§Ø·Ø¦) Ù„Ø§ ÙŠØ³ØªØ­Ù‚ ØªØ¬Ø±Ø¨Ø© Ø¨Ø§Ù‚ÙŠ Ø§Ù„Ù…ÙˆØ¯ÙŠÙ„Ø§Øª

                        raise

                    log.warning("[failover %s] %s attempt %d failed",

                                self.route, name, attempt)

        self._down_until = time.time() + config.ROUTE_COOLDOWN

        raise RuntimeError(f"All {self.route} candidates failed: {last}")



    async def astream(self, messages: List[BaseMessage], **_: Any):

        """ØªÙ†Ù‚Ù„ FailoverChat Ø¹Ù„Ù‰ astream: ÙŠÙ†ØªÙ‚Ù„ Ø¹Ù†Ø¯ Ø³Ù‚ÙˆØ· Ù…ÙˆØ¯ÙŠÙ„.



        Ø³Ù„ÙˆÙƒ Ø®Ø§Øµ: Ø¥Ø°Ø§ ÙØ´Ù„ Ø§Ù„ØªÙŠØ§Ø± Ø¨Ø¹Ø¯ Ø¨Ø¯Ø§ÙŠØ© Ø¥Ù†ØªØ§Ø¬ chunks ÙØ¹Ù„ÙŠÙ‘Ø©ØŒ Ù†ÙØ¹ÙŠØ¯

        Ø§Ù„Ø±Ù…ÙŠ (Ù„Ø§ Ù†Ø¶Ø§Ø¹Ù Ø§Ù„Ù†Øµ). Ø¥Ø°Ø§ ÙØ´Ù„ Ù‚Ø¨Ù„ Ø£ÙˆÙ„ chunkØŒ Ù†Ù†ØªÙ‚Ù„ Ù„Ù„Ù…Ø±Ø´Ø­ Ø§Ù„ØªØ§Ù„ÙŠ.

        """

        if self.down:

            raise RuntimeError(f"{self.route} pool cooling down "

                               f"({self._down_until - time.time():.0f}s left)")

        last: Optional[Exception] = None

        for i, (name, _) in enumerate(self._factories):

            for attempt in (1, 2):

                emitted = False

                try:

                    model = self._instance(i)

                    if config.PROVIDER_HEALTH_ENABLED and not self._healthy[i]:

                        ok = await self._probe(model)

                        self._healthy[i] = ok

                        _log_call(self.route, name, "ping", "" if ok else "probe failed")

                        if not ok:

                            self._instances[i] = None

                            break

                        self.active_model = name

                        self._down_until = 0.0

                    _log_call(self.route, name, "astream", f"attempt={attempt}")

                    async for chunk in model.astream(messages, **{}):

                        emitted = True

                        yield chunk

                    self._down_until = 0.0

                    return

                except Exception as exc:

                    last = exc

                    self._healthy[i] = False

                    self._instances[i] = None

                    _log_call(self.route, name, "fail", f"attempt={attempt} {exc}")

                    if emitted:

                        raise          # Ø§Ù„ØªÙŠØ§Ø± Ø¨Ø¯Ø£ â€” Ù„Ø§ Ù…Ø¶Ø§Ø¹ÙØ©

                    if not _is_transient(exc):

                        raise

                    log.warning("[failover %s] %s attempt %d failed (stream)",

                                self.route, name, attempt)

        self._down_until = time.time() + config.ROUTE_COOLDOWN

        raise RuntimeError(f"All {self.route} candidates failed (stream): {last}")





class ModelRouter:

    """Resolves a task (or an explicit override) to a chat model."""



    ROUTE_ALIASES = {

        "auto": "auto",

        "local": "local",

        "default": "local",

        "groq": "groq",

        "gemini": "gemini",

        "hf": "hf",

        "huggingface": "hf",

        "kilo": "kilo",

        "none": "none",

    }

    KNOWN_TEMPLATE_PREFIXES = {"auto", "template", "templates", "squad"}



    def __init__(self) -> None:

        self._pools: dict = {}

        self.last_decision: dict = {}



    # ------------------- factories Ù„ÙƒÙ„ Ù…Ø²ÙˆØ¯ ------------------- #

    def _groq_factories(self):

        rows = []

        if config.GROQ_READY:

            from langchain_groq import ChatGroq



            pool = [config.GROQ_MODEL, *config.GROQ_MODEL_FALLBACKS]

            seen = set()

            for m in pool:

                mid = str(m).strip()

                if not mid or mid in seen:

                    continue

                seen.add(mid)

                rows.append((mid, lambda mid=mid: ChatGroq(

                    api_key=config.GROQ_API_KEY,

                    model=mid,

                    temperature=0.2,

                    streaming=True,

                    # stay under free-tier OTPM (default 1000) so long

                    # answers are not killed by 429 "expected output"

                    max_tokens=int(getattr(config, "GROQ_MAX_TOKENS", 950)),

                )))

        return rows



    def _gemini_factories(self):

        rows = []

        if config.GEMINI_READY:

            from langchain_google_genai import ChatGoogleGenerativeAI



            pool = [config.GEMINI_MODEL, *config.GEMINI_MODEL_FALLBACKS]

            seen = set()

            for m in pool:

                mid = str(m).strip()

                if not mid or mid in seen:

                    continue

                seen.add(mid)

                rows.append((mid, lambda mid=mid: ChatGoogleGenerativeAI(

                    model=mid,

                    google_api_key=config.GEMINI_API_KEY,

                    temperature=0.2,

                    convert_system_message_to_human=True,

                )))

        return rows



    def _hf_factories(self):

        rows = []

        if config.HF_READY:

            pool = [config.HF_MODEL, *config.HF_MODEL_FALLBACKS]

            seen = set()

            for m in pool:

                mid = str(m).strip()

                if not mid or mid in seen:

                    continue

                seen.add(mid)

                rows.append((mid, lambda mid=mid: HFChefModel(

                    config.HF_API_KEY, mid)))

        return rows



    def _kilo_factories(self):

        """Kilo AI free models (OpenAI-compatible)."""

        if not getattr(config, "KILO_READY", False):

            return []

        from langchain_openai import ChatOpenAI

        rows = []

        models = [config.KILO_MODEL] if config.KILO_MODEL else []

        seen = set()

        for m in models:

            mid = str(m).strip()

            if not mid or mid in seen:

                continue

            seen.add(mid)

            rows.append((mid, lambda mid=mid: ChatOpenAI(

                api_key=config.KILO_API_KEY,

                base_url=config.KILO_BASE_URL,

                model=mid,

                temperature=0.2,

                streaming=True,

                max_tokens=int(getattr(config, "GROQ_MAX_TOKENS", 700)),

            )))

        return rows



    def _local_factories(self):

        """Local llama.cpp/OpenAI-compatible server (uncensored, no quotas)."""

        if not getattr(config, "LOCAL_READY", False):

            return []

        from langchain_openai import ChatOpenAI



        rows = [(config.LOCAL_MODEL_NAME, lambda: ChatOpenAI(

            api_key="not-needed",

            base_url=config.LOCAL_BASE_URL,

            model=config.LOCAL_MODEL_NAME,

            temperature=0.2,

            streaming=True,

            max_tokens=None,

        ))]

        return rows



    # ---------------- lazy pool construction ------------------ #

    def _make_pool(self, name: str) -> Optional["FailoverChat"]:

        factories = {

            "groq": self._groq_factories,

            "gemini": self._gemini_factories,

            "hf": self._hf_factories,

            "kilo": self._kilo_factories,

            "local": self._local_factories,

        }.get(name)

        if not factories:

            return None

        rows = factories()

        if not rows:

            return None

        pool = FailoverChat(name, rows)

        self._pools[name] = pool

        return pool



    def _active_model_name(self, route: str, brain: Any) -> str:

        if brain is None:

            return "none"

        return str(getattr(brain, "active_model", None) or getattr(brain, "model_name", None) or route or "default")



    def _decision(self, provider: str, model: str, reason: str, ms: float = 0.0,

                  activation_off: bool = False) -> dict:

        info = {

            "provider": str(provider or "local"),

            "model": str(model or "default"),

            "reason": str(reason or "resolved"),

            "ms": int(max(0.0, float(ms or 0.0))),

            "activation_off": bool(activation_off),

            "header": f"{provider}/{model} ({reason})",

        }

        self.last_decision = info

        log.info("X-Gateway-Decision provider=%s model=%s reason=%s ms=%s",

                 info["provider"], info["model"], info["reason"], info["ms"])

        return info



    def _all_known_model_ids(self) -> Dict[str, str]:

        """model_id(lower) -> provider route that owns it (configured pools)."""

        out: Dict[str, str] = {}

        for name in ("local", "groq", "kilo", "gemini", "hf"):

            try:

                rows = {

                    "local": self._local_factories,

                    "groq": self._groq_factories,

                    "gemini": self._gemini_factories,

                    "hf": self._hf_factories,

                }[name]()

            except Exception:

                rows = []

            for mid, _ in (rows or []):

                k = str(mid).strip().lower()

                if k and k not in out:

                    out[k] = name

        return out



    def get(self, name: RouteName):

        """Return a chat-model pool, or None if unavailable/cooling down."""

        if name not in ("groq", "gemini", "hf", "kilo", "local"):

            return None

        pool = self._pools.get(name) or self._make_pool(name)

        if pool is not None and pool.down:

            log.info("[router] %s pool cooling down — skipping", name)

            return None

        return pool



    # ----------------------- routing logic ------------------- #

    def classify(self, task: str, reasoning_level: int | None = None) -> RouteName:
        if reasoning_level is not None:
            mapped = {1: "groq", 2: "groq", 3: "gemini", 4: "gemini", 5: "hf"}.get(int(reasoning_level))
            if mapped:
                return mapped

        text = task.lower()

        if getattr(config, "LOCAL_READY", False):

            return "local"

        if len(task) > 6000 or any(h in text for h in LONG_TASK_HINTS):

            return "gemini"

        if any(h in text for h in NICHE_TASK_HINTS):

            return "hf"

        return "groq"



    def _local_default(self) -> tuple[str, str, Any | None]:

        model = str(getattr(config, "LOCAL_MODEL_NAME", "default") or "default")

        brain = None

        try:

            brain = self.get("local")

            if brain is not None:

                model = self._active_model_name("local", brain)

        except Exception:

            brain = None

        return "local", model, brain



    def get_brain(self, *args, **kwargs):
        return self.resolve(*args, **kwargs)

    def resolve(self, override: RouteName = "auto", *args, task: str = "", activation: bool = True,

                free_only: bool = True, **kwargs) -> Tuple[RouteName, Any]:

        """Resolve route -> (name, model). Fail-closed on activation=OFF/unknown/paid-with-freeOnly."""

        # compatibility: resolve('auto', 'task text') legacy callers

        if args and not task:

            try:

                task = str(args[0] or "")

            except Exception:

                pass

        if "task" in kwargs and not task:

            task = str(kwargs.get("task") or "")

        if "activation" in kwargs:

            activation = bool(kwargs.get("activation"))

        if "free_only" in kwargs:

            free_only = bool(kwargs.get("free_only"))

        t0 = time.perf_counter()

        req = str(override or "auto").strip()



        if not activation:

            route, model_name, brain = self._local_default()

            self._decision(route, model_name, "activation-off", (time.perf_counter() - t0) * 1000, activation_off=True)

            return route, brain



        low = req.lower()

        # "auto:free" is accepted as an alias of the "auto/free" template.

        if low.endswith(":free") and low[:-5] in self.KNOWN_TEMPLATE_PREFIXES:

            low = low[:-5] + "/free"

        has_free_tag = ":free" in low or low.endswith("/free")

        free_only = bool(free_only or has_free_tag)



        # --- AUTO FREE (UNIFIED): سلسلة واحدة تضم جميع الموديلات المجانية من كل الموفرين ---

        # إذا اختار المستخدم "auto/free" (أو أي قالب ينتهي بـ /free)، ننشئ قائمةFailoverChat

        # تضم كل الموديلات المجانية من Groq, Kilo, Gemini, HF (وأي مزود مجاني مضاف مستقبلاً).

        # إذا رفض موديل أو نفذ حد التوكنات (TPM)، ينتقل تلقائياً للموديل التالي من أي مزود.

        if has_free_tag:

            return self._resolve_free_auto(task, t0)



        # auto/template forms: auto, auto/..., template/..., accepts :free variants (auto/coding:free, auto/fast:free)

        if low in ("", "auto") or any(low.startswith(p + "/") for p in self.KNOWN_TEMPLATE_PREFIXES):

            picked = self.classify(task or "")

            fallback_order: List[RouteName] = ["local", "groq", "kilo", "gemini", "hf"]

            if free_only:

                fallback_order = [r for r in fallback_order if r not in PAID_ROUTE_NAMES]

            order = [picked] + [r for r in fallback_order if r != picked]

            for route in order:

                if free_only and route in PAID_ROUTE_NAMES:

                    continue

                brain = self.get(route)

                if brain is not None:

                    reason = ("auto-template:free" if has_free_tag else ("auto-template" if "/" in low else "auto"))

                    self._decision(route, self._active_model_name(route, brain), reason, (time.perf_counter() - t0) * 1000)

                    return route, brain

            raise HTTPException(status_code=503, detail="No eligible free providers available (fail-closed; paid fallback disabled).")



        alias = self.ROUTE_ALIASES.get(low)

        if alias in ("groq", "gemini", "hf", "kilo", "local"):

            if free_only and alias in PAID_ROUTE_NAMES:

                raise HTTPException(status_code=403, detail="freeOnly=true blocks paid providers.")

            brain = self.get(alias)  # type: ignore[arg-type]

            if brain is not None:

                self._decision(alias, self._active_model_name(alias, brain), "explicit-route", (time.perf_counter() - t0) * 1000)

                return alias, brain

            # explicit route unavailable -> controlled fallback, never paid when freeOnly

            return self.resolve("auto", task=task, activation=activation, free_only=free_only)



        # explicit model id: resolve to owning provider; unknown -> 400 (never silent paid fallback)

        owner = self._all_known_model_ids().get(low)

        if owner:

            if free_only and owner in PAID_ROUTE_NAMES:

                raise HTTPException(status_code=403, detail="freeOnly=true blocks paid providers.")

            brain = self.get(owner)  # type: ignore[arg-type]

            if brain is not None:

                self._decision(owner, self._active_model_name(owner, brain), "explicit-model", (time.perf_counter() - t0) * 1000)

                return owner, brain

            raise HTTPException(status_code=503, detail=f"Owning provider for model '{req}' is unavailable (no paid fallback).")



        raise HTTPException(status_code=400, detail=f"Unknown model_route/model id '{req}' (no silent paid fallback).")



    # --- AUTO FREE (UNIFIED): جمع كل الموديلات المجانية من كل الموفرين في سلسلة واحدة ---

    def _resolve_free_auto(self, task: str, t0: float) -> Tuple[RouteName, Any]:

        """تُرجع FailoverChat يضم كل الموديلات المجانية من Groq, Kilo, Gemini, HF (وغيرها).

        إذا تعطل موديل أو نفذ حد التوكنات، ينتقل تلقائياً للموديل التالي من أي مزود."""

        rows: List[tuple[str, Any]] = []

        seen_models: set[str] = set()



        def _add_groq(models: List[str]) -> None:

            if not config.GROQ_READY:

                return

            from langchain_groq import ChatGroq

            for m in models:

                mid = str(m).strip()

                if not mid or mid in seen_models:

                    continue

                seen_models.add(mid)

                rows.append((mid, lambda mid=mid: ChatGroq(

                    api_key=config.GROQ_API_KEY,

                    model=mid,

                    temperature=0.2,

                    streaming=True,

                    max_tokens=int(getattr(config, "GROQ_MAX_TOKENS", 700)),

                )))



        def _add_kilo(models: List[str]) -> None:

            if not getattr(config, "KILO_READY", False):

                return

            from langchain_openai import ChatOpenAI

            for m in models:

                mid = str(m).strip()

                if not mid or mid in seen_models:

                    continue

                seen_models.add(mid)

                rows.append((mid, lambda mid=mid: ChatOpenAI(

                    api_key=config.KILO_API_KEY,

                    base_url=config.KILO_BASE_URL,

                    model=mid,

                    temperature=0.2,

                    streaming=True,

                    max_tokens=int(getattr(config, "GROQ_MAX_TOKENS", 700)),

                )))



        def _add_gemini(models: List[str]) -> None:

            if not config.GEMINI_READY:

                return

            from langchain_google_genai import ChatGoogleGenerativeAI

            for m in models:

                mid = str(m).strip()

                if not mid or mid in seen_models:

                    continue

                seen_models.add(mid)

                rows.append((mid, lambda mid=mid: ChatGoogleGenerativeAI(

                    model=mid,

                    google_api_key=config.GEMINI_API_KEY,

                    temperature=0.2,

                    convert_system_message_to_human=True,

                )))



        def _add_hf(models: List[str]) -> None:

            if not config.HF_READY:

                return

            for m in models:

                mid = str(m).strip()

                if not mid or mid in seen_models:

                    continue

                seen_models.add(mid)

                rows.append((mid, lambda mid=mid: HFChefModel(

                    config.HF_API_KEY, mid

                )))



        # جمع كل الموديلات المجانية من كل الموفرين

        _add_groq([config.GROQ_MODEL, *config.GROQ_MODEL_FALLBACKS])

        _add_kilo([config.KILO_MODEL] if config.KILO_MODEL else [])

        _add_gemini([config.GEMINI_MODEL, *config.GEMINI_MODEL_FALLBACKS])

        _add_hf([config.HF_MODEL, *config.HF_MODEL_FALLBACKS])



        if not rows:

            raise HTTPException(status_code=503, detail="No free providers configured for Auto Free.")



        # بناء FailoverChat واحد يضم كل الموديلات المجانية من كل الموفرين

        pool = FailoverChat("auto-free", rows)

        self._pools["auto-free"] = pool

        # تشغيل أول موديل لتحديد النشط

        try:

            brain = pool._instance(0)

        except Exception:

            brain = None

        active = self._active_model_name("auto-free", brain) if brain else "auto-free"

        self._decision("auto-free", active, "auto-free:unified", (time.perf_counter() - t0) * 1000)

        return "auto-free", pool



    def manager(self):

        """Manager role: local first, then working providers, Kilo last.

        Kilo's base URL returned HTTP 404 with an HTML body on this build,
        which made every plan/reflection wait through two dead retries.
        """

        for route in ("local", "groq", "gemini", "hf", "kilo"):

            model = self.get(route)

            if model is not None:

                return route, model

        return "none", None



    def status(self) -> dict:

        """Provider availability snapshot for /health + /api/models."""

        out = {}

        for name in ("local", "groq", "kilo", "gemini", "hf"):

            pool = self.get(name)

            out[name] = {

                "available": pool is not None,

                "models": [n for n, _ in pool._factories] if pool else [],

                "active": pool.active_model if pool else None,

                "healthy": any(pool._healthy) if pool else False,

                "cooling_down": pool.down if pool else False,

            }

        return out





# ===================================================================== #

#  Hugging Face adapter â€” gives InferenceClient the LangChain contract  #

# ===================================================================== #

class HFChefModel:

    """Minimal async chat-model shim around `huggingface_hub.InferenceClient`."""



    def __init__(self, api_key: str, model: str):

        from huggingface_hub import InferenceClient  # lazy import



        self._client = InferenceClient(api_key=api_key, model=model)

        self.model_name = model



    def bind(self, **_: Any) -> "HFChefModel":

        return self



    async def ainvoke(self, messages: List[BaseMessage], **_: Any) -> AIMessage:

        prompt = "\n".join(f"{m.type.upper()}: {m.content}" for m in messages)

        reply = await asyncio.to_thread(

            self._client.text_generation,

            prompt,

            max_new_tokens=1024,

            return_full_text=False,

        )

        return AIMessage(content=str(reply).strip())



    def astream(self, messages: List[BaseMessage], **_: Any):

        from types import SimpleNamespace



        async def _gen():

            msg = await self.ainvoke(messages)

            yield SimpleNamespace(content=msg.content)



        return _gen()





# Shared singleton used by the agent engine + API layer

ROUTER = ModelRouter()



