"""Who may change a merchant's money terms, and the change history they leave."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.admin_states import AdminRole

#: Per-merchant pricing, contracts and credit: admin, super admin, finance.
MONEY_EDIT_ROLES = frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.FINANCE})
#: Vault documents may hold IDs / tax numbers: tighter read set, every read is logged.
DOCUMENT_READ_ROLES = frozenset(
    {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.FINANCE, AdminRole.COMPLIANCE}
)
DOCUMENT_DELETE_ROLES = frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.COMPLIANCE})

MONEY_EDIT_FORBIDDEN = "merchant_money_edit_forbidden"
HISTORY_RESOURCES = ("pricing", "contract", "credit", "api_key", "document", "owner", "segments")


def _role(ctx: Any) -> AdminRole | None:
    role = getattr(ctx, "role", None)
    if isinstance(role, AdminRole):
        return role
    try:
        return AdminRole(str(role))
    except ValueError:
        return None


def can_edit_money(ctx: Any) -> bool:
    return _role(ctx) in MONEY_EDIT_ROLES


def assert_money_editor(ctx: Any) -> None:
    if not can_edit_money(ctx):
        raise PermissionError(MONEY_EDIT_FORBIDDEN)


def assert_role(ctx: Any, allowed: frozenset[AdminRole], code: str) -> None:
    if _role(ctx) not in allowed:
        raise PermissionError(code)


def dict_diff(old: dict | None, new: dict | None) -> dict[str, dict[str, Any]]:
    """Top-level keys that changed: {key: {"old": .., "new": ..}}."""
    old = old or {}
    new = new or {}
    out: dict[str, dict[str, Any]] = {}
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            out[key] = {"old": old.get(key), "new": new.get(key)}
    return out


def change_history(db: Session, merchant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    from porterchain_api.merchant_models import MerchantAuditLog

    rows = (
        db.query(MerchantAuditLog)
        .filter(
            MerchantAuditLog.merchant_id == merchant_id,
            MerchantAuditLog.resource_type.in_(HISTORY_RESOURCES),
        )
        .order_by(MerchantAuditLog.created_at.desc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    out = []
    for row in rows:
        payload = dict(row.payload or {})
        changes = payload.get("changes")
        if changes is None and ("old" in payload or "new" in payload):
            old, new = payload.get("old"), payload.get("new")
            changes = dict_diff(old, new) if isinstance(old, dict) and isinstance(new, dict) else {
                "value": {"old": old, "new": new}
            }
        out.append(
            {
                "id": row.id,
                "at": row.created_at.isoformat() if row.created_at else None,
                "action": row.action,
                "area": row.resource_type,
                "actor": payload.get("admin_email") or row.actor_user_id,
                "actor_role": payload.get("admin_role"),
                "reason": payload.get("reason"),
                "changes": changes or {},
            }
        )
    return out
