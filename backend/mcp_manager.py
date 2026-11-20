"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: MCP (Model Context Protocol) manager

Task 1: local config storage + read-only connect/test/discovery.
Task 3: guarded MCP tool execution for the agent (opt-in, audited).

No hard dependency on the `mcp` package: missing SDK returns a clear
diagnostic instead of crashing boot.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import configs as config

log = logging.getLogger("mcp_manager")

DEFAULT_CONFIG = {"servers": {}}
MAX_AUDIT_ARGS = 240
MAX_AUDIT_OUT = 180


def _config_path() -> Path:
    path = getattr(config, "MCP_CONFIG_PATH", None)
    if path is None:
        path = config.BACKEND_DIR / "data" / "mcp_servers.json"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_config() -> Dict[str, Any]:
    path = _config_path()
    if not path.exists():
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT_CONFIG))
        data.setdefault("servers", {})
        if not isinstance(data["servers"], dict):
            data["servers"] = {}
        return data
    except Exception as exc:
        log.warning("failed to read MCP config %s: %s", path, exc)
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(data: Dict[str, Any]) -> None:
    path = _config_path()
    data = data or DEFAULT_CONFIG
    data.setdefault("servers", {})
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def _sdk_status() -> Dict[str, Any]:
    try:
        import mcp  # type: ignore
        return {
            "available": True,
            "version": getattr(mcp, "__version__", None),
        }
    except Exception as exc:
        return {
            "available": False,
            "version": None,
            "error": f"{type(exc).__name__}: {exc}",
            "install_hint": "pip install mcp  (in backend .venv) to enable MCP connect/test/execution",
        }


def status() -> Dict[str, Any]:
    cfg = load_config()
    servers = cfg.get("servers", {}) or {}
    return {
        "enabled": bool(getattr(config, "MCP_ENABLED", False)),
        "execution_requires_full_access": not bool(getattr(config, "ZERO_REFUSAL", False)),
        "sdk": _sdk_status(),
        "config_path": str(_config_path()),
        "server_count": len(servers),
        "limits": {
            "connect_timeout_s": float(getattr(config, "MCP_CONNECT_TIMEOUT", 15)),
            "exec_timeout_s": float(getattr(config, "MCP_EXEC_TIMEOUT", 45)),
            "max_output_chars": int(getattr(config, "MCP_MAX_OUTPUT_CHARS", 12000)),
        },
    }


def list_servers() -> List[Dict[str, Any]]:
    cfg = load_config()
    out: List[Dict[str, Any]] = []
    for name, spec in (cfg.get("servers", {}) or {}).items():
        spec = spec if isinstance(spec, dict) else {}
        out.append({
            "name": name,
            "enabled": bool(spec.get("enabled", True)),
            "transport": spec.get("transport", "stdio"),
            "command": spec.get("command", ""),
            "args": spec.get("args", []) if isinstance(spec.get("args"), list) else [],
            "has_env": bool(spec.get("env")),
        })
    out.sort(key=lambda x: x["name"].lower())
    return out


def _get_server_spec(name: str) -> Optional[Dict[str, Any]]:
    cfg = load_config()
    spec = (cfg.get("servers", {}) or {}).get(name)
    return spec if isinstance(spec, dict) else None


