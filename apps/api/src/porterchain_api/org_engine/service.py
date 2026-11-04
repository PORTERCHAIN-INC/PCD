"""Organisation service: provision, capabilities, versioned operating profile, external refs, backfill."""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from porterchain_api.org_engine import packs
from porterchain_api.org_engine.models import ExternalRef, OperatingProfile, Organisation, OrgCapability

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_public_id() -> str:
    return "ORG-" + "".join(secrets.choice(_CROCKFORD) for _ in range(6))


def provision(
    db: Session, *, display_name: str, business_type: str, subtype: str | None = None, org_id: str | None = None,
    legal_name: str | None = None, merchant_id: str | None = None, status: str = "lead", needs_review: bool = False,
) -> Organisation:
    bt = packs.business_type(business_type)
    caps = packs.default_capabilities(business_type, subtype)
    org = Organisation(
        id=org_id or merchant_id or secrets.token_hex(16), public_id=new_public_id(), display_name=display_name,
        legal_name=legal_name, business_type=business_type, subtype=subtype, role_flags=list(bt["roles"]),
        status=status, merchant_id=merchant_id, needs_review=needs_review,
    )
    db.add(org)
    db.flush()
    for cap in caps:
        db.add(OrgCapability(org_id=org.id, capability=cap, enabled=True, source="default"))
    set_profile(db, org.id, packs.default_profile(business_type))
    return org


def capabilities(db: Session, org_id: str) -> dict[str, bool]:
    rows = db.scalars(select(OrgCapability).where(OrgCapability.org_id == org_id))
    return {r.capability: r.enabled for r in rows}


def has_capability(db: Session, org_id: str, name: str) -> bool:
    return capabilities(db, org_id).get(name, False)


def set_capabilities(db: Session, org_id: str, changes: dict[str, bool], source: str = "ravi") -> dict[str, bool]:
    for name, enabled in changes.items():
        if name not in packs.CAPABILITIES:
            raise ValueError(f"unknown_capability:{name}")
        row = db.get(OrgCapability, (org_id, name))
        if row is None:
            db.add(OrgCapability(org_id=org_id, capability=name, enabled=bool(enabled), source=source))
        else:
            row.enabled, row.source = bool(enabled), source
    db.flush()
    return capabilities(db, org_id)


def current_profile(db: Session, org_id: str) -> OperatingProfile | None:
    return db.scalar(
        select(OperatingProfile).where(OperatingProfile.org_id == org_id).order_by(OperatingProfile.version.desc()).limit(1)
    )


def set_profile(db: Session, org_id: str, profile: dict[str, Any], actor: str | None = None) -> OperatingProfile:
    """Profile changes are versioned; orders keep the version they were created with."""
    base = profile_out(current_profile(db, org_id)) or {}
    merged = {**base, **{k: v for k, v in profile.items() if k != "version"}}
    packs.validate_profile(merged)
    last = db.scalar(select(func.max(OperatingProfile.version)).where(OperatingProfile.org_id == org_id)) or 0
    row = OperatingProfile(
        org_id=org_id, version=last + 1, pickup_mode=merged["pickup_mode"], pickup_params=merged.get("pickup_params"),
        tracking_mode=merged["tracking_mode"], label_mode=merged["label_mode"], relabel_rule=merged.get("relabel_rule"),
        barcode_formats=merged.get("barcode_formats"), ref_schema=merged.get("ref_schema"), created_by=actor,
    )
    db.add(row)
    db.flush()
    return row


def profile_out(p: OperatingProfile | None) -> dict[str, Any] | None:
    if p is None:
        return None
    return {
        "version": p.version, "pickup_mode": p.pickup_mode, "pickup_params": p.pickup_params,
        "tracking_mode": p.tracking_mode, "label_mode": p.label_mode, "relabel_rule": p.relabel_rule,
        "barcode_formats": p.barcode_formats, "ref_schema": p.ref_schema,
    }


