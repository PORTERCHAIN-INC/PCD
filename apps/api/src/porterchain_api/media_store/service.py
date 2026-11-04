"""Validate and store driver proof media. Keys: pod/<kind>/<driver>/<yyyy>/<mm>/<uuid>.<ext>."""
from __future__ import annotations

import base64
import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from porterchain_api.media_store import s3

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_SIGNATURE_BYTES = 512 * 1024
_MAGIC = {b"\xff\xd8\xff": ("image/jpeg", "jpg"), b"\x89PNG\r\n\x1a\n": ("image/png", "png")}
KEY_RE = re.compile(r"^pod/(photo|signature)/[A-Za-z0-9-]{1,64}/\d{4}/\d{2}/[0-9a-f-]{36}\.(jpg|png|webp)$")


def sniff(data: bytes) -> tuple[str, str]:
    for magic, out in _MAGIC.items():
        if data.startswith(magic):
            return out
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    raise ValueError("unsupported_image_type")


def _key(kind: str, driver_id: str, ext: str) -> str:
    now = datetime.now(UTC)
    did = re.sub(r"[^A-Za-z0-9-]", "", str(driver_id))[:64] or "unknown"
    return f"pod/{kind}/{did}/{now:%Y}/{now:%m}/{uuid.uuid4()}.{ext}"


def is_media_key(key: str | None) -> bool:
    return bool(key and KEY_RE.match(key))


def store_photo(driver_id: str, data: bytes, *, cfg: s3.S3Config | None = None, http: Any = None) -> dict[str, Any]:
    if not data:
        raise ValueError("empty_file")
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError("photo_too_large")
    ctype, ext = sniff(data)
    cfg = cfg or s3.config_from_env()
    if cfg is None:
        raise RuntimeError("media_storage_not_configured")
    key = _key("photo", driver_id, ext)
    s3.put_object(cfg, key, data, ctype, http=http)
    return {"key": key, "content_type": ctype, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_signature(driver_id: str, data_url: str, *, signer_name: str, cfg: s3.S3Config | None = None,
                    http: Any = None) -> dict[str, Any]:
    m = re.match(r"^data:image/png;base64,([A-Za-z0-9+/=]+)$", data_url or "")
    if not m:
        raise ValueError("signature_must_be_png_data_url")
    data = base64.b64decode(m.group(1))
    if len(data) > MAX_SIGNATURE_BYTES:
        raise ValueError("signature_too_large")
    if sniff(data)[0] != "image/png":
        raise ValueError("signature_must_be_png")
    if len((signer_name or "").strip()) < 2:
        raise ValueError("signer_name_required")
    cfg = cfg or s3.config_from_env()
    if cfg is None:
        raise RuntimeError("media_storage_not_configured")
    key = _key("signature", driver_id, "png")
    s3.put_object(cfg, key, data, "image/png", http=http)
    return {"key": key, "signer_name": signer_name.strip(), "sha256": hashlib.sha256(data).hexdigest()}


MEDIA_FIELDS = ("photo_key", "photo_keys", "media_key", "shipper_signature_key", "signature_key",
                "receiver_signature_key", "file_key")


def owner_of(key: str) -> str:
    return key.split("/")[2]


def require_own_keys(body: Any, driver_id: str) -> None:
    """Every media reference in a driver request must be a key this driver uploaded via /media/*."""
    if not isinstance(body, dict):
        return
    did = re.sub(r"[^A-Za-z0-9-]", "", str(driver_id))[:64] or "unknown"
    for f in MEDIA_FIELDS:
        v = body.get(f)
        for k in (v if isinstance(v, list) else [v]):
            if k in (None, ""):
                continue
            if not isinstance(k, str) or not is_media_key(k):
                raise ValueError(f"{f}_not_uploaded")
            if owner_of(k) != did:
                raise PermissionError(f"{f}_not_yours")
