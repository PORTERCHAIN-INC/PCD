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

    def _standard_live(self) -> bool:
        from porterchain_api.config import get_settings

        return bool(get_settings().pricing_standard_card_live)

    def calculate_retail(self, request: PricingRequest) -> PriceBreakdown:
        # Ravi 2026-10-31: customers get the parcel model only ($6/$9 + size/weight table).
        # Whole-vehicle hourly is merchants only, so a customer vehicle request is priced as parcels.
        from porterchain_pricing.three_models import parcel_price

        return _stamp(self._db, _hst_on(request, parcel_price(request), self._db))

    def calculate_merchant(self, request: PricingRequest) -> PriceBreakdown:
        # Model 3: an admin-set merchant price (pricing_config, contract schedule, custom org card) wins.
        if _has_custom_pricing(self._db, request.merchant_id):
            from porterchain_api.pricing_engine.standard_live import org_id_for_merchant, org_pricing

            org_id = org_id_for_merchant(self._db, request.merchant_id)
            org = org_pricing(self._db, org_id)
            if org is not None:  # admin custom org price on top of models 1/2
                return _stamp(self._db, _hst_on(request, _org_custom(request, org, org_id), self._db))
            return _vehicle_hst(request, PricingService.calculate_merchant(self, request), self._db)
        from porterchain_pricing.three_models import hourly_price, parcel_price

        if getattr(request, "booking_mode", "parcels") == "vehicle":
            return _stamp(self._db, _hst_on(request, hourly_price(request), self._db))  # model 2
        return _stamp(self._db, _hst_on(request, parcel_price(request), self._db))  # model 1

    def _retail(self, request: PricingRequest) -> PriceBreakdown:
        if self._standard_live():
            from porterchain_api.pricing_engine.standard_live import standard_breakdown

            bd = standard_breakdown(self._db, request)
            if bd is not None:
                return bd
        return super().calculate_retail(request)

    def _merchant(self, request: PricingRequest) -> PriceBreakdown:
        if self._standard_live():
            from porterchain_api.pricing_engine.standard_live import standard_breakdown

            bd = standard_breakdown(self._db, request)
            if bd is not None:
                return bd
        base = super().calculate_merchant(request)
        try:
            return apply_smart(self._db, request, base)
        except Exception:  # noqa: BLE001 - never break booking on the new engine
            logger.exception("smart route pricing failed; using existing price")
            return base


def _org_custom(request: PricingRequest, org: Any, org_id: str | None) -> PriceBreakdown:
    """Model 3 (admin custom merchant price): a flat price per stop, else a % on the model 1/2 price."""
    from porterchain_pricing.three_models import hourly_price, parcel_price
    from porterchain_pricing.types import PriceLineItem

    vehicle = getattr(request, "booking_mode", "parcels") == "vehicle"
    base = hourly_price(request) if vehicle else parcel_price(request)
    meta = {**(base.metadata or {})}
    if meta.get("custom_quote"):
        return base
    flat = getattr(org, "flat_parcel_cents", None)
    if flat and not vehicle:
        # Flat price per parcel, any size (no $6/$9 split, no handling tiers). % / per-stop do not stack on it.
        n = int(meta.get("small_parcels") or 0) + int(meta.get("van_parcels") or 0) or 1
        bd = PriceBreakdown(
            items=[PriceLineItem(code="custom_flat_parcel", label=f"Custom price x{n} (${flat / 100:.2f} per parcel)",
                                 amount_cents=int(flat) * n)],
            currency="CAD",
            metadata={**meta, "pricing": "custom_org", "price_rule": "custom_flat_parcel", "base_model": meta.get("pricing"),
                      "org_id": org_id, "flat_parcel_cents": int(flat)},
        )
        bd.finalize()
        bd.base_cents = bd.subtotal_cents
        return bd
    per_stop = getattr(org, "preset_per_stop_cents", None)
    pct = getattr(org, "preset_pct", None)
    items = list(base.items)
    rule = "custom_org"
    if pct:
        adj = int(round(base.subtotal_cents * float(pct) / 100))
        items.append(PriceLineItem(code="custom_adjustment", label=f"Custom contract price ({float(pct):+g}%)", amount_cents=adj))
    if per_stop:
        stops = 1 + len(request.additional_stops or [])
        sign = "+" if per_stop > 0 else "-"
        items.append(PriceLineItem(code="custom_per_stop", label=f"Custom contract per stop x{stops} ({sign}${abs(per_stop) / 100:.2f} each)",
                                   amount_cents=int(per_stop) * stops))
    bd = PriceBreakdown(items=items, currency="CAD", metadata={**meta, "pricing": "custom_org", "price_rule": rule,
                                                                "base_model": meta.get("pricing"), "org_id": org_id})
    bd.finalize()
    bd.base_cents = bd.subtotal_cents
    return bd