def upsert_external_ref(
    db: Session, *, org_id: str, ref_type: str, ref_value: str, entity_type: str, entity_id: str, source: str = "api",
) -> ExternalRef:
    """Idempotent: (org, type, value) is unique; replay returns the existing mapping."""
    if ref_type not in packs.REF_TYPES:
        raise ValueError(f"invalid_ref_type:{ref_type}")
    value = ref_value.strip()
    row = db.scalar(
        select(ExternalRef).where(ExternalRef.org_id == org_id, ExternalRef.ref_type == ref_type, ExternalRef.ref_value == value)
    )
    if row is not None:
        return row
    row = ExternalRef(org_id=org_id, ref_type=ref_type, ref_value=value, entity_type=entity_type, entity_id=entity_id, source=source)
    db.add(row)
    db.flush()
    return row


def org_out(db: Session, org: Organisation) -> dict[str, Any]:
    return {
        "id": org.id, "public_id": org.public_id, "display_name": org.display_name, "legal_name": org.legal_name,
        "business_type": org.business_type, "subtype": org.subtype, "role_flags": org.role_flags, "status": org.status,
        "locale": org.locale, "merchant_id": org.merchant_id, "needs_review": org.needs_review,
        "capabilities": capabilities(db, org.id), "profile": profile_out(current_profile(db, org.id)),
        "documents": packs.documents_for(org.business_type, org.subtype),
    }


_MERCHANT_STATUS = {"active": "active", "suspended": "suspended", "pending": "trial", "closed": "offboarded"}


def backfill_from_merchants(db: Session, *, dry_run: bool = True) -> dict[str, Any]:
    """Doc 70 §6 step 2: every merchant → organisation with the same id (FKs stay valid).

    Shopify-connected merchants become ``shopify_merchant``; the rest ``small_shop``/``other``
    flagged ``needs_review`` for Ravi's one-page review. Re-running is a no-op.
    """
    from porterchain_api.platform.engine_ports.merchant_engine__lookups import merchants_by_created, shopify_merchant_ids

    existing = set(db.scalars(select(Organisation.merchant_id).where(Organisation.merchant_id.is_not(None))))
    shopify = shopify_merchant_ids(db)
    created: list[dict[str, Any]] = []
    for m in merchants_by_created(db):
        if m.id in existing:
            continue
        is_shop = m.id in shopify
        plan = {
            "merchant_id": m.id, "display_name": m.company_name,
            "business_type": "shopify_merchant" if is_shop else "small_shop",
            "subtype": None if is_shop else "other", "needs_review": not is_shop,
        }
        created.append(plan)
        if not dry_run:
            provision(
                db, display_name=m.company_name, legal_name=m.legal_name, business_type=plan["business_type"],
                subtype=plan["subtype"], merchant_id=m.id, needs_review=plan["needs_review"],
                status=_MERCHANT_STATUS.get(str(m.status).lower(), "lead"),
            )
            org = db.get(Organisation, m.id)
            if org is not None and m.hst_number:
                org.gst_hst_number = m.hst_number
    if not dry_run:
        db.flush()
    return {"dry_run": dry_run, "count": len(created), "orgs": created}


def ensure_org_for_shopify(db: Session, merchant: Any, shop_domain: str | None = None) -> Organisation:
    """Doc 70: a Shopify install always has an organisation (same id as the merchant).

    Existing org: keep its type, just switch the ``shopify_app`` capability on. New:
    ``shopify_merchant`` with the pack defaults. Idempotent; never touches pricing.
    """
    org = db.scalar(select(Organisation).where(Organisation.merchant_id == merchant.id)) or db.get(Organisation, merchant.id)
    if org is None:
        org = provision(
            db, display_name=merchant.company_name or shop_domain or "Shopify store", legal_name=getattr(merchant, "legal_name", None),
            business_type="shopify_merchant", merchant_id=merchant.id,
            status=_MERCHANT_STATUS.get(str(merchant.status).lower(), "trial"),
        )
    elif org.merchant_id is None:
        org.merchant_id = merchant.id
    if not capabilities(db, org.id).get("shopify_app"):
        set_capabilities(db, org.id, {"shopify_app": True}, source="shopify_install")
    db.flush()
    return org


def ensure_org_for_shopify_safe(db: Session, merchant: Any, shop_domain: str | None = None) -> None:
    """Install hook: never let org provisioning break a Shopify install."""
    import logging

    try:
        with db.begin_nested():
            ensure_org_for_shopify(db, merchant, shop_domain)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("org auto-provision failed merchant=%s", getattr(merchant, "id", None))
