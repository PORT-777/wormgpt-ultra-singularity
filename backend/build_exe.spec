# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# --- Backend root path ---
BACKEND_DIR = r"D:\xxxGPT\WormGPT_Ultra_Singularity\backend"

# --- Collect all tool modules ---
tool_modules = collect_submodules("tools")

# --- Collect all hidden imports ---
hiddenimports = [
    "fastapi",
    "uvicorn",
    "uvicorn.loop",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.websockets",
    "uvicorn.logging",
    "uvicorn.config",
    "uvicorn.server",
    "pydantic",
    "pydantic.fields",
    "pydantic.main",
    "pydantic.networks",
    "pydantic.type_adapter",
    "starlette",
    "starlette.applications",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.responses",
    "starlette.staticfiles",
    "anyio",
    "anyio.abc",
    "anyio.streams",
    "anyio.streams.text",
    "anyio._backends",
    "anyio._backends._asyncio",
    "anyio._backends._threading",
    "sniffio",
    "contextvars",
    "httptools",
    "websockets",
    "websockets.server",
    "websockets.client",
    "websockets.datastructures",
    "websockets.extensions",
    "websockets.frames",
    "websockets.headers",
    "websockets.http",
    "websockets.typing",
    "websockets.uri",
    "websockets.version",
    "multidict",
    "yarl",
    "idna",
    "async_timeout",
    "aiosqlite",
    "sqlite3",
    "json",
    "logging",
    "threading",
    "subprocess",
    "pathlib",
    "contextvars",
    "typing",
    "collections",
    "collections.abc",
    "enum",
    "re",
    "base64",
    "hashlib",
    "hmac",
    "secrets",
    "uuid",
    "zipfile",
    "shutil",
    "os",
    "sys",
    "time",
    "asyncio",
    "configs",
    "execution",
    "git_ops",
    "memory",
    "runtime_env",
    "user_memory",
    "sandbox",
    "storage",
    "voice",
    "agent_engine",
    "model_router",
    "scheduler",
    "security_api",
    "gateway",
    "tools",
    "tools.base",
    "workspace_manager",
    "api.workspace",
    "langchain_core",
    "langchain_core.messages",
    "langchain_core.output_parsers",
    "langchain_core.prompts",
    "langchain_core.runnables",
]

# Add tool modules
hiddenimports.extend(tool_modules)

# --- Data files ---
datas = [
    # Include configs directory
    (os.path.join(BACKEND_DIR, "configs"), "configs"),
    # Include prompts directory
    (os.path.join(BACKEND_DIR, "prompts"), "prompts"),
    # Include skills_packs
    (os.path.join(BACKEND_DIR, "skills_packs"), "skills_packs"),
    # Include data directory (for audit.jsonl etc.)
    (os.path.join(BACKEND_DIR, "data"), "data"),
]

a = Analysis(
    [os.path.join(BACKEND_DIR, "main.py")],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
    "torch", "torchvision", "torchaudio", "torchtext",
    "transformers", "tokenizers",
    "pandas", "numpy", "scipy", "sklearn", "cv2", "PIL", "pyarrow",
    "matplotlib", "seaborn", "plotly", "bokeh",
    "tensorflow", "keras",
    "jupyter", "notebook", "ipython",
    "pytest", "unittest", "doctest",
    "tkinter", "turtle",
    "tensorboard",
],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="WormGPT_Ultra_Singularity",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version_file=None,
    manifest=None,
    uac_admin=False,
    uac_uiaccess=False,
)