def three_model_preview(org: Any) -> list[dict[str, Any]]:
    """Admin org pricing preview on the 2026-10-31 models (standard vs this org's custom price)."""
    from porterchain_pricing import GeoPoint
    from porterchain_pricing.three_models import hourly_price, parcel_price

    def req(**kw: Any) -> PricingRequest:
        return PricingRequest(pickup=GeoPoint(lat=43.65, lng=-79.38), dropoff=GeoPoint(lat=43.7, lng=-79.4),
                              vehicle_class=kw.pop("vehicle_class", "cargo_van"), channel="merchant", **kw)

    samples = {
        "small_parcel_(fits_20x14x14_in)": req(weight_kg=4, dimensions={"length": 40, "width": 30, "height": 20}),
        "van_parcel": req(weight_kg=20, dimensions={"length": 70, "width": 45, "height": 40}),
        "handling_+30_(101-125_lb)": req(weight_kg=52, dimensions={"length": 70, "width": 45, "height": 40}),
        "cargo_van_3_h": req(booking_mode="vehicle", dedicated_hours=3),
        "16_ft_box_4_h": req(booking_mode="vehicle", dedicated_hours=4, vehicle_class="box_16"),
    }
    rows = []
    for name, r in samples.items():
        std = (hourly_price(r) if r.booking_mode == "vehicle" else parcel_price(r)).subtotal_cents
        cus = _org_custom(r, org, None).subtotal_cents if getattr(org, "mode", "standard") == "custom" else std
        rows.append({"sample": name, "standard_cents": std, "custom_cents": cus, "hst_cents": int(round(cus * 0.13))})
    return rows


def _stamp(db: Session, bd: PriceBreakdown) -> PriceBreakdown:
    """Every quote carries the admin price version (audit trail), same as the legacy engine."""
    try:
        from porterchain_api.pricing_engine.repository import current_price_version

        bd.metadata = {**(bd.metadata or {}), "price_version": current_price_version(db)}
    except Exception:  # noqa: BLE001
        logger.exception("price version lookup failed")
    return bd


def _has_custom_pricing(db: Session, merchant_id: str | None) -> bool:
    """A merchant with its own negotiated pricing (pricing_config rate card / price book, or a
    custom org card) keeps it; the class-rate floor is for standard-priced merchants only."""
    if not merchant_id or db is None:
        return False
    try:
        from porterchain_api.merchant_models import Merchant
        from porterchain_api.pricing_engine.standard_live import org_id_for_merchant, org_pricing

        m = db.get(Merchant, merchant_id)
        if m is not None and (m.pricing_config or {}):
            return True
        return org_pricing(db, org_id_for_merchant(db, merchant_id)) is not None
    except Exception:  # noqa: BLE001
        logger.exception("custom pricing lookup failed")
        return False


