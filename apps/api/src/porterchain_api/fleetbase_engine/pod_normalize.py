"""Normalize Fleetbase POD proofs into a gallery-friendly shape."""

from __future__ import annotations

from typing import Any


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
            "id": proof.get("id") or proof.get("uuid") or proof.get("fleetbase_proof_id"),
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

    return {
        "photos": photos,
        "signatures": signatures,
        "otp": otps,
        "other": other,
        "complete": bool(photos or signatures or otps),
        "source": "fleetbase" if (photos or signatures or otps or other) else None,
    }
