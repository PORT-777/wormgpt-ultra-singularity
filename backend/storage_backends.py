"""Object storage abstraction (Supabase Storage / local / S3-compatible).

Private objects are always accessed through backend authorization. The
Supabase secret key is used server-side only and is never returned to the
browser. Local storage exists only for development.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except Exception:
    pass

BUCKETS: Dict[str, Dict[str, Any]] = {
    "avatars": {
        "public": True,
        "max_bytes": int(os.getenv("BUCKET_AVATARS_MAX_BYTES", str(5 * 1024 * 1024))),
        "mime": ["image/jpeg", "image/png", "image/webp", "image/gif"],
    },
    "user-files": {
        "public": False,
        "max_bytes": int(os.getenv("BUCKET_USER_FILES_MAX_BYTES", str(50 * 1024 * 1024))),
        "mime": [],
    },
    "chat-attachments": {
        "public": False,
        "max_bytes": int(os.getenv("BUCKET_CHAT_MAX_BYTES", str(20 * 1024 * 1024))),
        "mime": [],
    },
    "ai-generated-files": {
        "public": False,
        "max_bytes": int(os.getenv("BUCKET_AI_MAX_BYTES", str(50 * 1024 * 1024))),
        "mime": [],
    },
    "agent-artifacts": {
        "public": False,
        "max_bytes": int(os.getenv("BUCKET_AGENT_MAX_BYTES", str(100 * 1024 * 1024))),
        "mime": [],
    },
    "exports": {
        "public": False,
        "max_bytes": int(os.getenv("BUCKET_EXPORTS_MAX_BYTES", str(100 * 1024 * 1024))),
        "mime": [],
    },
}

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "auto").strip().lower()
LOCAL_ROOT = Path(
    os.getenv("STORAGE_LOCAL_DIR")
    or str(Path(__file__).resolve().parent / "data" / "storage")
)
SIGNING_SECRET = (
    os.getenv("FILE_SIGNING_SECRET")
    or os.getenv("AUTH_SECRET")
    or os.getenv("ENCRYPTION_MASTER_KEY")
    or "port777-local-signing-key"
)

_SAFE = re.compile(r"^[A-Za-z0-9._/\-]+$")


class StorageError(RuntimeError):
    pass


def sanitize_path(raw: str) -> str:
    """Normalize an object path and reject traversal / absolute paths."""
    value = str(raw or "").replace("\\", "/").strip()
    while value.startswith("/"):
        value = value[1:]
    segments = value.split("/")
    if any(part == ".." for part in segments):
        raise StorageError("path traversal is not allowed")
    parts = [p for p in segments if p not in ("", ".")]
    if not parts or not _SAFE.match("/".join(parts)):
        raise StorageError("invalid object path")
    return "/".join(parts)


def user_prefix(user_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(user_id or "anonymous"))[:64]


def validate_upload(bucket: str, size: int, content_type: str = "") -> None:
    cfg = BUCKETS.get(bucket)
    if not cfg:
        raise StorageError(f"unknown bucket: {bucket}")
    if size <= 0:
        raise StorageError("empty file")
    if size > cfg["max_bytes"]:
        raise StorageError(f"file exceeds {cfg['max_bytes']} byte limit for {bucket}")
    allowed = cfg.get("mime") or []
    if allowed and content_type not in allowed:
        raise StorageError("content type not allowed for this bucket")


class StorageBackend:
    """Common interface implemented by every storage adapter."""

    name = "base"

    def upload(self, bucket: str, path: str, data: bytes,
               content_type: str = "application/octet-stream",
               upsert: bool = True) -> Dict[str, Any]:
        raise NotImplementedError

    def download(self, bucket: str, path: str) -> bytes:
        raise NotImplementedError

    def delete(self, bucket: str, path: str) -> bool:
        raise NotImplementedError

    def copy(self, bucket: str, src: str, dst: str) -> bool:
        data = self.download(bucket, src)
        self.upload(bucket, dst, data)
        return True

    def move(self, bucket: str, src: str, dst: str) -> bool:
        self.copy(bucket, src, dst)
        return self.delete(bucket, src)

    def list(self, bucket: str, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def info(self, bucket: str, path: str) -> Dict[str, Any]:
        raise NotImplementedError

    def signed_url(self, bucket: str, path: str, expires: int = 3600) -> str:
        raise NotImplementedError

    def ensure_buckets(self) -> None:
        return None


class LocalStorage(StorageBackend):
    name = "local"

    def _target(self, bucket: str, path: str) -> Path:
        if bucket not in BUCKETS:
            raise StorageError(f"unknown bucket: {bucket}")
        target = (LOCAL_ROOT / bucket / sanitize_path(path)).resolve()
        root = (LOCAL_ROOT / bucket).resolve()
        if root not in target.parents and target != root:
            raise StorageError("path escapes storage root")
        return target

    def upload(self, bucket, path, data, content_type="application/octet-stream", upsert=True):
        target = self._target(bucket, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {"bucket": bucket, "path": path, "size": len(data), "backend": self.name}

    def download(self, bucket, path):
        target = self._target(bucket, path)
        if not target.is_file():
            raise StorageError("object not found")
        return target.read_bytes()

    def delete(self, bucket, path):
        target = self._target(bucket, path)
        if target.is_file():
            target.unlink()
            return True
        return False

    def list(self, bucket, prefix="", limit=100):
        root = (LOCAL_ROOT / bucket).resolve()
        if not root.is_dir():
            return []
        safe_prefix = sanitize_path(prefix) if prefix else ""
        base = root / safe_prefix
        if not base.exists():
            return []
        out = []
        for item in sorted(base.rglob("*")):
            if item.is_file():
                rel = item.relative_to(root).as_posix()
                out.append({
                    "name": item.name,
                    "path": rel,
                    "size": item.stat().st_size,
                    "updated_at": item.stat().st_mtime,
                })
                if len(out) >= limit:
                    break
        return out

    def info(self, bucket, path):
        target = self._target(bucket, path)
        if not target.is_file():
            raise StorageError("object not found")
        stat = target.stat()
        return {"path": path, "size": stat.st_size, "updated_at": stat.st_mtime}

    def signed_url(self, bucket, path, expires=3600):
        expire = int(time.time()) + max(1, int(expires))
        payload = f"{bucket}|{path}|{expire}"
        sig = hmac.new(SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        query = urllib.parse.urlencode({
            "bucket": bucket, "path": path, "expires": expire, "sig": sig,
        })
        return f"/api/saas/files/object?{query}"


def verify_local_signature(bucket: str, path: str, expires: Any, sig: str) -> bool:
    try:
        if int(expires) < int(time.time()):
            return False
    except (TypeError, ValueError):
        return False
    payload = f"{bucket}|{path}|{expires}"
    expected = hmac.new(SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(sig or ""))


class SupabaseStorage(StorageBackend):
    name = "supabase"

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
            raise StorageError(
                "Supabase Storage is not configured. Set SUPABASE_URL and "
                "SUPABASE_SECRET_KEY (service key from Dashboard -> Settings -> API)."
            )

    def _request(self, method: str, path: str, *, body: Any = None,
                 headers: Optional[Dict[str, str]] = None,
                 raw: bool = False) -> Any:
        url = SUPABASE_URL + "/storage/v1" + path
        data: Optional[bytes] = None
        default_headers = {
            "apikey": SUPABASE_SECRET_KEY,
            "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        }
        if body is not None:
            if isinstance(body, bytes):
                data = body
            else:
                data = json.dumps(body).encode()
                default_headers["Content-Type"] = "application/json"
        default_headers.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=default_headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = response.read()
                return payload if raw else json.loads(payload.decode() or "{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise StorageError(f"Supabase Storage {method} {path} HTTP {exc.code}: {detail}") from exc

    def upload(self, bucket, path, data, content_type="application/octet-stream", upsert=True):
        safe = sanitize_path(path)
        result = self._request(
            "POST", f"/object/{bucket}/{urllib.parse.quote(safe)}",
            body=data,
            headers={"Content-Type": content_type, "x-upsert": "true" if upsert else "false"},
        )
        return {"bucket": bucket, "path": safe, "size": len(data),
                "backend": self.name, "response": result}

    def download(self, bucket, path):
        return self._request(
            "GET", f"/object/{bucket}/{urllib.parse.quote(sanitize_path(path))}", raw=True
        )

    def delete(self, bucket, path):
        self._request("DELETE", f"/object/{bucket}/{urllib.parse.quote(sanitize_path(path))}")
        return True

    def list(self, bucket, prefix="", limit=100):
        result = self._request("POST", f"/object/list/{bucket}", body={
            "prefix": sanitize_path(prefix) if prefix else "",
            "limit": max(1, min(int(limit or 100), 1000)),
            "offset": 0,
            "sortByColumn": "name",
            "sortByOrder": "asc",
        })
        return result if isinstance(result, list) else []

    def info(self, bucket, path):
        result = self._request(
            "GET", f"/object/info/{bucket}/{urllib.parse.quote(sanitize_path(path))}"
        )
        return result if isinstance(result, dict) else {"path": path}

    def signed_url(self, bucket, path, expires=3600):
        result = self._request(
            "POST", f"/object/sign/{bucket}/{urllib.parse.quote(sanitize_path(path))}",
            body={"expiresIn": max(1, int(expires))},
        )
        token_path = result.get("signedURL") or result.get("signedUrl") or ""
        if not token_path:
            raise StorageError("Supabase did not return a signed URL")
        return SUPABASE_URL + "/storage/v1" + token_path

    def ensure_buckets(self) -> None:
        existing = self._request("GET", "/bucket")
        names = {b.get("name") for b in existing} if isinstance(existing, list) else set()
        for name, cfg in BUCKETS.items():
            if name in names:
                continue
            try:
                self._request("POST", "/bucket", body={
                    "name": name,
                    "id": name,
                    "public": bool(cfg.get("public")),
                    "file_size_limit": int(cfg["max_bytes"]),
                    "allowed_mime_types": list(cfg.get("mime") or []),
                })
            except StorageError:
                # Concurrent creation or policy restriction; re-check below.
                pass


class S3Storage(StorageBackend):
    """Optional S3-compatible adapter (requires boto3)."""

    name = "s3"

    def __init__(self):
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise StorageError("S3 storage requires: pip install boto3") from exc
        self._client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT") or None,
            aws_access_key_id=os.getenv("S3_ACCESS_KEY", ""),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY", ""),
            region_name=os.getenv("S3_REGION", "us-east-1"),
        )
        self._bucket = os.getenv("S3_BUCKET", "port777")

    def upload(self, bucket, path, data, content_type="application/octet-stream", upsert=True):
        key = f"{bucket}/{sanitize_path(path)}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        return {"bucket": bucket, "path": path, "size": len(data), "backend": self.name}

    def download(self, bucket, path):
        key = f"{bucket}/{sanitize_path(path)}"
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

    def delete(self, bucket, path):
        self._client.delete_object(Bucket=self._bucket, Key=f"{bucket}/{sanitize_path(path)}")
        return True

    def signed_url(self, bucket, path, expires=3600):
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": f"{bucket}/{sanitize_path(path)}",
            },
            ExpiresIn=max(1, int(expires)),
        )


_BACKEND: Optional[StorageBackend] = None


def backend() -> StorageBackend:
    global _BACKEND
    if _BACKEND is None:
        choice = STORAGE_BACKEND
        if choice == "local":
            _BACKEND = LocalStorage()
        elif choice == "supabase":
            _BACKEND = SupabaseStorage()
        elif choice == "s3":
            _BACKEND = S3Storage()
        elif SUPABASE_SECRET_KEY and SUPABASE_URL:
            _BACKEND = SupabaseStorage()
        else:
            _BACKEND = LocalStorage()
    return _BACKEND


def storage_status() -> Dict[str, Any]:
    try:
        b = backend()
        return {
            "backend": b.name,
            "configured": b.name != "supabase" or bool(SUPABASE_SECRET_KEY),
            "buckets": sorted(BUCKETS),
            "note": (
                "Supabase secret key required for private object access"
                if not SUPABASE_SECRET_KEY else "ready"
            ),
        }
    except Exception as exc:
        return {"backend": "unknown", "configured": False,
                "error": f"{type(exc).__name__}: {exc}", "buckets": sorted(BUCKETS)}


def ensure_buckets() -> None:
    b = backend()
    if b.name == "supabase":
        b.ensure_buckets()