def apply_vehicle_class_rate(request: PricingRequest, bd: PriceBreakdown) -> PriceBreakdown:
    """Merchant-channel parcel minimum (merchant portal, admin New order, API).
    Ravi 2026-10-31 correction (replaces L85/L92 class-rate floor): price = max(quote, minimum),
    minimum $6 for a small parcel (fits 20x14x14 in) and $9 for anything larger (van).
    Whole-vehicle bookings keep the gta_rate matrix; manual/refused quotes and contracts are untouched."""
    from porterchain_pricing.vehicle_class_rate import parcel_minimum_cents

    if not isinstance(bd, PriceBreakdown) or getattr(request, "booking_mode", "parcels") == "vehicle":
        return bd
    meta = bd.metadata or {}
    if meta.get("manual_quote") or meta.get("fsa_refused") or bd.contract_id or meta.get("contract_id"):
        return bd
    # Ravi 2026-10-31 correction: the vehicle class (e.g. the cargo-van merchant default) no longer
    # sets the floor. Small parcel (fits 20x14x14 in) minimum $6, anything larger van minimum $9.
    rate, size_class = parcel_minimum_cents(request)
    meta.update({"parcel_minimum_cents": rate, "parcel_size_class": size_class})
    bd.metadata = meta
    from porterchain_pricing.standard_card import STANDARD_V1_LINES, _hst

    if bd.subtotal_cents >= rate:
        meta.setdefault("price_rule", "parcel_card")
        return bd
    top_up = rate - int(bd.subtotal_cents)
    label = "Small parcel minimum" if size_class == "small_parcel" else "Van minimum"
    bd.items.append(PriceLineItem(code="parcel_minimum", label=label, amount_cents=top_up))
    meta["price_rule"] = f"{size_class}_minimum"
    hst_rate = float(STANDARD_V1_LINES["hst_rate"]) if bd.tax_cents else 0.0
    bd.subtotal_cents = rate
    bd.tax_cents = _hst(rate, hst_rate) if hst_rate else 0
    bd.final_cents = rate + bd.tax_cents
    return bd


def _exempt_merchant_ids(db: Session | None) -> set[str]:
    """pricing_tax.exempt_merchant_ids (same list TaxCalculator honours). Read even when collects_tax is off."""
    if db is None:
        return set()
    try:
        from porterchain_api.admin_models import SystemConfig

        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
    except Exception:  # noqa: BLE001 - missing table in minimal test DBs
        db.rollback()
        return set()
    ids = (row.value or {}).get("exempt_merchant_ids") if row else None
    return {str(i) for i in ids or []}


def _vehicle_hst(request: PricingRequest, bd: PriceBreakdown, db: Session | None = None) -> PriceBreakdown:
    """Doc 72: whole-vehicle (gta_rate card) quotes carry the same 13 % HST as the Standard card.
    Only fills HST when the legacy engine left it at 0 (no double tax if system_config sets hst_percent)."""
    if not isinstance(bd, PriceBreakdown):  # stubs / non-standard engines: leave untouched
        return bd
    if getattr(request, "booking_mode", "parcels") != "vehicle" or bd.tax_cents or bd.subtotal_cents <= 0:
        return bd
    if (bd.metadata or {}).get("tax_exempt"):
        return bd
    mid = getattr(request, "merchant_id", None)
    if mid and str(mid) in _exempt_merchant_ids(db):
        bd.metadata["hst_source"] = "exempt_merchant"
        return bd
    from porterchain_pricing.standard_card import STANDARD_V1_LINES, _hst

    bd.tax_cents = _hst(int(bd.subtotal_cents), float(STANDARD_V1_LINES["hst_rate"]))
    bd.final_cents = bd.subtotal_cents + bd.tax_cents
    bd.metadata["hst_source"] = "doc72_standard_rate"
    return bd


def _hst_on(request: PricingRequest, bd: PriceBreakdown, db: Session | None = None) -> PriceBreakdown:
    """13 % Ontario HST on top of the three-model prices (all quoted before HST); exempt merchants skipped."""
    if (bd.metadata or {}).get("custom_quote") or bd.subtotal_cents <= 0:
        return bd
    mid = getattr(request, "merchant_id", None)
    if mid and str(mid) in _exempt_merchant_ids(db):
        bd.metadata["hst_source"] = "exempt_merchant"
        return bd
    from porterchain_pricing.standard_card import _hst

    bd.tax_cents = _hst(int(bd.subtotal_cents), 0.13)
    bd.final_cents = bd.subtotal_cents + bd.tax_cents
    bd.metadata["hst_source"] = "on_13"
    return bd


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
    if enabled and on_contract(merchant):
        raise ValueError("contract_merchant")
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


def on_contract(merchant: Any) -> bool:
    """A signed contract schedule prices this merchant; route pricing is not offered."""
    sched = (getattr(merchant, "pricing_config", None) or {}).get("schedule") or {}
    return bool(isinstance(sched, dict) and str(sched.get("contract_schedule") or "").strip())


def status_payload(db: Session, merchant: Any) -> dict[str, Any]:
    """What the portal / Shopify banner shows: state, plain summary, old vs new examples."""
    state = opt_in_state(merchant)
    if on_contract(merchant):
        return {**state, "contract": True, "show_banner": False, "examples": [], "summary": ""}
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
