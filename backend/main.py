"""
Cybersecurity AI Agent — application entrypoint.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.chat import router as chat_router
from backend.api.plugins import router as plugins_router
from backend.plugins.deps import get_store
from backend.plugins.registry import registry_instance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("App")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("booting plugin subsystem")
    await registry_instance.discover_plugins()
    logger.info("registry ready — %d plugins loaded", len(registry_instance._plugins))

    reports = await registry_instance.validate_all_plugins()
    invalid = [pid for pid, rep in reports.items() if not rep["valid"]]
    if invalid:
        logger.warning("plugins failed validation: %s", ", ".join(invalid))

    yield

    logger.info("shutting down")
    store = get_store()
    logger.info("audit entries written: %d", store.snapshot()["usage_log_size"])


app = FastAPI(
    title="Cybersecurity AI Agent",
    description="Agent core with dynamic plugin tooling.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1:7777"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plugins_router, prefix="/api", tags=["plugins"])
app.include_router(chat_router, prefix="/api", tags=["chat"])


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "plugins_loaded": len(registry_instance._plugins),
    }


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc), "path": request.url.path},
    )


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=7777, reload=False)
