"""File metadata, ownership, quotas and secure object access."""
from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any, Dict, List, Optional

from .. import database
from .. import storage_backends as objects
from . import db


def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    d["size"] = int(d.get("size") or 0)
    return d


def register(user_id: str, bucket: str, object_path: str, filename: str,
             size: int, content_type: str = "", sha256: str = "") -> Dict[str, Any]:
    fid = "file-" + secrets.token_hex(10)
    now = db.now()
    c = db.conn()
    c.execute(
        "INSERT INTO saas_files(id,user_id,bucket,object_path,filename,size,content_type,sha256,created,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (fid, user_id, bucket, object_path, str(filename or "")[:300], int(size),
         str(content_type or "")[:150], sha256 or "", now, now),
    )
    c.commit()
    return get(fid, user_id)


def get(file_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    c = db.conn()
    sql = "SELECT * FROM saas_files WHERE id=?"
    params: List[Any] = [file_id]
    if user_id:
        sql += " AND user_id=?"
        params.append(user_id)
    row = c.execute(sql, tuple(params)).fetchone()
    if not row:
        raise KeyError("file not found")
    return _row_to_dict(row)


def by_path(user_id: str, bucket: str, path: str) -> Optional[Dict[str, Any]]:
    row = db.conn().execute(
        "SELECT * FROM saas_files WHERE user_id=? AND bucket=? AND object_path=?",
        (user_id, bucket, path),
    ).fetchone()
    return _row_to_dict(row) if row else None


def list_files(user_id: str, bucket: str = "", page: int = 1,
               limit: int = 50) -> Dict[str, Any]:
    p, size, offset = database.page_params(page, limit)
    where = "user_id=?"
    params: List[Any] = [user_id]
    if bucket:
        where += " AND bucket=?"
        params.append(bucket)
    c = db.conn()
    total = c.execute(f"SELECT COUNT(*) FROM saas_files WHERE {where}", tuple(params)).fetchone()[0]
    rows = c.execute(
        f"SELECT * FROM saas_files WHERE {where} ORDER BY created DESC LIMIT ? OFFSET ?",
        tuple(params + [size, offset]),
    ).fetchall()
    return {"files": [_row_to_dict(r) for r in rows], "total": int(total),
            "page": p, "limit": size}


def storage_used(user_id: str) -> int:
    row = db.conn().execute(
        "SELECT COALESCE(SUM(size),0) FROM saas_files WHERE user_id=?", (user_id,)
    ).fetchone()
    return int(row[0] or 0)


def enforce_quota(user_id: str, extra_bytes: int) -> None:
    from . import plans

    sub = plans.ensure_subscription(user_id)
    plan = plans.get_plan(sub.get("plan_id", "free")) or plans.get_plan("free")
    limit_gb = float((plan or {}).get("config", {}).get("storage_gb", 1))
    limit_bytes = int(limit_gb * 1024 * 1024 * 1024)
    if storage_used(user_id) + int(extra_bytes) > limit_bytes:
        raise PermissionError(
            f"storage quota exceeded ({limit_gb} GB on the current plan)"
        )


def upload(user_id: str, bucket: str, filename: str, data: bytes,
           content_type: str = "") -> Dict[str, Any]:
    objects.validate_upload(bucket, len(data), content_type)
    enforce_quota(user_id, len(data))
    prefix = objects.user_prefix(user_id)
    safe_name = objects.sanitize_path(filename).split("/")[-1][:150]
    object_path = f"{prefix}/{int(time.time())}-{secrets.token_hex(4)}-{safe_name}"
    created = objects.backend().upload(
        bucket, object_path, data,
        content_type=content_type or "application/octet-stream",
        upsert=False,
    )
    sha = hashlib.sha256(data).hexdigest()
    try:
        return register(user_id, bucket, object_path, safe_name, len(data),
                        content_type, sha)
    except Exception:
        objects.backend().delete(bucket, object_path)
        raise


def download(user_id: str, file_id: str) -> bytes:
    row = get(file_id, user_id)
    return objects.backend().download(row["bucket"], row["object_path"])


def signed_url(user_id: str, file_id: str, expires: int = 3600) -> str:
    row = get(file_id, user_id)
    return objects.backend().signed_url(row["bucket"], row["object_path"], expires)


def delete(user_id: str, file_id: str) -> bool:
    row = get(file_id, user_id)
    c = db.conn()
    c.execute("DELETE FROM saas_files WHERE id=? AND user_id=?", (file_id, user_id))
    c.commit()
    try:
        objects.backend().delete(row["bucket"], row["object_path"])
    except Exception:
        # Metadata is gone; orphaned object can be reaped by retention job.
        pass
    return True


def object_from_signature(bucket: str, path: str, expires: Any, sig: str) -> bytes:
    """Serve a locally-stored object only with a valid HMAC signed URL."""
    if not objects.verify_local_signature(bucket, path, expires, sig):
        raise PermissionError("invalid or expired signed URL")
    if bucket not in objects.BUCKETS:
        raise KeyError("unknown bucket")
    return objects.backend().download(bucket, path)
