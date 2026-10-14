"""Soft-delete actions: delete, restore (whole batch), purge, retention, auto-purge."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import SystemConfig
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.platform.soft_delete import DeletedBatch, including_deleted
from porterchain_api.soft_delete.registry import (
    DEFAULT_RETENTION_DAYS,
    NEVER_DELETE,
    REGISTRY,
    RETENTION_KEY,
    TABLE_TO_KEY,
    Blocked,
    Entity,
    _get_any,
    _hard_delete,
)


# ── permissions ─────────────────────────────────────────────────────────────────


def can_delete(ctx: AdminContext) -> bool:
    return ctx.role in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN)


def can_purge(ctx: AdminContext) -> bool:
    return ctx.role == AdminRole.SUPER_ADMIN


def _require(ok: bool, msg: str) -> None:
    if not ok:
        raise PermissionError(msg)


# ── settings ────────────────────────────────────────────────────────────────────


def retention_days(db: Session) -> int:
    row = db.get(SystemConfig, RETENTION_KEY)
    try:
        days = int((row.value or {}).get("retention_days", DEFAULT_RETENTION_DAYS)) if row else DEFAULT_RETENTION_DAYS
    except (TypeError, ValueError):
        days = DEFAULT_RETENTION_DAYS
    return max(0, min(days, 3650))


def set_retention_days(db: Session, ctx: AdminContext, days: int) -> int:
    _require(can_purge(ctx), "Only a super admin can change how long deleted items are kept.")
    if days < 1 or days > 3650:
        raise Blocked("Keep deleted items between 1 and 3650 days.", "bad_retention")
    row = db.get(SystemConfig, RETENTION_KEY)
    if row is None:
        row = SystemConfig(key=RETENTION_KEY, value={})
        db.add(row)
    row.value = {**(row.value or {}), "retention_days": days}
    log_admin_audit(db, ctx, action="settings.deleted_items_retention", resource_type="system_config",
                    resource_id=RETENTION_KEY, payload={"retention_days": days})
    return days


# ── actions ─────────────────────────────────────────────────────────────────────


def entity(key: str) -> Entity:
    if key in NEVER_DELETE or key in {"invoice", "payment", "audit_log", "credit_note", "payout"}:
        raise Blocked("Finance and audit records can't be deleted. Void or archive them instead.", "never_delete")
    try:
        return REGISTRY[key]
    except KeyError as exc:
        raise Blocked(f"{key} can't be deleted here.", "unknown_entity") from exc


def check(db: Session, key: str, row_id: str) -> dict[str, Any]:
    """Dry run used by the Delete button: tells the admin what will happen before they click."""
    ent = entity(key)
    row = db.get(ent.model, row_id)
    if row is None or row.deleted_at is not None:
        raise LookupError(f"{key}_not_found")
    blocked = ent.guard_delete(db, row) if ent.guard_delete else None
    kids = ent.children(db, row) if ent.children else []
    counts: dict[str, int] = {}
    for k in kids:
        name = TABLE_TO_KEY.get(k.__tablename__, k.__tablename__)
        counts[name] = counts.get(name, 0) + 1
    return {"entity": key, "id": row_id, "label": ent.label(row), "allowed": blocked is None, "reason": blocked,
            "cascade": counts}


def soft_delete(db: Session, ctx: AdminContext, key: str, row_id: str, *, reason: str | None = None) -> DeletedBatch:
    _require(can_delete(ctx), "Only admins can delete.")
    ent = entity(key)
    row = db.get(ent.model, row_id)
    if row is None or row.deleted_at is not None:
        raise LookupError(f"{key}_not_found")
    if ent.guard_delete and (why := ent.guard_delete(db, row)):
        raise Blocked(why)
    now = datetime.now(UTC)
    kids = [k for k in (ent.children(db, row) if ent.children else []) if k.deleted_at is None]
    batch = DeletedBatch(entity=key, root_id=row.id, label=ent.label(row)[:255], reason=(reason or "").strip()[:500] or None,
                         deleted_by=ctx.user.id, deleted_by_email=ctx.user.email, deleted_at=now,
                         purge_after=now + timedelta(days=retention_days(db)),
                         children=[{"entity": TABLE_TO_KEY.get(k.__tablename__, k.__tablename__), "id": k.id} for k in kids],
                         side_effects=ent.side_effects(db, row) if ent.side_effects else {})
    db.add(batch)
    db.flush()
    for r in (row, *kids):
        r.deleted_at, r.deleted_by, r.delete_reason, r.delete_batch_id = now, ctx.user.id, batch.reason, batch.id
    log_admin_audit(db, ctx, action="soft_delete.delete", resource_type=key, resource_id=row.id,
                    payload={"batch_id": batch.id, "label": batch.label, "children": len(kids), "reason": batch.reason})
    db.flush()
    return batch


def _batch(db: Session, batch_id: str) -> DeletedBatch:
    b = db.get(DeletedBatch, batch_id)
    if b is None:
        raise LookupError("batch_not_found")
    if b.state != "deleted":
        raise Blocked(f"This item was already {b.state}.", "already_closed")
    return b


def _batch_rows(db: Session, b: DeletedBatch) -> tuple[Entity, Any, list[Any]]:
    ent = REGISTRY[b.entity]
    with including_deleted(db):
        root = _get_any(db, ent.model, b.root_id)
        kids = []
        for c in b.children or []:
            ce = REGISTRY.get(c["entity"])
            if ce is not None and (k := _get_any(db, ce.model, c["id"])) is not None:
                kids.append(k)
    return ent, root, kids


def restore(db: Session, ctx: AdminContext, batch_id: str) -> DeletedBatch:
    _require(can_delete(ctx), "Only admins can restore.")
    b = _batch(db, batch_id)
    ent, root, kids = _batch_rows(db, b)
    if root is None:
        raise Blocked("The original record no longer exists.", "missing")
    if ent.parent and (p := ent.parent(db, root)) and p[1] is not None and p[1].deleted_at is not None:
        raise Blocked(f"Its {p[0]} is deleted too. Restore the {p[0]} first.", "parent_deleted")
    for r in (root, *kids):
        if r.delete_batch_id == b.id:
            r.deleted_at = r.deleted_by = r.delete_reason = r.delete_batch_id = None
    if ent.restore_side_effects:
        ent.restore_side_effects(db, b.side_effects or {})
    b.state, b.closed_at, b.closed_by = "restored", datetime.now(UTC), ctx.user.id
    log_admin_audit(db, ctx, action="soft_delete.restore", resource_type=b.entity, resource_id=b.root_id,
                    payload={"batch_id": b.id, "label": b.label, "children": len(kids)})
    db.flush()
    return b


def purge(db: Session, ctx: AdminContext | None, batch_id: str, *, confirm: str | None, auto: bool = False) -> DeletedBatch:
    """Permanent delete. Super admin + typed confirm, or the auto-purge job (``ctx=None, auto=True``)."""
    if not auto:
        _require(ctx is not None and can_purge(ctx), "Only a super admin can delete permanently.")
    b = _batch(db, batch_id)
    if not auto and (confirm or "").strip() != b.label.strip():
        raise Blocked(f'Type "{b.label}" exactly to confirm.', "confirm_mismatch")
    ent, root, kids = _batch_rows(db, b)
    if root is None:
        raise Blocked("The original record no longer exists.", "missing")
    if ent.guard_purge and (why := ent.guard_purge(db, root)):
        raise Blocked(why, "archive_only")
    actor = ctx or _system_ctx()
    with including_deleted(db):
        outcome = ent.purge(db, root, actor) if ent.purge else _hard_delete(db, root, [k for k in kids if k.delete_batch_id == b.id], actor)
    b.state, b.closed_at, b.closed_by = "purged", datetime.now(UTC), (ctx.user.id if ctx else "system:auto_purge")
    b.outcome = outcome
    log_admin_audit(db, ctx, action="soft_delete.purge", resource_type=b.entity, resource_id=b.root_id,
                    payload={"batch_id": b.id, "label": b.label, "auto": auto, "outcome": outcome.get("mode")})
    return b


def _system_ctx() -> AdminContext:
    from porterchain_api.admin_models import AdminUser

    return AdminContext(user=AdminUser(id="system:auto_purge", clerk_user_id="system:auto_purge",
                                       email="auto-purge@porterchain.local", role="super_admin"),
                        role=AdminRole.SUPER_ADMIN)


def list_batches(db: Session, *, entity_key: str | None = None, q: str | None = None, state: str = "deleted",
                 limit: int = 200) -> list[dict[str, Any]]:
    stmt = select(DeletedBatch).where(DeletedBatch.state == state).order_by(DeletedBatch.deleted_at.desc()).limit(limit)
    if entity_key:
        stmt = stmt.where(DeletedBatch.entity == entity_key)
    if q:
        stmt = stmt.where(DeletedBatch.label.ilike(f"%{q.strip()}%"))
    return [batch_out(b) for b in db.scalars(stmt)]


def batch_out(b: DeletedBatch) -> dict[str, Any]:
    ent = REGISTRY.get(b.entity)
    return {"id": b.id, "entity": b.entity, "entity_title": ent.title if ent else b.entity, "root_id": b.root_id,
            "label": b.label, "reason": b.reason, "deleted_by": b.deleted_by_email or b.deleted_by,
            "deleted_at": b.deleted_at.isoformat() if b.deleted_at else None,
            "purge_after": b.purge_after.isoformat() if b.purge_after else None,
            "children": len(b.children or []), "state": b.state, "outcome": b.outcome or {}}


def auto_purge(db: Session, *, now: datetime | None = None, limit: int = 100) -> dict[str, int]:
    """Worker job: permanently delete batches past ``purge_after``. Guarded items stay archived."""
    now = now or datetime.now(UTC)
    due = list(db.scalars(select(DeletedBatch).where(DeletedBatch.state == "deleted", DeletedBatch.purge_after <= now)
                          .order_by(DeletedBatch.purge_after).limit(limit)))
    out = {"scanned": len(due), "purged": 0, "kept": 0}
    for b in due:
        try:
            purge(db, None, b.id, confirm=None, auto=True)
            db.commit()
            out["purged"] += 1
        except Blocked as exc:
            db.rollback()
            b = db.get(DeletedBatch, b.id)
            b.purge_after = None  # archive-only: never retry, stays restorable
            b.outcome = {"mode": "kept", "reason": exc.reason}
            db.commit()
            out["kept"] += 1
    return out
