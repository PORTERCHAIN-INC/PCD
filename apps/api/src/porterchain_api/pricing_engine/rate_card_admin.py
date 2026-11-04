"""Pricing admin use-cases (doc 72 §9): Standard rate card versions, org Custom pricing, audit.

DB access for ``routers/pricing_cards.py``. Errors surface as :class:`PricingAdminError`
(HTTP status + detail) so the router keeps its exact responses.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_api.pricing_engine.models import (
    PricingAudit,
    PricingOrgPricing,
    PricingRateCard,
    PricingRateCardVersion,
)
from porterchain_api.pricing_engine.smart_apply import three_model_preview
from porterchain_pricing.standard_card import (
    STANDARD_CODE,
    Item,
    ManualQuoteRequired,
    OrgPricing,
    diff_lines,
    quote,
    sample_basket_preview,
    standard_v1,
)


class PricingAdminError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def audit(
    db: Session, actor_id: str | None, entity: str, entity_id: str, action: str, diff: Any, reason: str | None = None
) -> None:
    db.add(PricingAudit(entity=entity, entity_id=entity_id, action=action, diff=diff, actor_id=actor_id, reason=reason))


def standard_card(db: Session) -> PricingRateCard:
    card = db.scalar(select(PricingRateCard).where(PricingRateCard.code == STANDARD_CODE))
    if card is None:
        card = PricingRateCard(code=STANDARD_CODE, name="PorterChain Standard", kind="standard")
        db.add(card)
        db.flush()
        db.add(
            PricingRateCardVersion(
                rate_card_id=card.id,
                version=1,
                status="published",
                lines=standard_v1(),
                effective_from=datetime.now(UTC),
                published_at=datetime.now(UTC),
                notes="Standard v1 (doc 72)",
            )
        )
        db.flush()
    return card


def versions(db: Session, card_id: str) -> list[PricingRateCardVersion]:
    return list(
        db.scalars(
            select(PricingRateCardVersion)
            .where(PricingRateCardVersion.rate_card_id == card_id)
            .order_by(PricingRateCardVersion.version.desc())
        )
    )


def published_lines(db: Session) -> dict[str, Any]:
    """Live Standard lines (falls back to the code default)."""
    card = standard_card(db)
    for v in versions(db, card.id):
        if v.status == "published":
            return v.lines
    return standard_v1()


def ver_out(v: PricingRateCardVersion) -> dict[str, Any]:
    return {
        "id": v.id,
        "version": v.version,
        "status": v.status,
        "notes": v.notes,
        "effective_from": v.effective_from.isoformat() if v.effective_from else None,
        "published_at": v.published_at.isoformat() if v.published_at else None,
    }


def get_standard(db: Session, *, can_edit: bool) -> dict[str, Any]:
    card = standard_card(db)
    vs = versions(db, card.id)
    live = next((v for v in vs if v.status == "published"), None)
    draft = next((v for v in vs if v.status == "draft"), None)
    db.commit()
    return {
        "code": card.code,
        "name": card.name,
        "published": ver_out(live) | {"lines": live.lines} if live else None,
        "draft": ver_out(draft) | {"lines": draft.lines} if draft else None,
        "versions": [ver_out(v) for v in vs],
        "can_edit": can_edit,
    }


def validate_lines(lines: dict[str, Any]) -> None:
    try:
        quote([Item(weight_kg=4, length_cm=40, width_cm=30, height_cm=20)], "Z1", lines=lines)
        sample_basket_preview(lines)
    except (KeyError, TypeError, ValueError) as exc:
        raise PricingAdminError(422, f"invalid_rate_card:{exc}") from exc


def save_draft(db: Session, actor_id: str | None, lines: dict[str, Any] | None, notes: str | None) -> dict[str, Any]:
    card = standard_card(db)
    vs = versions(db, card.id)
    draft = next((v for v in vs if v.status == "draft"), None)
    base = lines or copy.deepcopy(published_lines(db))
    validate_lines(base)
    if draft is None:
        draft = PricingRateCardVersion(
            rate_card_id=card.id, version=(vs[0].version + 1) if vs else 1, status="draft", lines=base
        )
        db.add(draft)
    else:
        draft.lines = base
    draft.notes = notes
    db.flush()
    audit(db, actor_id, "rate_card_version", draft.id, "draft_saved", diff_lines(published_lines(db), base))
    db.commit()
    return ver_out(draft) | {"lines": draft.lines}


def preview_lines(db: Session, lines: dict[str, Any] | None) -> dict[str, Any]:
    lines = lines or published_lines(db)
    validate_lines(lines)
    live = published_lines(db)
    db.commit()
    return {"rows": sample_basket_preview(lines), "live_rows": sample_basket_preview(live), "diff": diff_lines(live, lines)}


def publish(db: Session, actor_id: str | None, reason: str) -> dict[str, Any]:
    card = standard_card(db)
    vs = versions(db, card.id)
    draft = next((v for v in vs if v.status == "draft"), None)
    if draft is None:
        raise PricingAdminError(409, "no_draft")
    now = datetime.now(UTC)
    old = published_lines(db)
    for v in vs:
        if v.status == "published":
            v.status, v.effective_to = "retired", now
    draft.status, draft.published_at, draft.effective_from, draft.published_by = "published", now, now, actor_id
    audit(db, actor_id, "rate_card_version", draft.id, "published", diff_lines(old, draft.lines), reason)
    db.commit()
    return ver_out(draft)


def rollback(db: Session, actor_id: str | None, version: int, reason: str) -> dict[str, Any]:
    """Republish an older version's lines as a new version (history is never rewritten)."""
    card = standard_card(db)
    vs = versions(db, card.id)
    target = next((v for v in vs if v.version == version), None)
    if target is None:
        raise PricingAdminError(404, "version_not_found")
    now = datetime.now(UTC)
    old = published_lines(db)
    for v in vs:
        if v.status in ("published", "draft"):
            v.status, v.effective_to = "retired", now
    new = PricingRateCardVersion(
        rate_card_id=card.id,
        version=vs[0].version + 1,
        status="published",
        lines=copy.deepcopy(target.lines),
        published_at=now,
        effective_from=now,
        published_by=actor_id,
        notes=f"Rollback to v{target.version}",
    )
    db.add(new)
    db.flush()
    audit(db, actor_id, "rate_card_version", new.id, "rollback", diff_lines(old, new.lines), reason)
    db.commit()
    return ver_out(new)


