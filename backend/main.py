"""Unified FastAPI entrypoint for 🔥😈 PORT 777 EVIL ☠️🔥👹 / WormGPT_Ultra_Singularity.

Run from the project root:
    .\\backend\\.venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 7777
"""
from __future__ import annotations

import copy
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _BACKEND_DIR.parent
# Append, never prepend: api/main.py does `from main import SingularityOrchestrator`
# and must resolve to the project-root main.py, not back into this entrypoint.
for _p in (str(_PROJECT_DIR), str(_BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.append(_p)

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND_DIR / ".env", override=False)
except Exception:  # dotenv is optional; env vars can be supplied by the shell
    pass

from backend.api.chat import router as chat_router  # noqa: E402
from backend.saas.api import router as saas_router  # noqa: E402
from backend.api.computer import router as computer_router  # noqa: E402
from backend.api.plugins import router as plugins_router  # noqa: E402
from backend.connect import router as connect_router  # noqa: E402
from backend.api.intelligence import router as intelligence_router  # noqa: E402
from backend.api.system import router as system_router  # noqa: E402
from backend.api.vendor import router as vendor_router  # noqa: E402
from backend.api.workspace import router as workspace_router  # noqa: E402
from backend.plugins.deps import get_store  # noqa: E402
from plugins_system.registry import registry_instance  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("App")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        import platform_secrets

        loaded = platform_secrets.load_into_env()
        if loaded:
            logger.info("loaded %d encrypted OAuth credentials", loaded)
    except Exception as exc:
        logger.warning("encrypted secret store unavailable: %s", exc)
    try:
        import database
        import storage_backends

        database.ensure_schema()
        storage_backends.ensure_buckets()
        logger.info("persistence backend: %s / storage: %s",
                    database.backend_name(), storage_backends.backend().name)
    except Exception as exc:
        logger.warning("persistence init failed: %s", exc)
    try:
        from saas import db as saas_db
        from saas import plans as saas_plans

        saas_db.init()
        saas_plans.seed()
    except Exception as exc:
        logger.warning("SaaS subsystem init failed: %s", exc)
    try:
        from computer import store as computer_store
        from computer.manager import get_manager

        computer_store.init_tables()
        removed = get_manager().sweep_temporary()
        if removed:
            logger.info("cleaned %d expired temporary computers", removed)
    except Exception as exc:
        logger.warning("AI Computer subsystem init failed: %s", exc)
    logger.info("booting plugin subsystem")
    await registry_instance.discover_plugins()
    reports = await registry_instance.validate_all_plugins()
    invalid = [pid for pid, rep in reports.items() if not rep["valid"]]
    if invalid:
        logger.warning("plugins failed validation: %s", ", ".join(invalid))
    logger.info("registry ready — %d plugins loaded", len(registry_instance._plugins))
    yield
    logger.info("shutting down")
    try:
        import database

        database.release()
    except Exception:
        pass
    store = get_store()
    logger.info("audit entries written: %d", store.snapshot()["usage_log_size"])


app = FastAPI(
    title="🔥😈 PORT 777 EVIL ☠️🔥👹 — Singularity Edition",
    description="Agent core with dynamic plugin tooling, integrations and MCP.",
    version="6.1.0",
    lifespan=lifespan,
)

import os as _os

_default_origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:7777", "http://127.0.0.1:7777",
]
_configured_origins = [
    origin.strip() for origin in _os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_origins or _default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router mounting ----------------------------------------------------
# FastAPI 0.162 / Starlette 1.10 in this venv registers an empty path through
# include_router(). Mount APIRoutes explicitly instead.
def mount_router(target: FastAPI, router, prefix: str = "") -> None:
    from starlette.routing import compile_path

    added = 0
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        clone = copy.copy(route)
        path = prefix + route.path
        regex, path_format, convertors = compile_path(path)
        clone.path = path
        clone.path_regex = regex
        clone.path_format = path_format
        clone.param_convertors = convertors
        target.router.routes.append(clone)
        added += 1
    logger.info("mounted %d routes from %s%s", added, getattr(router, "prefix", "router"), prefix)


# --- API routers -------------------------------------------------------
mount_router(app, saas_router)  # /api/saas/*
mount_router(app, computer_router)  # /api/computer/*
mount_router(app, intelligence_router)  # /api/intelligence/*
mount_router(app, system_router)  # /api/status, /api/history, /api/runtime, ...
mount_router(app, connect_router)  # /api/connect/* one-click linking
mount_router(app, vendor_router)   # /api/vendor/* vendored reference repos
# Mount the static paths before plugins_router: its /plugins/{plugin_id}
# catch-all would otherwise swallow /api/plugins/catalog and /execute.
try:
    from plugins_api import router as legacy_plugins_router  # catalog/execute/audit

    mount_router(app, legacy_plugins_router)
except Exception as exc:  # pragma: no cover
    logger.warning("legacy plugin routes not mounted: %s", exc)
mount_router(app, plugins_router, "/api")

mount_router(app, chat_router, "/api")
mount_router(app, workspace_router)
try:
    from integrations.api import router as integrations_router

    mount_router(app, integrations_router)
except Exception as exc:  # pragma: no cover
    logger.warning("integrations API not mounted: %s", exc)

try:
    from security_api import router as security_router

    mount_router(app, security_router)
except Exception as exc:  # pragma: no cover
    logger.warning("security API not mounted: %s", exc)

# --- MCP control plane --------------------------------------------------
from fastapi import APIRouter, Body  # noqa: E402

import mcp_manager  # noqa: E402

mcp_router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@mcp_router.get("")
async def mcp_root():
    data = mcp_manager.status()
    servers = mcp_manager.list_servers()
    data["server_count"] = len(servers)
    data["servers"] = servers
    return data


@mcp_router.get("/status")
async def mcp_status():
    return mcp_manager.status()


@mcp_router.get("/servers")
async def mcp_servers():
    return {"servers": mcp_manager.list_servers()}


@mcp_router.post("/servers")
async def mcp_upsert(payload: dict = Body(...)):
    name = payload.pop("name", None) or payload.pop("id", None)
    if not name:
        return JSONResponse(status_code=400, content={"error": "name is required"})
    return mcp_manager.upsert_server(str(name), payload)


@mcp_router.delete("/servers/{name}")
async def mcp_remove(name: str):
    return mcp_manager.remove_server(name)


@mcp_router.post("/test/{name}")
async def mcp_test(name: str):
    return await mcp_manager.test_server(name)


@mcp_router.post("/call/{name}/{tool}")
async def mcp_call(name: str, tool: str, arguments: dict = Body(default_factory=dict)):
    return await mcp_manager.call_tool(name, tool, arguments=arguments)


# Advanced.jsx uses the original flat MCP contract; keep it working.
@mcp_router.post("")
async def mcp_legacy_save(payload: dict = Body(...)):
    name = payload.get("name")
    spec = payload.get("spec")
    if not name or not isinstance(spec, dict):
        return JSONResponse(status_code=400, content={"error": "name and spec are required"})
    return mcp_manager.upsert_server(str(name), spec)


@mcp_router.delete("/{name}")
async def mcp_legacy_remove(name: str):
    return mcp_manager.remove_server(name)


@mcp_router.post("/{name}/test")
async def mcp_legacy_test(name: str):
    return await mcp_manager.test_server(name)


mount_router(app, mcp_router)

# --- Standalone app route adoption -------------------------------------
# gateway.py and api/main.py are standalone FastAPI apps from an earlier layout.
# Adopt their API routes into this app so the frontend's /api/* calls resolve.
for module_name in ("gateway", "api.main"):
    try:
        module = __import__(module_name, fromlist=["app"])
        source_app = getattr(module, "app")
    except Exception as exc:
        logger.warning("could not adopt routes from %s: %s", module_name, exc)
        continue
    existing = {
        (getattr(r, "path", None), frozenset(getattr(r, "methods", None) or ()))
        for r in app.routes
    }
    adopted = 0
    for route in source_app.routes:
        if not isinstance(route, APIRoute):
            continue
        key = (route.path, frozenset(getattr(route, "methods", None) or ()))
        if key in existing or not route.path.startswith(("/api", "/v1", "/upload")):
            continue
        app.router.routes.append(route)
        existing.add(key)
        adopted += 1
    logger.info("adopted %d routes from %s", adopted, module_name)


@app.get("/api/health")
async def health():
    import database
    import storage_backends

    db_status = database.health()
    return {
        "status": "healthy" if db_status["ok"] else "degraded",
        "plugins_loaded": len(registry_instance._plugins),
        "database": db_status,
        "storage": storage_backends.storage_status(),
    }


@app.get("/health")
async def render_health():
    """Render health check: 200 only when the external database is reachable."""
    import database
    from fastapi.responses import JSONResponse

    status = database.health()
    return JSONResponse(
        status_code=200 if status["ok"] else 503,
        content={"status": "ok" if status["ok"] else "unavailable", "database": status},
    )


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc), "path": request.url.path},
    )


# --- Frontend (last) ----------------------------------------------------
for candidate in (_PROJECT_DIR / "frontend" / "dist", _PROJECT_DIR / "frontend"):
    if candidate.is_dir() and (candidate / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(candidate), html=True), name="frontend")
        logger.info("serving frontend from %s", candidate)
        break


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=7777, reload=False)
