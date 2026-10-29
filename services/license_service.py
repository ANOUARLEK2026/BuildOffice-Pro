# ============================================================
# شرح الملف: services/license_service.py
# هذا الملف جزء من منطق الأعمال والخدمات والتحليلات.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro.
"""Offline license activation and local authentication.

The distributed application contains only the Ed25519 public key.
Keep the seller private key outside the distributed application.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from repositories.db import get_connection

PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAjX2/IXGIKpB1m4+6C4g8TfNbGD+4Ku6vQdMfLJLlO0k=
-----END PUBLIC KEY-----"""
PRODUCT_NAME = "BuildOffice Pro"


# شرح الدالة _b64e: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


# شرح الدالة _b64d: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# شرح الدالة _machine_guid: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _machine_guid() -> str:
    """Return a stable Windows machine identifier without collecting personal data."""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                if value:
                    return str(value)
        except (ImportError, OSError):
            pass
    return f"{platform.node()}|{uuid.getnode()}"


# شرح الدالة device_id: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def device_id() -> str:
    """Return a one-way device fingerprint used for local activation binding."""
    return hashlib.sha256(
        ("BuildOffice Pro|" + _machine_guid()).encode("utf-8")
    ).hexdigest()


# شرح الدالة _public_key: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _public_key() -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("Configured public key is not an Ed25519 public key.")
    return key


# شرح الدالة verify_license_key: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def verify_license_key(license_key: str) -> dict:
    """Verify signature, product, required fields, and expiration."""
    key = license_key.strip()
    if not key:
        raise ValueError("License key is empty.")

    parts = key.split(".")
    if len(parts) != 3 or parts[0] != "BOP1":
        raise ValueError("Invalid BuildOffice Pro license format.")

    payload_raw = _b64d(parts[1])
    signature = _b64d(parts[2])
    _public_key().verify(signature, payload_raw)
    payload = json.loads(payload_raw.decode("utf-8"))

    if payload.get("product") != PRODUCT_NAME:
        raise ValueError("This license belongs to another product.")
    if not payload.get("license_id") or not payload.get("customer"):
        raise ValueError("License data is incomplete.")

    expires = payload.get("expires_at")
    if expires:
        expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) >= expiry:
            raise ValueError("This license has expired.")

    return payload


# شرح الدالة is_activated: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def is_activated() -> bool:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT 1 FROM app_license WHERE status='Active' LIMIT 1"
        ).fetchone() is not None
    finally:
        conn.close()


# شرح الدالة activate_license: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def activate_license(license_key: str) -> dict:
    """Verify and bind a license to the current device."""
    payload = verify_license_key(license_key)
    current_device = device_id()

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT device_id FROM app_license WHERE license_id=?",
            (payload["license_id"],),
        ).fetchone()
        if existing and existing["device_id"] != current_device:
            raise ValueError("This license is already activated on another device.")

        conn.execute("DELETE FROM app_license")
        conn.execute(
            """
            INSERT INTO app_license
            (license_id, license_key, customer_name, product_name,
             issued_at, expires_at, device_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
            """,
            (
                payload["license_id"],
                license_key.strip(),
                payload["customer"],
                payload["product"],
                payload["issued_at"],
                payload.get("expires_at"),
                current_device,
            ),
        )
        conn.commit()
        return payload
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة license_status: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def license_status() -> dict | None:
    """Return the active license when it is still valid on this device."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM app_license WHERE status='Active' LIMIT 1"
        ).fetchone()
        if not row or row["device_id"] != device_id():
            return None

        expires = row["expires_at"]
        if expires:
            expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) >= expiry:
                conn.execute(
                    "UPDATE app_license SET status='Expired' WHERE license_id=?",
                    (row["license_id"],),
                )
                conn.commit()
                return None
        return dict(row)
    finally:
        conn.close()


# شرح الدالة _hash_password: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a password using scrypt and a unique random salt."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return _b64e(digest), _b64e(salt)


# شرح الدالة user_count: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def user_count() -> int:
    conn = get_connection()
    try:
        return int(conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0])
    finally:
        conn.close()


# شرح الدالة create_user: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def create_user(username: str, password: str, role: str = "Administrator") -> None:
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must contain at least 3 characters.")
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    password_hash, salt = _hash_password(password)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO app_users(user_id, username, password_hash, password_salt, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), username, password_hash, salt, role),
        )
        conn.commit()
    except (sqlite3.Error, ValueError, TypeError, OSError):
        conn.rollback()
        raise
    finally:
        conn.close()


# شرح الدالة authenticate: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def authenticate(username: str, password: str) -> dict | None:
    """Authenticate a local user and update the last-login timestamp."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM app_users WHERE username=? AND active=1 COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        if not row:
            return None

        digest, _ = _hash_password(password, _b64d(row["password_salt"]))
        if not secrets.compare_digest(digest, row["password_hash"]):
            return None

        conn.execute(
            "UPDATE app_users SET last_login_at=CURRENT_TIMESTAMP WHERE user_id=?",
            (row["user_id"],),
        )
        conn.commit()
        return dict(row)
    finally:
        conn.close()
