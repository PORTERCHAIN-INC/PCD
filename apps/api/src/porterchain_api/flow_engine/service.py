"""DB adapter: build pickup + delivery flow specs for a driver job (doc 82 §1.1)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_api.flow_engine import flow_spec as fs

_FLAG_KEYS = ("bol_required", "pallets", "customs", "rx", "cold_chain", "dangerous_goods", "packing_slip",
              "signature_required", "dolly", "bulk_api", "age_restricted", "sealed", "temp_range_c", "failed",
              "customs_released", "signed_handover")


def flags_for(order: Any) -> dict[str, Any]:
    meta = dict(getattr(order, "compliance_metadata", None) or {})
    flags = {k: meta[k] for k in _FLAG_KEYS if k in meta}
    if str(getattr(order, "status", "") or "").lower() in ("failed", "delivery_failed", "returned"):
        flags["failed"] = True
    return flags


def flow_specs_for_order(db: Session, order: Any) -> dict[str, Any]:
    from porterchain_api.org_engine import packs
    from porterchain_api.org_engine.models import OperatingProfile, Organisation

    flags = flags_for(order)
    code, subtype, pickup_mode = "retail_customer", None, "on_demand"
    org = None
    if getattr(order, "merchant_id", None):
        org = db.execute(select(Organisation).where(Organisation.merchant_id == order.merchant_id)).scalar_one_or_none()
    if org is not None:
        code, subtype = org.business_type, org.subtype
        prof = db.execute(select(OperatingProfile).where(OperatingProfile.org_id == org.id)
                          .order_by(OperatingProfile.version.desc())).scalars().first()
        pickup_mode = prof.pickup_mode if prof else packs.default_profile(code)["pickup_mode"]
    elif getattr(order, "merchant_id", None):
        code, pickup_mode = "shopify_merchant", "scheduled_daily"
    try:
        matrix = packs.documents_for(code, subtype)
    except ValueError:
        matrix = {"pod": "A"}
    docs = fs.active_documents(matrix, flags)
    gvwr = (flags.get("vehicle_gvwr_kg") if isinstance(flags.get("vehicle_gvwr_kg"), int) else None)
    multi = len(getattr(order, "stops", None) or []) > 2
    from porterchain_api.job_docs.rules import required_pickup_docs
    pickup = fs.with_pickup_docs(fs.pickup_flow(pickup_mode, vehicle_gvwr_kg=gvwr, multi_stop=multi),
                                 required_pickup_docs(docs, flags))
    return {"documents": sorted(docs), "pickup_docs": pickup.get("pickup_docs", []),
            "pickup": pickup,
            "delivery": fs.delivery_flow(docs, flags)}
