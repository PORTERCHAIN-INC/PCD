"""Private proof-of-delivery photo store.

POD photos used to arrive as data URLs and were truncated to 500 chars in
``DriverStopMeta`` (the image was effectively lost). They are now written as files
under ``POD_MEDIA_DIR`` (default ``apps/api/data/pod-media``, never public) and the
proof keeps a ``pod://<key>`` reference. Retention deletes the file, then redacts the ref.
"""

from __future__ import annotations

import base64
import os
import re
import uuid
from pathlib import Path
from typing import Any

PREFIX = "pod://"
_DATA_URL = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$", re.S)
_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_KEY = re.compile(r"^[0-9a-f-]{36}/[0-9a-f]{32}\.(?:jpg|png|webp)$")
MAX_BYTES = 2_000_000


def root() -> Path:
    raw = (os.environ.get("POD_MEDIA_DIR") or "").strip()
    path = Path(raw) if raw else Path(__file__).resolve().parents[3] / "data" / "pod-media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_ref(value: str | None) -> bool:
    return bool(value) and str(value).startswith(PREFIX)


def _path(key: str) -> Path:
    if not _KEY.match(key):
        raise ValueError("pod_key_invalid")
    return root() / key


def save_data_url(order_id: str, data_url: str) -> str:
    """Store a data-URL photo; returns ``pod://<order_id>/<hex>.<ext>``."""
    m = _DATA_URL.match(data_url or "")
    if not m:
        raise ValueError("pod_photo_must_be_image_data_url")
    blob = base64.b64decode(m.group(2), validate=False)
    if not blob or len(blob) > MAX_BYTES:
        raise ValueError("pod_photo_size_invalid")
    key = f"{order_id}/{uuid.uuid4().hex}{_EXT[m.group(1)]}"
    p = _path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(blob)
    return PREFIX + key


def size(ref: str) -> int:
    try:
        p = _path(ref[len(PREFIX):])
    except ValueError:
        return 0
    return p.stat().st_size if p.exists() else 0


def delete(ref: str) -> bool:
    """Delete the file behind a ``pod://`` ref. True when a file was removed."""
    try:
        p = _path(ref[len(PREFIX):])
    except ValueError:
        return False
    if not p.exists():
        return False
    p.unlink()
    try:
        p.parent.rmdir()  # only succeeds when the order folder is empty
    except OSError:
        pass
    return True


def has_photo(db: Any, order_id: str) -> bool:
    from porterchain_api.driver_models import DriverStopMeta

    row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
    return bool(row and any(p.get("type") == "photo" for p in (row.meta or {}).get("proofs", [])))


def attach_photo(db: Any, order_id: str, driver_id: str, data_url: str) -> str:
    """Store the photo file and append a ``pod://`` proof to the order's stop meta."""
    from porterchain_api.driver_models import DriverStopMeta

    ref = save_data_url(order_id, data_url)
    row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
    if row is None:
        row = DriverStopMeta(order_id=order_id, driver_id=driver_id, meta={})
        db.add(row)
    meta = dict(row.meta or {})
    meta["proofs"] = [*meta.get("proofs", []), {"type": "photo", "value": ref}]
    row.meta = meta
    return ref