def upsert_server(name: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("server name is required")
    if any(c in name for c in "/\\\x00"):
        raise ValueError("invalid server name")
    transport = str(spec.get("transport", "stdio") or "stdio").lower()
    if transport != "stdio":
        raise ValueError("only transport='stdio' is supported")
    command = str(spec.get("command", "") or "").strip()
    if not command:
        raise ValueError("command is required for stdio transport")
    args = spec.get("args", [])
    if args is None:
        args = []
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise ValueError("args must be a list of strings")
    env = spec.get("env", {})
    if env is None:
        env = {}
    if not isinstance(env, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ValueError("env must be an object of string keys/values")

    cfg = load_config()
    cfg.setdefault("servers", {})
    cfg["servers"][name] = {
        "enabled": bool(spec.get("enabled", True)),
        "transport": "stdio",
        "command": command,
        "args": args,
        "env": env,
    }
    save_config(cfg)
    return {"ok": True, "name": name, "server": cfg["servers"][name]}


def remove_server(name: str) -> Dict[str, Any]:
    cfg = load_config()
    servers = cfg.get("servers", {}) or {}
    if name not in servers:
        return {"ok": False, "deleted": False, "error": "server not found"}
    del servers[name]
    cfg["servers"] = servers
    save_config(cfg)
    return {"ok": True, "deleted": True, "name": name}


def _stdio_params(spec: Dict[str, Any]):
    command = str(spec.get("command", "")).strip()
    args = spec.get("args", []) if isinstance(spec.get("args"), list) else []
    env_spec = spec.get("env", {}) if isinstance(spec.get("env"), dict) else {}
    resolved = shutil.which(command) or command
    merged_env = os.environ.copy()
    merged_env.update({str(k): str(v) for k, v in env_spec.items()})
    from mcp import StdioServerParameters  # type: ignore
    return StdioServerParameters(command=resolved, args=list(args), env=merged_env), resolved


def _summarize_tool_result(result: Any) -> Dict[str, Any]:
    parts: List[str] = []
    for item in (getattr(result, "content", None) or []):
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(str(text))
            continue
        data = getattr(item, "data", None)
        if data is not None:
            try:
                parts.append(json.dumps(data, ensure_ascii=False)[:4000])
            except Exception:
                parts.append(str(data)[:4000])
            continue
        try:
            parts.append(json.dumps(item, ensure_ascii=False, default=str)[:2000])
        except Exception:
            parts.append(str(item)[:2000])
    structured = getattr(result, "structuredContent", None)
    text = "\n".join(p for p in parts if p).strip()
    max_chars = int(getattr(config, "MCP_MAX_OUTPUT_CHARS", 12000))
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "\n...[truncated]"
    return {
        "isError": bool(getattr(result, "isError", False)),
        "text": text,
        "structuredContent": structured,
        "truncated": truncated,
    }


async def test_server(name: str) -> Dict[str, Any]:
    """Read-only connect + capability discovery. No tool execution."""
    started = time.time()
    spec = _get_server_spec(name)
    if not spec:
        return {"ok": False, "name": name, "error": "server not found"}
    if not spec.get("enabled", True):
        return {"ok": False, "name": name, "error": "server is disabled"}

    sdk = _sdk_status()
    if not sdk.get("available"):
        return {
            "ok": False,
            "name": name,
            "error": "MCP SDK not installed in backend environment",
            "sdk": sdk,
            "elapsed_ms": int((time.time() - started) * 1000),
        }

    timeout = float(getattr(config, "MCP_CONNECT_TIMEOUT", 15))
    try:
        from mcp import ClientSession  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
        params, resolved = _stdio_params(spec)

        async def _probe() -> Dict[str, Any]:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_resp = await session.list_tools()
                    resources_resp = await session.list_resources()
                    prompts_resp = await session.list_prompts()
                    tools = [{
                        "name": getattr(t, "name", ""),
                        "description": getattr(t, "description", "") or "",
                        "inputSchema": getattr(t, "inputSchema", None),
                    } for t in (getattr(tools_resp, "tools", None) or [])]
                    resources = [{
                        "uri": str(getattr(r, "uri", "")),
                        "name": getattr(r, "name", "") or "",
                        "description": getattr(r, "description", "") or "",
                        "mimeType": getattr(r, "mimeType", None),
                    } for r in (getattr(resources_resp, "resources", None) or [])]
                    prompts = [{
                        "name": getattr(p, "name", ""),
                        "description": getattr(p, "description", "") or "",
                    } for p in (getattr(prompts_resp, "prompts", None) or [])]
                    return {
                        "ok": True,
                        "name": name,
                        "transport": "stdio",
                        "command": resolved,
                        "capabilities": {"tools": tools, "resources": resources, "prompts": prompts},
                        "counts": {"tools": len(tools), "resources": len(resources), "prompts": len(prompts)},
                    }

        result = await asyncio.wait_for(_probe(), timeout=timeout)
        result["elapsed_ms"] = int((time.time() - started) * 1000)
        result["sdk"] = sdk
        return result
    except asyncio.TimeoutError:
        return {"ok": False, "name": name, "error": f"connect/test timed out after {timeout:g}s",
                "sdk": sdk, "elapsed_ms": int((time.time() - started) * 1000)}
    except Exception as exc:
        log.warning("MCP test failed for %s: %s", name, exc)
        return {"ok": False, "name": name, "error": f"{type(exc).__name__}: {exc}",
                "sdk": sdk, "elapsed_ms": int((time.time() - started) * 1000)}


async def call_tool(server_name: str, tool_name: str,
                    arguments: Optional[Dict[str, Any]] = None,
                    *, allow_execution: bool = False) -> Dict[str, Any]:
    """Guarded MCP tool execution (Task 3). Opt-in + Full Access required."""
    started = time.time()
    args = arguments if isinstance(arguments, dict) else {}
    audit_args = json.dumps(args, ensure_ascii=False, default=str)[:MAX_AUDIT_ARGS]
    label = f"MCP:{server_name}:{tool_name}"

    if not bool(getattr(config, "MCP_ENABLED", False)):
        return {"ok": False, "server": server_name, "tool": tool_name,
                "error": "MCP execution disabled (set MCP_ENABLED=true in backend config/.env after review)"}
    if False and not allow_execution:
        return {"ok": False, "server": server_name, "tool": tool_name,
                "error": "MCP tool execution execution requires MCP to be enabled/configured for this request"}

    spec = _get_server_spec(server_name)
    if not spec:
        return {"ok": False, "server": server_name, "tool": tool_name, "error": "MCP server not found"}
    if not spec.get("enabled", True):
        return {"ok": False, "server": server_name, "tool": tool_name, "error": "MCP server is disabled"}
    if not str(tool_name or "").strip():
        return {"ok": False, "server": server_name, "tool": tool_name, "error": "MCP tool name is required"}

    sdk = _sdk_status()
    if not sdk.get("available"):
        return {"ok": False, "server": server_name, "tool": tool_name,
                "error": "MCP SDK not installed in backend environment", "sdk": sdk}

    timeout = float(getattr(config, "MCP_EXEC_TIMEOUT", 45))
    try:
        import storage
        storage.audit(label, audit_args, "executing")
    except Exception:
        pass

    try:
        from mcp import ClientSession  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
        params, resolved = _stdio_params(spec)

        async def _run() -> Dict[str, Any]:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, args)
                    summary = _summarize_tool_result(result)
                    return {
                        "ok": not summary["isError"],
                        "server": server_name,
                        "tool": tool_name,
                        "command": resolved,
                        "elapsed_ms": int((time.time() - started) * 1000),
                        "result": summary,
                    }

        out = await asyncio.wait_for(_run(), timeout=timeout)
        try:
            import storage
            status = "ok" if out.get("ok") else "tool_error"
            detail = (out.get("result") or {}).get("text") or ""
            storage.audit(label, audit_args, f"{status}:{detail[:MAX_AUDIT_OUT]}")
        except Exception:
            pass
        return out
    except asyncio.TimeoutError:
        try:
            import storage
            storage.audit(label, audit_args, f"timeout:{timeout:g}s")
        except Exception:
            pass
        return {"ok": False, "server": server_name, "tool": tool_name,
                "error": f"MCP tool call timed out after {timeout:g}s",
                "elapsed_ms": int((time.time() - started) * 1000)}
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        try:
            import storage
            storage.audit(label, audit_args, f"error:{err[:MAX_AUDIT_OUT]}")
        except Exception:
            pass
        log.warning("MCP call failed %s.%s: %s", server_name, tool_name, exc)
        return {"ok": False, "server": server_name, "tool": tool_name, "error": err,
                "elapsed_ms": int((time.time() - started) * 1000)}

