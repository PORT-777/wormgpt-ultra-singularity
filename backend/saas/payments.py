"""Paymob payment adapter — real HTTP calls, HMAC verification, no simulated success."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict

try:
    from .. import database
except ImportError:  # imported as top-level `saas` package in tests
    import database

from . import db, plans

API = "https://accept.paymob.com/api"
HMAC_KEYS = [
    "amount_cents", "created_at", "currency", "error_occured", "has_parent_transaction",
    "id", "integration_id", "is_3d_secure", "is_auth", "is_capture", "is_refunded",
    "is_standalone_payment", "is_voided", "order.id", "owner", "pending",
    "source_data.pan", "source_data.sub_type", "source_data.type", "success",
]


def configured() -> bool:
    keys = ("PAYMOB_API_KEY", "PAYMOB_INTEGRATION_ID", "PAYMOB_IFRAME_ID", "PAYMOB_HMAC_SECRET")
    return all(os.getenv(k, "").strip() for k in keys)


def status() -> Dict[str, Any]:
    return {
        "provider": "paymob", "configured": configured(),
        "mode": os.getenv("PAYMOB_MODE", "test"),
        "requirements": list(("PAYMOB_API_KEY", "PAYMOB_INTEGRATION_ID", "PAYMOB_IFRAME_ID", "PAYMOB_HMAC_SECRET")),
        "note": "Recurring/subscription billing must be enabled on the merchant account; this adapter implements hosted checkout and verified callbacks.",
    }


def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    url = API + path
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Paymob {path} HTTP {e.code}: {e.read().decode()[:500]}") from e


def _dig(obj: Dict[str, Any], key: str):
    cur: Any = obj
    for part in key.split("."):
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(part, "")
    return cur


def verify_hmac(data: Dict[str, Any], supplied: str) -> bool:
    secret = os.getenv("PAYMOB_HMAC_SECRET", "").strip()
    if not secret or not supplied:
        return False
    source = "".join(str(_dig(data, k)) for k in HMAC_KEYS)
    expected = hmac.new(secret.encode(), source.encode(), hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, str(supplied))


def create_checkout(user_id: str, plan_id: str, period: str = "monthly") -> Dict[str, Any]:
    if not configured():
        raise RuntimeError("Paymob is not configured: " + ", ".join(status()["requirements"]))
    plan = plans.get_plan(plan_id)
    if not plan or not plan["active"]:
        raise ValueError("plan not found or inactive")
    amount = plan["monthly_price"] if period == "monthly" else plan["annual_price"]
    if amount <= 0:
        raise ValueError("paid checkout requires a priced plan")
    currency = os.getenv("PAYMOB_CURRENCY", "EGP")
    amount_cents = int(round(amount * 100))
    pid = "pay-" + os.urandom(8).hex()
    c = db.conn()
    c.execute(
        "INSERT INTO saas_payments(id,user_id,plan_id,provider,amount,currency,status,event,payload,created) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (pid, user_id, plan_id, "paymob", amount, currency, "pending", "checkout_created",
         db.jdump({"period": period}), db.now()),
    )
    c.commit()

    token = _post("/auth/tokens", {"api_key": os.environ["PAYMOB_API_KEY"]})
    order = _post("/ecommerce/orders", {
        "auth_token": token["token"],
        "delivery_needed": False,
        "amount_cents": amount_cents,
        "currency": currency,
        "merchant_order_id": pid,
        "items": [],
    })
    billing = {
        "apartment": "NA", "email": user_id, "floor": "NA", "first_name": "PORT777",
        "last_name": "User", "city": "Cairo", "country": "EG", "street": "NA",
        "building": "NA", "phone_number": "+20000000000", "postal_code": "NA",
        "extra_description": pid,
    }
    key = _post("/acceptance/payment_keys", {
        "auth_token": token["token"], "amount_cents": amount_cents, "expiration": 3600,
        "order_id": order["id"], "billing_data": billing, "currency": currency,
        "integration_id": int(os.environ["PAYMOB_INTEGRATION_ID"]), "lock_order_when_paid": True,
    })
    iframe = os.environ["PAYMOB_IFRAME_ID"]
    url = f"https://accept.paymob.com/api/acceptance/iframes/{iframe}?payment_token={key['token']}"
    c.execute("UPDATE saas_payments SET provider_ref=?,event='checkout_url_created' WHERE id=?",
              (str(order["id"]), pid))
    c.commit()
    return {"ok": True, "checkout_url": url, "payment_id": pid, "amount": amount, "currency": currency}


def handle_callback(data: Dict[str, Any], supplied_hmac: str) -> Dict[str, Any]:
    if not verify_hmac(data, supplied_hmac):
        raise ValueError("invalid Paymob HMAC signature")
    # Paymob sends two shapes: "Processed" callbacks nest everything in obj,
    # while "Response" callbacks are flat and use dotted keys (order.id).
    obj = data.get("obj") if isinstance(data.get("obj"), dict) else data
    txn = str(_dig(obj, "obj.id") or _dig(obj, "id") or "")
    merchant_order_id = str(
        _dig(obj, "obj.order.merchant_order_id")
        or _dig(obj, "order.merchant_order_id")
        or _dig(obj, "merchant_order_id")
        or ""
    )
    order_id = str(_dig(obj, "obj.order.id") or _dig(obj, "order.id")
                   or _dig(obj, "order_id") or "")
    c = db.conn()
    # Payment update + subscription activation must be atomic, and concurrent
    # callbacks for the same transaction must not both grant access.
    with database.transaction(c):
        lock = " FOR UPDATE" if database.IS_POSTGRES else ""
        # Prefer our own payment id; fall back to the provider order reference.
        row = None
        if merchant_order_id:
            row = c.execute(
                "SELECT * FROM saas_payments WHERE id=?" + lock, (merchant_order_id,)
            ).fetchone()
        if row is None and order_id:
            row = c.execute(
                "SELECT * FROM saas_payments WHERE provider_ref=?" + lock, (order_id,)
            ).fetchone()
        if row is None:
            raise ValueError("unknown payment order")
        existing = c.execute(
            "SELECT 1 FROM saas_payments WHERE provider='paymob' AND provider_txn_id=?" + lock,
            (txn,),
        ).fetchone()
        if existing:
            return {"ok": True, "duplicate": True, "payment_id": row["id"]}
        success = str(_dig(obj, "obj.success") or _dig(obj, "success")).lower() in ("true", "1")
        amount_cents = int(_dig(obj, "obj.amount_cents") or _dig(obj, "amount_cents") or 0)
        expected_cents = int(round(float(row["amount"]) * 100))
        if success and amount_cents != expected_cents:
            success = False
        c.execute(
            "UPDATE saas_payments SET provider_txn_id=?,status=?,event=?,payload=?,created=? WHERE id=?",
            (txn, "succeeded" if success else "failed",
             "callback_success" if success else "callback_failed",
             db.jdump(data), db.now(), row["id"]),
        )
        if success:
            payload = db.jload(row["payload"], {}) or {}
            duration = 365 if payload.get("period") == "annual" else 30
            period_end = db.now() + duration * 86400
            sub = c.execute(
                "SELECT id FROM saas_subscriptions WHERE user_id=? ORDER BY created DESC LIMIT 1" + lock,
                (row["user_id"],),
            ).fetchone()
            if sub:
                c.execute(
                    "UPDATE saas_subscriptions SET plan_id=?,status=?,provider=?,provider_ref=?,"
                    "current_period_end=?,updated=? WHERE id=?",
                    (row["plan_id"], "active", "paymob", txn, period_end, db.now(), sub["id"]),
                )
            else:
                c.execute(
                    "INSERT INTO saas_subscriptions(id,user_id,plan_id,status,provider,provider_ref,"
                    "current_period_end,created,updated) VALUES(?,?,?,?,?,?,?,?,?)",
                    ("sub-" + os.urandom(8).hex(), row["user_id"], row["plan_id"],
                     "active", "paymob", txn, period_end, db.now(), db.now()),
                )
    return {"ok": success, "payment_id": row["id"], "duplicate": False}


def history(user_id: str) -> list:
    c = db.conn()
    rows = c.execute("SELECT id,plan_id,provider,amount,currency,status,event,created FROM saas_payments WHERE user_id=? ORDER BY created DESC",
                     (user_id,)).fetchall()
    return [dict(r) for r in rows]
