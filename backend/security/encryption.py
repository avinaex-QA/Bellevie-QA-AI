"""
Encryption helpers for integration credentials.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet

from backend.config.settings import settings


def _derive_local_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    key = settings.encryption_key
    if key:
        return Fernet(key.encode("utf-8"))
    return Fernet(_derive_local_key(settings.app_secret_key))


def encrypt_json(payload: dict[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if value not in (None, "")}
    raw = json.dumps(clean, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet().encrypt(raw).decode("utf-8")


def decrypt_json(token: str) -> dict[str, Any]:
    if not token:
        return {}
    raw = _fernet().decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))
