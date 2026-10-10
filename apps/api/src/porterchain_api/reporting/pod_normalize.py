"""Normalize POD proofs into a gallery-friendly shape.

Every POD surface — admin order 360, merchant 360, merchant live tracking —
reads this one function, so the galleries cannot disagree about what the driver
captured or about how to download it.
"""

from __future__ import annotations

import re
from typing import Any

#: Identifiers only. Dots are deliberately excluded: a handle ends up in a URL
#: path, a filename, and a ZIP entry name, and none of those want ``..``.
_SAFE_SLUG = re.compile(r"[^A-Za-z0-9_-]+")

#: Gallery key -> the singular kind used in a download handle.
_KIND_BY_GALLERY_KEY = {
    "photos": "photo",
    "signatures": "signature",
    "otp": "otp",
    "other": "other",
}


def proof_slug(value: Any) -> str | None:
    """A value reduced to something safe to put in a URL and a filename."""
    text = _SAFE_SLUG.sub("-", str(value or "").strip()).strip("-")
    return text.lower() or None


def normalize_pod(proofs: list[dict[str, Any]] | None) -> dict[str, Any]:
    photos: list[dict[str, Any]] = []
    signatures: list[dict[str, Any]] = []
    otps: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []

    for proof in proofs or []:
        if not isinstance(proof, dict):
            continue
        raw_type = str(proof.get("type") or proof.get("proof_type") or "").lower()
        normalized = {
            "id": proof.get("id")
            or proof.get("uuid")
            or proof.get("proof_id"),
            "type": raw_type,
            "url": proof.get("url") or proof.get("file_url") or proof.get("photo_url"),
            "captured_at": proof.get("captured_at") or proof.get("created_at"),
            "signature": proof.get("signature"),
            "notes": proof.get("notes") or proof.get("comment"),
            "otp": proof.get("otp") or proof.get("barcode") or proof.get("code"),
        }
        if raw_type in ("photo", "image", "picture"):
            photos.append(normalized)
        elif raw_type in ("signature", "sign"):
            signatures.append(normalized)
        elif raw_type in ("otp", "barcode", "pin", "code"):
            otps.append(normalized)
        elif normalized.get("url"):
            photos.append(normalized)
        else:
            other.append(normalized)

    gallery = {
        "photos": photos,
        "signatures": signatures,
        "otp": otps,
        "other": other,
        "complete": bool(photos or signatures or otps),
        "source": "porterchain" if (photos or signatures or otps or other) else None,
    }
    return stamp_download_slugs(gallery)


def stamp_download_slugs(gallery: dict[str, Any]) -> dict[str, Any]:
    """Give every proof a stable ``download`` handle (BR).

    The portal sends this handle back to ask for the bytes, so it never has to
    hand the API a media URL. A stable proof id is preferred because gallery
    order could shift between the page load and the download click; position
    is the fallback when a proof arrives without an id.
    """
    used: set[str] = set()
    for gallery_key, kind in _KIND_BY_GALLERY_KEY.items():
        entries = gallery.get(gallery_key)
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            slug = proof_slug(entry.get("id")) or f"{kind}-{index}"
            if slug in used:
                slug = f"{kind}-{index}"
            used.add(slug)
            entry["download"] = slug
    return gallery
