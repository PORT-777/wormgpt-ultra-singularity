"""Real SaaS tests: auth, isolation, entitlements, keys, admin, payment HMAC."""
from __future__ import annotations

import hashlib
import hmac
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from backend.main import app
from saas import auth, db, payments, plans

client = TestClient(app)


@pytest.fixture(autouse=True)
def _schema():
    """TestClient does not run lifespan, so create the tables explicitly."""
    db.init()
    plans.seed()


def _payloads():
    tag = uuid.uuid4().hex[:8]
    return {"email": f"u_{tag}@example.com", "password": "StrongPass12345", "username": f"u_{tag}"}


def _token(email: str, password: str) -> str:
    return client.post("/api/saas/auth/login", json={"email": email, "password": password}).json()["token"]


def _admin():
    p = _payloads()
    c = db.conn()
    c.execute(
        "INSERT INTO saas_users(id,email,username,password_hash,role,status,email_verified,created,updated) VALUES(?,?,?,?,?,?,?,?,?)",
        ("adm-" + uuid.uuid4().hex[:8], p["email"], "admin", auth._hash_password(p["password"]),
         "admin", "active", 1, db.now(), db.now()),
    )
    c.commit()
    return p["email"], p["password"]


def test_register_login_verify_and_isolation():
    p = _payloads()
    r = client.post("/api/saas/auth/register", json=p)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["dev_verification_token"]
    assert client.post("/api/saas/auth/verify", json={"token": body["dev_verification_token"]}).status_code == 200
    token = _token(p["email"], p["password"])
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/saas/me", headers=headers)
    assert me.status_code == 200 and me.json()["user"]["email"] == p["email"]
    other = _payloads()
    client.post("/api/saas/auth/register", json=other)
    other_token = _token(other["email"], other["password"])
    assert client.get("/api/saas/me", headers={"Authorization": f"Bearer {other_token}"}).json()["user"]["email"] != p["email"]
    assert client.get("/api/saas/me", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_password_reset_and_change():
    p = _payloads()
    client.post("/api/saas/auth/register", json=p)
    r = client.post("/api/saas/auth/request-reset", json={"email": p["email"]}).json()
    assert client.post("/api/saas/auth/reset", json={"token": r["dev_reset_token"], "password": "NewPass123456"}).status_code == 200
    token = _token(p["email"], "NewPass123456")
    assert client.post("/api/saas/me/password", headers={"Authorization": f"Bearer {token}"},
                       json={"old": "NewPass123456", "new": "FinalPass123456"}).status_code == 200


def test_entitlements_limits_and_model_permissions():
    p = _payloads()
    client.post("/api/saas/auth/register", json=p)
    token = _token(p["email"], p["password"])
    h = {"Authorization": f"Bearer {token}"}
    ent = client.get("/api/saas/entitlements", headers=h).json()
    assert ent["plan"]["id"] == "free"
    assert ent["allowed"]["api"] is False
    assert client.post("/api/saas/api-keys", headers=h, json={"name": "x"}).status_code == 200
    key = client.get("/api/saas/api-keys", headers=h).json()["keys"][0]
    assert client.delete(f"/api/saas/api-keys/{key['id']}", headers=h).status_code == 200
    from saas import usage

    for _ in range(30):
        usage.record(ent["subscription"]["user_id"] if "user_id" in ent["subscription"] else client.get("/api/saas/me", headers=h).json()["user"]["id"], "request")
    limited = client.get("/api/saas/entitlements", headers=h).json()
    assert limited["allowed"]["daily_requests"] is False


def test_admin_authorization():
    email, password = _admin()
    token = _token(email, password)
    assert client.get("/api/saas/admin/users", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    p = _payloads()
    client.post("/api/saas/auth/register", json=p)
    user_token = _token(p["email"], p["password"])
    assert client.get("/api/saas/admin/users", headers={"Authorization": f"Bearer {user_token}"}).status_code == 403


def test_paymob_hmac_and_webhook_idempotency(monkeypatch):
    secret = "test-hmac-secret"
    monkeypatch.setenv("PAYMOB_HMAC_SECRET", secret)
    p = _payloads()
    client.post("/api/saas/auth/register", json=p)
    token = _token(p["email"], p["password"])
    uid = client.get("/api/saas/me", headers={"Authorization": f"Bearer {token}"}).json()["user"]["id"]
    c = db.conn()
    pid = "pay-test-" + uuid.uuid4().hex[:8]
    order_ref = str(int(uuid.uuid4().int % 900000000) + 100000000)
    c.execute("INSERT INTO saas_payments(id,user_id,plan_id,provider,provider_ref,amount,currency,status,event,payload,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
              (pid, uid, "pro", "paymob", order_ref, 19.0, "EGP", "pending", "checkout_created", db.jdump({"period": "monthly"}), db.now()))
    c.commit()
    data = {
        "amount_cents": 1900, "created_at": "2026-01-01T00:00:00", "currency": "EGP",
        "error_occured": False, "has_parent_transaction": False,
        "id": int(uuid.uuid4().int % 900000000) + 100000000,
        "integration_id": 123, "is_3d_secure": False, "is_auth": False, "is_capture": False,
        "is_refunded": False, "is_standalone_payment": True, "is_voided": False,
        "order": {"id": int(order_ref), "merchant_order_id": pid}, "owner": 1, "pending": False,
        "source_data": {"pan": "2346", "sub_type": "MasterCard", "type": "card"}, "success": True,
    }
    source = "".join(str(payments._dig(data, k)) for k in payments.HMAC_KEYS)
    sig = hmac.new(secret.encode(), source.encode(), hashlib.sha512).hexdigest()
    r = client.post("/api/saas/webhook/paymob", json=data, headers={"hmac": sig})
    assert r.status_code == 200 and r.json()["ok"] is True
    again = client.post("/api/saas/webhook/paymob", json=data, headers={"hmac": sig})
    assert again.json()["duplicate"] is True
    sub = client.get("/api/saas/subscription", headers={"Authorization": f"Bearer {token}"}).json()
    assert sub["plan_id"] == "pro" and sub["status"] == "active"
    bad = client.post("/api/saas/webhook/paymob", json=data, headers={"hmac": "bad"})
    assert bad.status_code == 400
