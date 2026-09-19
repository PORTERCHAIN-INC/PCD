"""Clerk directory merge for the settings center.

Kept out of settings_service so that module can shrink. Labels stay in the service.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from porterchain_api.admin_engine.clerk_directory_service import fetch_clerk_snapshots
from porterchain_api.auth.clerk_client import ClerkUserSnapshot
from porterchain_api.config import Settings
from porterchain_api.schemas_admin import PlatformUserItem

logger = logging.getLogger(__name__)


def _access_status_label(access_status: str, invite_status: str, identity_status: str) -> str:
    from porterchain_api.admin_engine.settings_service import _status_label

    return _status_label(access_status, invite_status, identity_status)


def _enrich_with_clerk(item: PlatformUserItem, snap: ClerkUserSnapshot | None) -> PlatformUserItem:
    if not snap:
        return item
    invite = "accepted" if snap.clerk_user_id else item.invite_status
    identity = "registered"
    access = item.access_status
    if snap.banned:
        access = "suspended"
    name = item.name
    if not name and (snap.first_name or snap.last_name):
        name = " ".join(p for p in (snap.first_name, snap.last_name) if p)
    label = _access_status_label(access, invite, identity)
    if snap.clerk_status == "banned":
        label = f"{label} · Banned in Clerk"
    elif not snap.password_set and item.provisioned:
        label = f"{label} · Password not set"
    return item.model_copy(
        update={
            "clerk_user_id": snap.clerk_user_id,
            "clerk_linked": True,
            "clerk_status": snap.clerk_status,
            "clerk_email_verified": snap.email_verified,
            "clerk_password_set": snap.password_set,
            "clerk_last_sign_in_at": snap.last_sign_in_at,
            "invite_status": invite,
            "identity_status": identity,
            "access_status": access,
            "status_label": label,
            "name": name,
            "created_at": snap.created_at or item.created_at,
        }
    )


def _mark_not_in_clerk(item: PlatformUserItem) -> PlatformUserItem:
    """Seat exists in PorterChain but is absent from the live Clerk directory."""
    cid = item.clerk_user_id or ""
    if cid.startswith("pending") or item.invite_status == "invite_pending":
        identity = "invite_pending"
    else:
        identity = "not_registered"
    label = _access_status_label(item.access_status, item.invite_status, identity)
    if identity == "not_registered":
        label = f"{label} · Not in Clerk"
    return item.model_copy(
        update={
            "clerk_linked": False,
            "clerk_status": None,
            "identity_status": identity,
            "status_label": label,
        }
    )


def _merge_clerk_directory(
    items: list[PlatformUserItem],
    settings: Settings,
    user_type: str,
    *,
    limit: int,
    search: str | None,
    include_unprovisioned: bool = False,
    keep_unlinked: bool = True,
) -> tuple[list[PlatformUserItem], bool, int]:
    """Enrich PorterChain directory rows with live Clerk snapshots.

    PorterChain DB is the visibility SoT — **one row per DB persona** (no email
    collapse). Clerk enrich is additive. When Clerk is down or empty, rows stay
    visible with honest ``not_registered`` / Not-in-Clerk labels.

    ``include_unprovisioned``: also inject Clerk-only orphans (no PorterChain seat).
    Staff never enters this path (Staff IdP directory).
    """
    _ = keep_unlinked  # retained for callers; DB visibility is always on
    if user_type == "staff":
        raise ValueError("staff_directory_is_staff_idp_not_clerk")
    try:
        snaps = fetch_clerk_snapshots(settings, user_type, limit=limit, query=search)
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("clerk_directory_sync_failed keep_db_rows", exc_info=True)
        return [_mark_not_in_clerk(i) for i in items], False, 0

    snaps = snaps or {}
    by_clerk_id: dict[str, Any] = {
        s.clerk_user_id: s for s in snaps.values() if getattr(s, "clerk_user_id", None)
    }

    merged: list[PlatformUserItem] = []
    for item in items:
        email = (item.email or "").lower().strip()
        snap = snaps.get(email) if email else None
        if not snap and item.clerk_user_id:
            snap = by_clerk_id.get(item.clerk_user_id)
        if snap:
            merged.append(_enrich_with_clerk(item, snap))
        else:
            merged.append(_mark_not_in_clerk(item))

    seen = {(i.email or "").lower() for i in merged if i.email}

    if include_unprovisioned and snaps:
        for email, snap in snaps.items():
            if email in seen:
                continue
            access = "not_authorized"
            invite = "not_invited"
            identity = "registered"
            name = " ".join(p for p in (snap.first_name, snap.last_name) if p) or email.split("@")[0]
            label = f"{_access_status_label(access, invite, identity)} · Clerk only · no PorterChain seat"
            merged.append(
                PlatformUserItem(
                    id=f"clerk:{snap.clerk_user_id}",
                    user_type=user_type,
                    email=email,
                    name=name,
                    role=user_type if user_type != "staff" else None,
                    status=None,
                    access_status=access,
                    invite_status=invite,
                    identity_status=identity,
                    status_label=label,
                    clerk_linked=True,
                    clerk_user_id=snap.clerk_user_id,
                    provisioned=False,
                    clerk_status=snap.clerk_status,
                    clerk_email_verified=snap.email_verified,
                    clerk_password_set=snap.password_set,
                    clerk_last_sign_in_at=snap.last_sign_in_at,
                    detail_href=(
                        "/merchants"
                        if user_type == "merchant"
                        else ("/drivers" if user_type == "driver" else None)
                    ),
                    created_at=snap.created_at or datetime.now(UTC),
                )
            )
    merged.sort(key=lambda i: i.created_at or datetime.min.replace(tzinfo=UTC), reverse=True)
    return merged, True, len(snaps)

