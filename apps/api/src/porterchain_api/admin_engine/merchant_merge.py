"""Duplicate-merchant review queue + Merge tool (with undo).

Merge moves every row that points at the source merchant (any table with a
``merchant_id`` column: users, Shopify stores, bookings, documents, invoices,
FSA rates, addresses, CRM, ...) to the target, records the moved row ids, and
soft-deletes the source. Undo moves exactly those rows back and restores it.
Audit-log rows stay where they were written (history); each step adds new ones.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant, MerchantAuditLog, MerchantMerge

KEEP_ON_SOURCE = {"merchant_audit_logs", "merchant_merges"}


def _actor(ctx: Any) -> str:
    user = getattr(ctx, "user", None)
    return f"admin:{getattr(user, 'id', 'unknown')}"


def _audit(db: Session, merchant_id: str, actor: str, action: str, payload: dict) -> None:
    db.add(MerchantAuditLog(merchant_id=merchant_id, actor_user_id=actor, action=action,
                            resource_type="merchant", resource_id=None, payload=payload))


def _merchant_tables(db: Session) -> list[str]:
    rows = db.execute(text(
        "SELECT c.table_name FROM information_schema.columns c "
        "JOIN information_schema.columns i ON i.table_name=c.table_name AND i.table_schema=c.table_schema AND i.column_name='id' "
        "JOIN information_schema.tables t ON t.table_name=c.table_name AND t.table_schema=c.table_schema AND t.table_type='BASE TABLE' "
        "WHERE c.table_schema=current_schema() AND c.column_name='merchant_id' ORDER BY 1"
    )).scalars().all()
    return [r for r in rows if r not in KEEP_ON_SOURCE]


def _live(db: Session, merchant_id: str) -> Merchant:
    m = db.get(Merchant, merchant_id)
    if m is None or m.deleted_at is not None:
        raise LookupError("merchant_not_found")
    return m


# ---------- review queue ----------

def list_duplicate_queue(db: Session) -> list[dict]:
    out = []
    for m in db.query(Merchant).filter(Merchant.deleted_at.is_(None)).all():
        dup = (m.profile or {}).get("possible_duplicate_of")
        if not isinstance(dup, dict) or dup.get("status") != "open":
            continue
        other = db.get(Merchant, dup.get("merchant_id"))
        if other is None or other.deleted_at is not None:
            continue
        out.append({
            "merchant_id": m.id, "company_name": m.company_name, "email": m.email,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "match_merchant_id": other.id, "match_company_name": other.company_name,
            "match_email": other.email, "score": dup.get("score"), "reasons": dup.get("reasons", []),
            "source": dup.get("source"), "preview": merge_preview(db, m.id, other.id),
        })
    return sorted(out, key=lambda r: -(r["score"] or 0))


def keep_separate(db: Session, ctx: Any, merchant_id: str) -> dict:
    m = _live(db, merchant_id)
    prof = dict(m.profile or {})
    dup = dict(prof.get("possible_duplicate_of") or {})
    if not dup:
        raise ValueError("no_duplicate_flag")
    dup.update(status="dismissed", reviewed_by=_actor(ctx), reviewed_at=datetime.now(UTC).isoformat())
    prof["possible_duplicate_of"] = dup
    m.profile = prof
    _audit(db, m.id, _actor(ctx), "merchant.duplicate_kept_separate", {"other": dup.get("merchant_id")})
    db.commit()
    return {"merchant_id": m.id, "status": "dismissed"}


# ---------- merge ----------

def merge_preview(db: Session, source_id: str, target_id: str) -> dict[str, int]:
    counts = {}
    for t in _merchant_tables(db):
        n = db.execute(text(f'SELECT count(*) FROM "{t}" WHERE merchant_id = :s'), {"s": source_id}).scalar()
        if n:
            counts[t] = int(n)
    return counts


def merge_merchants(db: Session, ctx: Any, source_id: str, target_id: str) -> dict:
    if source_id == target_id:
        raise ValueError("merge_same_merchant")
    source, target = _live(db, source_id), _live(db, target_id)
    moved: dict[str, list[str]] = {}
    try:
        for t in _merchant_tables(db):
            ids = db.execute(
                text(f'UPDATE "{t}" SET merchant_id = :t WHERE merchant_id = :s RETURNING id'),
                {"s": source_id, "t": target_id},
            ).scalars().all()
            if ids:
                moved[t] = [str(i) for i in ids]
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(f"merge_conflict: {exc.orig}") from exc
    now = datetime.now(UTC)
    prof = dict(source.profile or {})
    prof["merged_into"] = target_id
    if isinstance(prof.get("possible_duplicate_of"), dict):
        prof["possible_duplicate_of"] = {**prof["possible_duplicate_of"], "status": "merged"}
    source.profile = prof
    source.deleted_at = now
    source.delete_reason = f"merged into {target_id}"
    rec = MerchantMerge(source_merchant_id=source_id, target_merchant_id=target_id, actor=_actor(ctx), moved=moved)
    db.add(rec)
    db.flush()
    summary = {t: len(v) for t, v in moved.items()}
    for mid in (source_id, target_id):
        _audit(db, mid, _actor(ctx), "merchant.merged",
               {"merge_id": rec.id, "source": source_id, "target": target_id, "moved": summary})
    db.commit()
    return {"merge_id": rec.id, "moved": summary, "target_company": target.company_name}


def undo_merge(db: Session, ctx: Any, merge_id: str) -> dict:
    rec = db.get(MerchantMerge, merge_id)
    if rec is None:
        raise LookupError("merge_not_found")
    if rec.status != "merged":
        raise ValueError("merge_already_undone")
    for t, ids in (rec.moved or {}).items():
        if ids:
            db.execute(text(f'UPDATE "{t}" SET merchant_id = :s WHERE id::text = ANY(:ids)'),
                       {"s": rec.source_merchant_id, "ids": list(ids)})
    source = (
        db.query(Merchant).execution_options(include_deleted=True)
        .filter(Merchant.id == rec.source_merchant_id).first()
    )
    if source is not None:
        prof = dict(source.profile or {})
        prof.pop("merged_into", None)
        source.profile = prof
        source.deleted_at = None
        source.delete_reason = None
    rec.status, rec.undone_at = "undone", datetime.now(UTC)
    for mid in (rec.source_merchant_id, rec.target_merchant_id):
        _audit(db, mid, _actor(ctx), "merchant.merge_undone", {"merge_id": rec.id})
    db.commit()
    return {"merge_id": rec.id, "status": "undone"}
