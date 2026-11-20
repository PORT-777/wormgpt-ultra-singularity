"""Real account authentication: PBKDF2 passwords, hashed sessions, email tokens, RBAC."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import smtplib
import time
from email.message import EmailMessage
from typing import Any, Dict, Optional

from . import db

PBKDF2_ROUNDS = 210_000
SESSION_DAYS = int(os.getenv("SAAS_SESSION_DAYS", "7"))
REMEMBER_DAYS = int(os.getenv("SAAS_REMEMBER_DAYS", "30"))


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(dk.hex(), digest_hex)
    except Exception:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1] and len(email) <= 254


def register(email: str, password: str, username: str = "") -> Dict[str, Any]:
    email = email.strip().lower()
    if not _valid_email(email):
        raise ValueError("invalid email")
    if len(password) < 10:
        raise ValueError("password must be at least 10 characters")
    c = db.conn()
    if c.execute("SELECT 1 FROM saas_users WHERE email=?", (email,)).fetchone():
        raise ValueError("email already registered")
    uid = "usr-" + secrets.token_hex(8)
    c.execute(
        "INSERT INTO saas_users(id,email,username,password_hash,role,status,email_verified,created,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (uid, email, username or email.split("@")[0], _hash_password(password), "user",
         "pending_verification", 0, db.now(), db.now()),
    )
    c.commit()
    token = _new_token(uid, "verify", hours=48)
    delivered = _deliver_email(email, "Verify your PORT 777 AI account",
                               f"Verification token: {token}\nThis token expires in 48 hours.")
    return {"ok": True, "user_id": uid, "email": email,
            "email_delivery": delivered,
            "dev_verification_token": token if not delivered.get("sent") else None}


def _new_token(user_id: str, kind: str, hours: int = 24) -> str:
    token = secrets.token_urlsafe(32)
    c = db.conn()
    c.execute("INSERT INTO saas_tokens(token_hash,user_id,kind,expires,created) VALUES(?,?,?,?,?)",
              (_hash_token(token), user_id, kind, db.now() + hours * 3600, db.now()))
    c.commit()
    return token


def _consume_token(token: str, kind: str) -> Optional[str]:
    c = db.conn()
    row = c.execute("SELECT * FROM saas_tokens WHERE token_hash=? AND kind=? AND used=0 AND expires>?",
                    (_hash_token(token), kind, db.now())).fetchone()
    if not row:
        return None
    c.execute("UPDATE saas_tokens SET used=1 WHERE token_hash=?", (row["token_hash"],))
    c.commit()
    return row["user_id"]


def _deliver_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        return {"sent": False, "reason": "SMTP_HOST not configured"}
    try:
        msg = EmailMessage()
        msg["From"] = os.getenv("SMTP_FROM", "no-reply@port777.local")
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as s:
            if os.getenv("SMTP_TLS", "true").lower() == "true":
                s.starttls()
            user = os.getenv("SMTP_USER", "")
            if user:
                s.login(user, os.getenv("SMTP_PASSWORD", ""))
            s.send_message(msg)
        return {"sent": True}
    except Exception as exc:
        return {"sent": False, "reason": f"{type(exc).__name__}: {exc}"}


def verify_email(token: str) -> bool:
    uid = _consume_token(token, "verify")
    if not uid:
        return False
    c = db.conn()
    c.execute("UPDATE saas_users SET email_verified=1,status='active',updated=? WHERE id=?", (db.now(), uid))
    c.commit()
    return True


def login(email: str, password: str, *, remember: bool = False,
          ip: str = "", user_agent: str = "") -> Dict[str, Any]:
    c = db.conn()
    row = c.execute("SELECT * FROM saas_users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not row or not _verify_password(password, row["password_hash"]):
        raise ValueError("invalid email or password")
    if row["status"] in ("suspended", "deleted"):
        raise ValueError("account unavailable")
    token = secrets.token_urlsafe(40)
    days = REMEMBER_DAYS if remember else SESSION_DAYS
    c.execute(
        "INSERT INTO saas_sessions(token_hash,user_id,created,expires,remember,last_seen,ip,user_agent) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (_hash_token(token), row["id"], db.now(), db.now() + days * 86400,
         1 if remember else 0, db.now(), ip[:100], user_agent[:300]),
    )
    c.commit()
    return {"token": token, "user": public_user(row), "expires_days": days}


def logout(token: str) -> bool:
    c = db.conn()
    c.execute("UPDATE saas_sessions SET revoked=1 WHERE token_hash=?", (_hash_token(token),))
    c.commit()
    return True


def user_from_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    c = db.conn()
    row = c.execute(
        "SELECT u.* FROM saas_sessions s JOIN saas_users u ON u.id=s.user_id "
        "WHERE s.token_hash=? AND s.revoked=0 AND s.expires>?",
        (_hash_token(token), db.now()),
    ).fetchone()
    if not row:
        return None
    c.execute("UPDATE saas_sessions SET last_seen=? WHERE token_hash=?", (db.now(), _hash_token(token)))
    c.commit()
    return public_user(row)


def public_user(row) -> Dict[str, Any]:
    return {
        "id": row["id"], "email": row["email"], "username": row["username"],
        "role": row["role"], "status": row["status"],
        "email_verified": bool(row["email_verified"]),
        "profile_image": row["profile_image"],
        "preferences": db.jload(row["preferences"], {}),
    }


def request_password_reset(email: str) -> Dict[str, Any]:
    c = db.conn()
    row = c.execute("SELECT id FROM saas_users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not row:
        return {"ok": True, "note": "if the account exists, a reset token was issued"}
    token = _new_token(row["id"], "reset", hours=2)
    delivered = _deliver_email(email, "Reset your PORT 777 AI password",
                               f"Password reset token: {token}\nThis token expires in 2 hours.")
    return {"ok": True, "email_delivery": delivered,
            "dev_reset_token": token if not delivered.get("sent") else None}


def reset_password(token: str, new_password: str) -> bool:
    if len(new_password) < 10:
        raise ValueError("password must be at least 10 characters")
    uid = _consume_token(token, "reset")
    if not uid:
        return False
    c = db.conn()
    c.execute("UPDATE saas_users SET password_hash=?,updated=? WHERE id=?",
              (_hash_password(new_password), db.now(), uid))
    c.execute("UPDATE saas_sessions SET revoked=1 WHERE user_id=?", (uid,))
    c.commit()
    return True


def change_password(user_id: str, old: str, new: str) -> bool:
    c = db.conn()
    row = c.execute("SELECT password_hash FROM saas_users WHERE id=?", (user_id,)).fetchone()
    if not row or not _verify_password(old, row["password_hash"]):
        return False
    if len(new) < 10:
        raise ValueError("password must be at least 10 characters")
    c.execute("UPDATE saas_users SET password_hash=?,updated=? WHERE id=?",
              (_hash_password(new), db.now(), user_id))
    c.commit()
    return True


def list_sessions(user_id: str) -> list:
    c = db.conn()
    rows = c.execute("SELECT token_hash,created,expires,remember,last_seen,ip,user_agent,revoked "
                     "FROM saas_sessions WHERE user_id=? ORDER BY created DESC", (user_id,)).fetchall()
    return [{"id": r["token_hash"][:12], "created": r["created"], "expires": r["expires"],
             "remember": bool(r["remember"]), "last_seen": r["last_seen"],
             "ip": r["ip"], "user_agent": r["user_agent"], "revoked": bool(r["revoked"])} for r in rows]


def delete_account(user_id: str) -> bool:
    c = db.conn()
    c.execute("UPDATE saas_users SET status='deleted',email=email||'-deleted-'||?,updated=? WHERE id=?",
              (secrets.token_hex(4), db.now(), user_id))
    c.execute("UPDATE saas_sessions SET revoked=1 WHERE user_id=?", (user_id,))
    c.commit()
    return True
