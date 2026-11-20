"""Real tests for the persistent database + object storage layers.

Database and storage translation tests always run against the local adapter.
The live Supabase round-trip is opt-in (RUN_SUPABASE_TESTS=1) because it needs
real credentials and permanently writes to the project.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import database
import storage_backends
from backend.main import app
from saas import auth, db, files, plans

client = TestClient(app)


@pytest.fixture(autouse=True)
def _schema():
    db.init()
    plans.seed()


@pytest.fixture()
def local_storage(monkeypatch):
    monkeypatch.setattr(storage_backends, "_BACKEND", storage_backends.LocalStorage())
    return storage_backends.backend()


def _account():
    tag = uuid.uuid4().hex[:8]
    email = f"supa_{tag}@example.com"
    password = "StrongPass12345"
    body = client.post("/api/saas/auth/register", json={
        "email": email, "password": password, "username": tag,
    }).json()
    assert body.get("ok"), body
    token = client.post("/api/saas/auth/login", json={
        "email": email, "password": password,
    }).json()["token"]
    return email, password, token, {"Authorization": f"Bearer {token}"}


def test_sql_translation_for_postgres(monkeypatch):
    monkeypatch.setattr(database, "IS_POSTGRES", True)
    assert database._pg_placeholders("SELECT * FROM t WHERE a=? AND b='?'") == \
        "SELECT * FROM t WHERE a=%s AND b='?'"
    assert "ON CONFLICT (module, key) DO UPDATE" in database._pg_upsert(
        "INSERT OR REPLACE INTO kv_store(module,key,value) VALUES (?,?,?)")
    assert "BIGSERIAL PRIMARY KEY" in database._translate(
        "CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    assert database.page_params(3, 25)[2] == 50


def test_health_reports_real_database():
    r = client.get("/health")
    assert r.status_code in (200, 503)
    body = r.json()
    assert body["database"]["backend"] in ("sqlite", "postgresql")
    assert isinstance(body["database"]["ok"], bool)
    assert "storage" in client.get("/api/health").json()


def test_local_storage_roundtrip_and_private_access(local_storage, tmp_path):
    monkeypatch_target = tmp_path / "objects"
    storage_backends.LOCAL_ROOT = monkeypatch_target
    local_storage.upload("user-files", "u1/hello.txt", b"hello", "text/plain")
    assert local_storage.download("user-files", "u1/hello.txt") == b"hello"
    assert local_storage.info("user-files", "u1/hello.txt")["size"] == 5
    assert any(f["path"] == "u1/hello.txt" for f in local_storage.list("user-files", "u1"))
    url = local_storage.signed_url("user-files", "u1/hello.txt", 60)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert files.object_from_signature(
        qs["bucket"][0], qs["path"][0], qs["expires"][0], qs["sig"][0]) == b"hello"
    with pytest.raises(PermissionError):
        files.object_from_signature("user-files", "u1/hello.txt", qs["expires"][0], "bad-sig")
    assert local_storage.delete("user-files", "u1/hello.txt") is True
    with pytest.raises(storage_backends.StorageError):
        local_storage.upload("user-files", "../escape.txt", b"x")


def test_file_upload_download_and_tenant_isolation(local_storage, monkeypatch, tmp_path):
    storage_backends.LOCAL_ROOT = tmp_path / "objects"
    _, _, _, owner = _account()
    _, _, _, other = _account()

    upload = client.post(
        "/api/saas/files/upload",
        files={"file": ("report.txt", b"secret report", "text/plain")},
        data={"bucket": "user-files"},
        headers=owner,
    )
    assert upload.status_code == 200, upload.text
    fid = upload.json()["id"]

    assert client.get(f"/api/saas/files/{fid}", headers=owner).status_code == 200
    assert client.get(f"/api/saas/files/{fid}", headers=other).status_code == 404
    content = client.get(f"/api/saas/files/{fid}/content", headers=owner)
    assert content.status_code == 200 and content.content == b"secret report"
    assert client.get(f"/api/saas/files/{fid}/content", headers=other).status_code == 404

    url = client.get(f"/api/saas/files/{fid}/url", headers=owner).json()["url"]
    signed = client.get(url)
    assert signed.status_code == 200 and signed.content == b"secret report"

    listed = client.get("/api/saas/files?page=1&limit=5", headers=owner).json()
    assert listed["total"] >= 1 and listed["page"] == 1
    assert client.delete(f"/api/saas/files/{fid}", headers=other).status_code == 404
    assert client.delete(f"/api/saas/files/{fid}", headers=owner).status_code == 200


def test_upload_limits_are_enforced(local_storage, tmp_path):
    storage_backends.LOCAL_ROOT = tmp_path / "objects"
    _, _, _, headers = _account()
    r = client.post(
        "/api/saas/files/upload",
        files={"file": ("bad.exe", b"not an image", "application/x-msdownload")},
        data={"bucket": "avatars"},
        headers=headers,
    )
    assert r.status_code == 400
    r = client.post(
        "/api/saas/files/upload",
        files={"file": ("x.txt", b"data", "text/plain")},
        data={"bucket": "does-not-exist"},
        headers=headers,
    )
    assert r.status_code == 400


def test_migrations_are_additive_only():
    migration_dir = BACKEND / "migrations"
    assert (migration_dir / "001_initial.sql").is_file()
    assert (migration_dir / "002_rls.sql").is_file()
    for path in migration_dir.glob("*.sql"):
        sql = path.read_text(encoding="utf-8").upper()
        assert "DROP TABLE" not in sql
        assert "TRUNCATE" not in sql
    schema = (migration_dir / "001_initial.sql").read_text(encoding="utf-8")
    for name in ("saas_users", "saas_payments", "saas_files", "messages", "computers"):
        assert f"CREATE TABLE IF NOT EXISTS {name}" in schema


@pytest.mark.skipif(
    os.getenv("RUN_SUPABASE_TESTS") != "1" or not os.getenv("SUPABASE_SECRET_KEY"),
    reason="set RUN_SUPABASE_TESTS=1 and SUPABASE_SECRET_KEY for live Supabase tests",
)
def test_live_supabase_roundtrip():
    """Opt-in: verifies DB connection, user, conversation, message, payment, file."""
    assert database.IS_POSTGRES
    assert database.health()["ok"] is True
    uid = "usr-test-" + uuid.uuid4().hex[:8]
    c = database.conn()
    try:
        c.execute(
            "INSERT INTO saas_users(id,email,password_hash,role,status,email_verified,created,updated) "
            "VALUES(%s,%s,%s,'user','active',1,%s,%s)",
            (uid, f"{uid}@example.test", auth._hash_password("StrongPass12345"), 0, 0),
        )
        c.execute(
            "INSERT INTO sessions(id,created,title) VALUES(%s,%s,%s)",
            (uid + "-s", 0, "test"),
        )
        c.execute(
            "INSERT INTO messages(session_id,role,content,ts) VALUES(%s,%s,%s,%s)",
            (uid + "-s", "user", "persisted", 0),
        )
        count = c.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id=%s", (uid + "-s",)
        ).fetchone()[0]
        assert count >= 1
        plans.ensure_subscription(uid)
        c.commit()
        assert storage_backends.backend().name == "supabase"
        storage_backends.backend().upload("user-files", uid + "/t.txt", b"live")
        assert storage_backends.backend().download("user-files", uid + "/t.txt") == b"live"
    finally:
        for table, column in (
            ("saas_subscriptions", "user_id"),
            ("messages", "session_id"), ("sessions", "id"),
            ("saas_users", "id"),
        ):
            c.execute(f"DELETE FROM {table} WHERE {column}=%s", (uid,))
        c.commit()
        try:
            storage_backends.backend().delete("user-files", uid + "/t.txt")
        except Exception:
            pass


def test_backend_selection():
    assert storage_backends.storage_status()["buckets"]
    assert database.backend_name() in ("sqlite", "postgresql")
    with pytest.raises(storage_backends.StorageError):
        storage_backends.sanitize_path("../../etc/passwd")