def org_obj(row: PricingOrgPricing | None) -> OrgPricing:
    if row is None or row.mode != "custom":
        return OrgPricing()
    return OrgPricing(
        mode="custom",
        preset_pct=row.preset_pct,
        preset_per_stop_cents=row.preset_per_stop_cents,
        flat_parcel_cents=row.flat_parcel_cents,
        band_overrides=dict(row.band_overrides or {}),
    )


def org_pricing_obj(db: Session, org_id: str | None) -> OrgPricing | None:
    return org_obj(db.get(PricingOrgPricing, org_id)) if org_id else None


def org_out(org_id: str, row: PricingOrgPricing | None) -> dict[str, Any]:
    if row is None:
        return {
            "org_id": org_id,
            "mode": "standard",
            "preset_pct": None,
            "preset_per_stop_cents": None,
            "flat_parcel_cents": None,
            "band_overrides": {},
        }
    return {
        "org_id": org_id,
        "mode": row.mode,
        "preset_pct": row.preset_pct,
        "preset_per_stop_cents": row.preset_per_stop_cents,
        "flat_parcel_cents": row.flat_parcel_cents,
        "band_overrides": row.band_overrides or {},
        "contract_document_id": row.contract_document_id,
        "red_reason": row.red_reason,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


def body_org(body: Any) -> OrgPricing:
    if body.mode != "custom":
        return OrgPricing()
    return OrgPricing(
        mode="custom",
        preset_pct=body.preset_pct,
        preset_per_stop_cents=body.preset_per_stop_cents,
        flat_parcel_cents=body.flat_parcel_cents,
        band_overrides=body.band_overrides,
    )


def get_org(db: Session, org_id: str) -> dict[str, Any]:
    row = db.get(PricingOrgPricing, org_id)
    published_lines(db)
    db.commit()
    return org_out(org_id, row) | {"preview": three_model_preview(org_obj(row))}


def preview_org(db: Session, org_id: str, body: Any) -> dict[str, Any]:
    published_lines(db)
    db.commit()
    try:
        return {"org_id": org_id, "rows": three_model_preview(body_org(body))}
    except ValueError as exc:
        raise PricingAdminError(422, str(exc)) from exc


def put_org(db: Session, actor_id: str | None, org_id: str, body: Any) -> dict[str, Any]:
    published_lines(db)
    try:
        rows = three_model_preview(body_org(body))
    except ValueError as exc:
        raise PricingAdminError(422, str(exc)) from exc
    if body.mode == "custom" and body.band_overrides and not body.contract_document_id:
        raise PricingAdminError(422, "contract_required_for_overrides")
    row = db.get(PricingOrgPricing, org_id)
    before = org_out(org_id, row)
    if row is None:
        row = PricingOrgPricing(org_id=org_id)
        db.add(row)
    custom = body.mode == "custom"
    row.mode = body.mode
    row.preset_pct = body.preset_pct if custom else None
    row.preset_per_stop_cents = body.preset_per_stop_cents if custom else None
    row.flat_parcel_cents = body.flat_parcel_cents if custom else None
    row.band_overrides = body.band_overrides if custom else {}
    row.contract_document_id = body.contract_document_id
    row.red_reason = body.red_reason
    row.expires_at = body.expires_at
    row.effective_from = datetime.now(UTC)
    row.updated_by = actor_id
    db.flush()
    after = org_out(org_id, row)
    audit(db, actor_id, "org_pricing", org_id, "updated", diff_lines(before, after), body.reason)
    db.commit()
    return after | {"preview": rows}


def list_audit(db: Session, entity_id: str | None, limit: int) -> dict[str, Any]:
    q = select(PricingAudit).order_by(PricingAudit.created_at.desc()).limit(max(1, min(limit, 500)))
    if entity_id:
        q = q.where(PricingAudit.entity_id == entity_id)
    return {
        "items": [
            {
                "id": a.id,
                "entity": a.entity,
                "entity_id": a.entity_id,
                "action": a.action,
                "diff": a.diff,
                "actor_id": a.actor_id,
                "reason": a.reason,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in db.scalars(q)
        ]
    }


def standard_quote(db: Session, body: Any, items: list[Item]) -> dict[str, Any]:
    """Staff explainer: the one Standard price (plus the org's Custom view)."""
    lines = published_lines(db)
    org = org_pricing_obj(db, body.org_id)
    db.commit()
    try:
        return quote(
            items, body.zone, add_ons=body.add_ons, audience=body.audience, lines=lines, org=org, stops=body.stops
        )
    except ManualQuoteRequired as exc:
        raise PricingAdminError(422, f"manual_quote:{exc}") from exc
    except ValueError as exc:
        raise PricingAdminError(422, str(exc)) from exc
