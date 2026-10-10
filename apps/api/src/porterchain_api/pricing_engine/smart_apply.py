"""Route pricing for opted-in merchants: one hook for every merchant price path.

Booking, quotes, CSV import and Shopify checkout rates all call
``PricingService.calculate_merchant``. For a merchant who opted in (Settings or the
merchant-portal banner), the route portion of that breakdown is replaced by the smart
route price (optimized sequence, marginal stops, cost floor); add-ons such as liftgate,
coverage and waiting stay as they were. Merchants who have not opted in keep the exact
existing price. Any smart-engine failure or custom-quote case falls back to the old price.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_pricing import PricingRequest, PricingService
from porterchain_pricing.types import PriceBreakdown, PriceLineItem

logger = logging.getLogger(__name__)

# Charges that sit on top of the route price and are kept as-is.
ADDON_CODES = frozenset({"liftgate", "coverage_upgrade", "past_designated_point", "wait"})
SAMPLE_FSAS = ("M5V", "L4Z", "L6H")


class SmartAwarePricingService(PricingService):
    def __init__(self, db: Session, **kw: Any) -> None:
        super().__init__(**kw)
        self._db = db

    def calculate_merchant_legacy(self, request: PricingRequest) -> PriceBreakdown:
        return super().calculate_merchant(request)

    def calculate_merchant(self, request: PricingRequest) -> PriceBreakdown:
        base = super().calculate_merchant(request)
        try:
            return apply_smart(self._db, request, base)
        except Exception:  # noqa: BLE001 - never break booking on the new engine
            logger.exception("smart route pricing failed; using existing price")
            return base


def _points(request: PricingRequest) -> tuple[list[Any], list[Any]] | None:
    drops = [request.dropoff, *(request.additional_stops or [])]
    pts = [request.pickup, *drops]
    if any(getattr(p, "lat", None) is None or getattr(p, "lng", None) is None for p in pts):
        return None
    return [request.pickup], drops


def apply_smart(db: Session, request: PricingRequest, base: PriceBreakdown) -> PriceBreakdown:
    from porterchain_api.merchant_models import Merchant
    from porterchain_api.pricing_engine.smart_pricing import merchant_opted_in, quote_route

    if not request.merchant_id or base.final_cents <= 0:
        return base
    merchant = db.get(Merchant, request.merchant_id)
    if merchant is None or not merchant_opted_in(db, merchant):
        return base
    pts = _points(request)
    if pts is None:
        return base
    smart = quote_route(db, pickups=pts[0], drops=pts[1], vehicle_class=request.vehicle_class,
                        merchant_id=request.merchant_id)
    if smart.get("custom_quote") or not smart.get("total_cents"):
        return base
    addons = [i for i in base.items if i.code in ADDON_CODES]
    old_sub = base.subtotal_cents or 1
    out = replace(base, items=[PriceLineItem(code="route_price", label=f"Route price ({smart['shape']})",
                                             amount_cents=int(smart["total_cents"])), *addons],
                  metadata={**base.metadata})
    out.finalize()
    if base.tax_cents:
        out.tax_cents = round(base.tax_cents * out.subtotal_cents / old_sub)
        out.final_cents = max(0, out.subtotal_cents + out.tax_cents)
    out.metadata["smart_pricing"] = {
        "applied": True,
        "previous_final_cents": base.final_cents,
        "route_km": smart.get("route_km"),
        "confidence": smart.get("confidence"),
        "matrix_source": smart.get("matrix_source"),
    }
    out.metadata["price_version"] = "smart_route_v1"
    return out


# --- merchant opt-in (portal banner / Shopify embedded app) ---------------------------


def opt_in_state(merchant: Any) -> dict[str, Any]:
    own = ((merchant.pricing_config or {}).get("smart_pricing") or {})
    return {"opted_in": bool(own.get("enabled")), "opted_in_at": own.get("opted_in_at"),
            "dismissed_at": own.get("banner_dismissed_at")}


def set_opt_in(merchant: Any, *, enabled: bool, actor: str) -> dict[str, Any]:
    cfg = dict(merchant.pricing_config or {})
    own = dict(cfg.get("smart_pricing") or {})
    own["enabled"] = bool(enabled)
    own["opted_in_at" if enabled else "opted_out_at"] = datetime.now(UTC).isoformat()
    own["opted_by"] = actor[:120]
    cfg["smart_pricing"] = own
    merchant.pricing_config = cfg
    return opt_in_state(merchant)


def dismiss_banner(merchant: Any) -> dict[str, Any]:
    cfg = dict(merchant.pricing_config or {})
    own = dict(cfg.get("smart_pricing") or {})
    own["banner_dismissed_at"] = datetime.now(UTC).isoformat()
    cfg["smart_pricing"] = own
    merchant.pricing_config = cfg
    return opt_in_state(merchant)


def examples(db: Session, merchant: Any) -> list[dict[str, Any]]:
    """Old vs new for a few drops from the merchant's own pickup (their recent FSAs first)."""
    from porterchain_api.pricing_engine import get_pricing_service
    from porterchain_api.pricing_engine.fsa_rate_card import default_pickup
    from porterchain_api.pricing_engine.smart_pricing import centroid, quote_route
    from porterchain_pricing import GeoPoint

    pickup = default_pickup(db, merchant.id)
    if pickup is None:
        return []
    fsas: list[str] = []
    for f in [*_recent_drop_fsas(db, merchant.id), *SAMPLE_FSAS]:
        if f not in fsas and centroid(f):
            fsas.append(f)
    svc = get_pricing_service(db)
    rows = []
    for fsa in fsas[:3]:
        lat, lng = centroid(fsa)  # type: ignore[misc]
        req = PricingRequest(
            pickup=GeoPoint(lat=pickup.lat, lng=pickup.lng, formatted=pickup.formatted, postal=pickup.fsa),
            dropoff=GeoPoint(lat=lat, lng=lng, formatted=fsa, postal=fsa),
            vehicle_class="cargo_van", channel="merchant", merchant_id=merchant.id,
            service_type="scheduled", schedule_mode="later", parcel_count=1,
        )
        try:
            old = svc.calculate_merchant_legacy(req) if hasattr(svc, "calculate_merchant_legacy") else svc.calculate_merchant(req)
            new = quote_route(db, pickups=[req.pickup], drops=[req.dropoff], vehicle_class="cargo_van",
                              merchant_id=merchant.id, config_override={"enabled": True})
        except Exception:  # noqa: BLE001
            logger.warning("route pricing example failed for %s", fsa, exc_info=True)
            continue
        rows.append({"from_fsa": pickup.fsa, "to_fsa": fsa, "old_cents": int(old.final_cents),
                     "new_cents": int(new.get("total_cents") or 0), "route_km": new.get("route_km")})
    return rows


def _recent_drop_fsas(db: Session, merchant_id: str) -> list[str]:
    from porterchain_api.booking_models import Order

    rows = (db.query(Order.compliance_metadata).filter(Order.merchant_id == merchant_id)
            .order_by(Order.created_at.desc()).limit(50).all())
    seen: list[str] = []
    for (meta,) in rows:
        f = ((meta or {}).get("analytics") or {}).get("fsa")
        if f and f not in seen:
            seen.append(f)
    return seen


def status_payload(db: Session, merchant: Any) -> dict[str, Any]:
    """What the portal / Shopify banner shows: state, plain summary, old vs new examples."""
    state = opt_in_state(merchant)
    return {
        **state,
        "show_banner": not state["opted_in"] and not state["dismissed_at"],
        "examples": [] if state["opted_in"] else examples(db, merchant),
        "summary": (
            "Route pricing prices your whole route on real road distance, in the optimized "
            "order, with a fair price for each extra stop. Liftgate, coverage and waiting "
            "charges stay the same. Your current prices stay until you opt in."
        ),
    }
