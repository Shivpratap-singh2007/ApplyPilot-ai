"""Authenticated symmetric encryption helpers for sensitive stored text."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_ENC_PREFIX = "enc:v1:"


def _get_fernet() -> Fernet:
    settings = get_settings()
    raw_secret = (settings.data_encryption_key or settings.secret_key).encode("utf-8")
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        raw_secret,
        b"applypilot-at-rest-v1",
        iterations=100_000,
        dklen=32,
    )
    key = base64.urlsafe_b64encode(derived)
    return Fernet(key)


def encrypt_text(plaintext: str) -> str:
    """Encrypt non-empty text with Fernet authenticated encryption."""
    if not plaintext:
        return ""
    if plaintext.startswith(_ENC_PREFIX):
        return plaintext
    token = _get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{_ENC_PREFIX}{token}"


def decrypt_text(stored: str) -> str:
    """Decrypt text encrypted with `encrypt_text` (or return legacy plaintext untouched)."""
    if not stored:
        return ""
    if not stored.startswith(_ENC_PREFIX):
        return stored
    token = stored.removeprefix(_ENC_PREFIX).encode("ascii")
    try:
        return _get_fernet().decrypt(token).decode("utf-8")
    except InvalidToken:
        return ""

