"""Encrypt merchant webhook signing secrets for server-side HMAC delivery."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(encryption_key: str) -> Fernet:
    digest = hashlib.sha256(encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_signing_secret(plaintext: str, *, encryption_key: str) -> str:
    return _fernet(encryption_key).encrypt(plaintext.encode()).decode()


def decrypt_signing_secret(ciphertext: str, *, encryption_key: str) -> str:
    try:
        return _fernet(encryption_key).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("invalid_signing_secret_ciphertext") from exc
