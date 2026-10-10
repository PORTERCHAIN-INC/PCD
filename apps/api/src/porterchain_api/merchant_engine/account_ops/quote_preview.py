"""Per-merchant quote preview and the driver-cost margin floor.

Preview runs the exact merchant pricing path (`quote_merchant_rate`, the same
engine as booking and Shopify checkout) for an address pair, then compares the
pre-tax price with an estimated driver cost from the live `driver_pay_plan`.
Nothing is booked or stored.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant

POLICY_KEY = "merchant_margin_floor"
DEFAULT_POLICY: dict[str, Any] = {"min_margin_pct": 20, "stops_per_block": 6, "service_minutes": 15}


def margin_policy(db: Session) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig

    row = db.query(SystemConfig).filter(SystemConfig.key == POLICY_KEY).first()
    raw = row.value if row and isinstance(row.value, dict) else {}
    out = dict(DEFAULT_POLICY)
    for key in DEFAULT_POLICY:
        try:
            if key in raw:
                out[key] = max(0, int(raw[key]))
        except (TypeError, ValueError):
            pass
    out["stops_per_block"] = max(1, out["stops_per_block"])
    return out


def driver_plan(db: Session) -> dict[str, Any]:
    from porterchain_pricing.driver_pay import (
        default_driver_pay_plan,
        normalize_driver_pay_plan,
    )

    from porterchain_api.admin_models import SystemConfig

    row = db.query(SystemConfig).filter(SystemConfig.key == "driver_pay_plan").first()
    try:
        return normalize_driver_pay_plan(row.value if row else None)
    except ValueError:
        return default_driver_pay_plan()


def driver_cost_cents(plan: dict[str, Any], policy: dict[str, Any], *, drive_minutes: float | None) -> dict[str, Any]:
    """Marginal driver cost of one pickup + one drop under the pay plan."""
    mode = plan["mode"]
    minutes = float(drive_minutes or 0) + policy["service_minutes"]
    hourly = int(round(plan["hourly_cents"] * minutes / 60))
    per_stop = plan["per_stop_cents"] + plan["per_pickup_cents"]
    if mode == "hourly":
        cents, basis = hourly, f"{minutes:.0f} min at hourly rate"
    elif mode == "per_stop":
        cents, basis = per_stop, "per stop + per pickup"
    elif mode == "hybrid":
        cents, basis = max(hourly, per_stop), "higher of hourly time and per-stop"
    elif mode == "per_route":
        stops = plan["route_included_stops"] or 1
        cents, basis = int(round(plan["per_route_cents"] / stops)), f"route pay / {stops} included stops"
    else:  # wave_block
        wb = plan["wave_block"]
        stops = wb["included_stops"] or policy["stops_per_block"]
        cents = int(round(wb["block_cents"] / stops))
        basis = f"{wb['block_hours']:g} h block / {stops} stops"
    return {"cents": cents, "mode": mode, "basis": basis}


def margin_verdict(price_cents: int, cost_cents: int, min_pct: int) -> dict[str, Any]:
    margin = price_cents - cost_cents
    pct = int(round(margin * 100 / price_cents)) if price_cents > 0 else None
    if price_cents <= 0:
        status = "no_price"
    elif margin < 0:
        status = "below_cost"
    elif pct is not None and pct < min_pct:
        status = "below_floor"
    else:
        status = "ok"
    return {"margin_cents": margin, "margin_pct": pct, "status": status, "floor_pct": min_pct}


def _address(db: Session, raw: dict[str, Any] | None, merchant: Merchant, *, pickup: bool):
    from porterchain_api.schemas_merchant import AddressInput

    raw = raw or {}
    if pickup and not (raw.get("formatted") or raw.get("postal")):
        from porterchain_api.merchant_models import SavedAddress

        saved = (
            db.query(SavedAddress)
            .filter(SavedAddress.merchant_id == merchant.id, SavedAddress.address_type == "pickup")
            .order_by(SavedAddress.is_default.desc(), SavedAddress.created_at.asc())
            .first()
        )
        if not saved:
            raise ValueError("pickup_required")
        return AddressInput(formatted=saved.formatted, lat=saved.lat, lng=saved.lng, postal=saved.postal)
    text = str(raw.get("formatted") or "").strip()
    postal = str(raw.get("postal") or "").strip().upper() or None
    lat, lng = raw.get("lat"), raw.get("lng")
    if lat is None or lng is None:
        from porterchain_api.merchant_engine.import_geocode import geocode_stop

        geo = geocode_stop(address=text or (postal or ""), postal=postal, province="ON")
        if geo.lat is None or geo.lng is None:
            raise ValueError("address_not_found")
        lat, lng = geo.lat, geo.lng
        text = text or geo.formatted or postal or ""
        postal = postal or getattr(geo, "postal", None)
    if not text and not postal:
        raise ValueError("dropoff_required")
    return AddressInput(formatted=text or postal or "", lat=float(lat), lng=float(lng), postal=postal)


def fsa_rows_below_floor(db: Session, merchant: Merchant, cost: int, min_pct: int) -> list[dict[str, Any]]:
    from porterchain_api.admin_models import PricingFsaRate

    out = []
    rows = (
        db.query(PricingFsaRate)
        .filter(PricingFsaRate.merchant_id == merchant.id, PricingFsaRate.is_active.is_(True))
        .all()
    )
    for row in rows:
        verdict = margin_verdict(int(row.flat_cents or 0), cost, min_pct)
        if verdict["status"] in ("below_cost", "below_floor"):
            out.append(
                {
                    "origin_fsa": row.origin_fsa,
                    "dest_fsa": row.dest_fsa,
                    "vehicle_class": row.vehicle_class,
                    "flat_cents": row.flat_cents,
                    **verdict,
                }
            )
    return out[:50]


def preview(db: Session, merchant_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from porterchain_api.integrations.shopify_carrier_rates import quote_merchant_rate
    from porterchain_api.merchant_engine.account_ops import get_merchant

    merchant = get_merchant(db, merchant_id)
    pickup = _address(db, body.get("pickup"), merchant, pickup=True)
    dropoff = _address(db, body.get("dropoff"), merchant, pickup=False)
    weight = body.get("weight_kg")
    try:
        weight = float(weight) if weight not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise ValueError("weight_invalid") from exc
    final, breakdown = quote_merchant_rate(
        db, merchant, pickup=pickup, dropoff=dropoff, weight_kg=weight,
        vehicle_class=body.get("vehicle_class") or None,
    )
    meta = breakdown.get("metadata") or {}
    distance = meta.get("distance_meters")
    duration_min = meta.get("estimated_duration_minutes")
    if duration_min is None and distance:
        duration_min = float(distance) / 1000 / 35 * 60  # 35 km/h city average
    policy = margin_policy(db)
    plan = driver_plan(db)
    cost = driver_cost_cents(plan, policy, drive_minutes=duration_min)
    subtotal = int(breakdown.get("subtotal_cents") or final)
    verdict = margin_verdict(subtotal, cost["cents"], policy["min_margin_pct"])
    return {
        "price": {
            "final_cents": final,
            "subtotal_cents": subtotal,
            "tax_cents": breakdown.get("tax_cents"),
            "lines": breakdown.get("items") or [],
            "pricing_model": merchant.pricing_model,
            "refused": final <= 0,
            "price_version": meta.get("price_version"),
        },
        "route": {
            "pickup": pickup.formatted,
            "dropoff": dropoff.formatted,
            "distance_km": round(float(distance) / 1000, 1) if distance else None,
            "drive_minutes": int(duration_min) if duration_min else None,
        },
        "driver_cost": cost,
        "margin": verdict,
        "fsa_rows_below_floor": fsa_rows_below_floor(db, merchant, cost["cents"], policy["min_margin_pct"])
        if merchant.pricing_model == "fsa"
        else [],
    }
