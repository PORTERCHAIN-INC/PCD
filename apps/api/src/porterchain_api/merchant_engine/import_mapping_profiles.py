"""Persist route-import column mappings on merchant.profile (no extra table)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant

_PROFILE_KEY = "route_import_mapping_profiles"


def list_profiles(merchant: Merchant) -> list[dict[str, Any]]:
    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    rows = profile.get(_PROFILE_KEY) or []
    return list(rows) if isinstance(rows, list) else []


def save_profile(
    db: Session,
    merchant: Merchant,
    *,
    name: str,
    headers: list[str],
    mapping: list[dict[str, Any]],
) -> dict[str, Any]:
    profile = dict(merchant.profile) if isinstance(merchant.profile, dict) else {}
    rows: list[dict[str, Any]] = list(profile.get(_PROFILE_KEY) or [])
    entry = {
        "id": str(uuid.uuid4()),
        "name": (name or "Saved mapping").strip()[:120],
        "headers": headers,
        "mapping": mapping,
        "created_at": datetime.now(UTC).isoformat(),
    }
    # replace same name
    rows = [r for r in rows if r.get("name") != entry["name"]]
    rows.insert(0, entry)
    profile[_PROFILE_KEY] = rows[:20]
    merchant.profile = profile
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return entry


def get_profile(merchant: Merchant, profile_id: str) -> dict[str, Any] | None:
    want = (profile_id or "").strip()
    if not want:
        return None
    for row in list_profiles(merchant):
        if str(row.get("id") or "") == want:
            return row
    return None


def find_matching_profile(merchant: Merchant, headers: list[str]) -> dict[str, Any] | None:
    """Return newest profile whose header set matches (order-insensitive)."""
    want = {h.lower().strip() for h in headers if h}
    for row in list_profiles(merchant):
        have = {str(h).lower().strip() for h in (row.get("headers") or []) if h}
        if have and have == want:
            return row
    return None
