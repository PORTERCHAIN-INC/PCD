"""Per-merchant FSA rate card: one price per GTA drop FSA from the merchant's pickup.

Flow (one module, no second price formula):
1. Drive time + distance from the default pickup to every GTA FSA centroid
   (one Valhalla matrix call, OSRM fallback) → `porterchain_pricing.fsa_card`
   turns it into a clean banded drop price (Settings → `pricing_fsa_card`).
2. Prices are stored as the merchant's `pricing_fsa_rates` rows, so checkout,
   bookings and the card read the same numbers through PricingEngine.
3. Parcel-tier columns are real PricingEngine quotes (price book tiers, handling,
   minimum), never re-implemented here.

Cache: rows carry `config.pickup_key`; the card regenerates when the pickup moves.
Admin overrides (`config.override`) survive regeneration for the same pickup FSA.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

from porterchain_pricing import GeoPoint, PricingRequest
from porterchain_pricing.components.fsa import normalize_fsa
from porterchain_pricing.fsa_card import drop_price_cents, normalize_fsa_card
from porterchain_pricing.gta150_fsa import load_gta150_registry
from sqlalchemy.orm import Session

from porterchain_api.admin_models import PricingFsaRate, SystemConfig
from porterchain_api.merchant_models import Merchant, SavedAddress
from porterchain_api.services.routing import route_table

SETTINGS_KEY = "pricing_fsa_card"
SOURCE = "fsa_rate_card"
CARD_VEHICLE = "sedan_suv"


@dataclass(frozen=True, slots=True)
class Pickup:
    lat: float
    lng: float
    fsa: str
    formatted: str

    @property
    def key(self) -> str:
        """Cache key: moving the pickup ~100 m or changing its FSA regenerates the card."""
        return f"{self.fsa}:{self.lat:.3f},{self.lng:.3f}"


def card_settings(db: Session) -> dict[str, Any]:
    row = db.query(SystemConfig).filter(SystemConfig.key == SETTINGS_KEY).first()
    return normalize_fsa_card(row.value if row else None)


def default_pickup(db: Session, merchant_id: str) -> Pickup | None:
    addr = (
        db.query(SavedAddress)
        .filter(
            SavedAddress.merchant_id == merchant_id,
            SavedAddress.address_type == "pickup",
        )
        .order_by(SavedAddress.is_default.desc(), SavedAddress.created_at.asc())
        .first()
    )
    if addr is None or addr.lat is None or addr.lng is None:
        return None
    return Pickup(
        float(addr.lat),
        float(addr.lng),
        normalize_fsa(addr.postal or ""),
        addr.formatted,
    )


def gta_drop_fsas(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Active registry FSAs inside the card radius, with centroids."""
    radius = float(card["radius_km"])
    return [
        row
        for row in load_gta150_registry()["fsas"]
        if row.get("active", True) and float(row.get("distance_km_from_hub") or 1e9) <= radius
    ]


def _rows(db: Session, merchant_id: str, *, manual: bool = False) -> list[PricingFsaRate]:
    """Card rows (or, with ``manual``, hand-entered rows the card must not overwrite)."""
    rows = db.query(PricingFsaRate).filter(PricingFsaRate.merchant_id == merchant_id).all()
    return [r for r in rows if ((r.config or {}).get("source") == SOURCE) != manual]


def generate(db: Session, merchant_id: str, *, force: bool = False) -> list[PricingFsaRate]:
    """(Re)build the merchant's FSA rows when the pickup changed (or ``force``)."""
    pickup = default_pickup(db, merchant_id)
    if pickup is None:
        raise ValueError("pickup_required")
    existing = _rows(db, merchant_id)
    if existing and not force and all((r.config or {}).get("pickup_key") == pickup.key for r in existing):
        return existing

    card = card_settings(db)
    drops = gta_drop_fsas(card)
    legs = route_table((pickup.lat, pickup.lng), [(float(d["lat"]), float(d["lng"])) for d in drops])
    keep_overrides = {
        r.dest_fsa: r for r in existing if (r.config or {}).get("override") and r.origin_fsa == (pickup.fsa or None)
    }
    for row in existing:
        if row.dest_fsa not in keep_overrides:
            db.delete(row)
    db.flush()

    out: list[PricingFsaRate] = []
    hand_priced = {r.dest_fsa for r in _rows(db, merchant_id, manual=True) if r.vehicle_class is None}
    for drop, (seconds, meters) in zip(drops, legs, strict=True):
        code = str(drop["code"])
        if code in hand_priced:
            continue  # a negotiated row already prices this FSA
        if seconds is None or meters is None:
            continue  # unreachable by road from this pickup: no price, custom quote
        km, minutes = meters / 1000.0, seconds / 60.0
        meta = {
            "source": SOURCE,
            "pickup_key": pickup.key,
            "km": round(km, 1),
            "minutes": round(minutes),
            "computed_cents": drop_price_cents(km, minutes, code, card),
        }
        row = keep_overrides.get(code)
        if row is not None:
            row.config = {**(row.config or {}), **meta}
        else:
            row = PricingFsaRate(
                merchant_id=merchant_id,
                origin_fsa=pickup.fsa or None,
                dest_fsa=code,
                vehicle_class=None,
                flat_cents=meta["computed_cents"],
                includes_location_fees=True,  # downtown uplift is inside the price
                label=f"FSA card {pickup.fsa or 'pickup'} → {code}",
                is_active=True,
                config=meta,
            )
            db.add(row)
        out.append(row)
    db.commit()
    return out


def override(db: Session, merchant_id: str, dest_fsa: str, cents: int | None) -> PricingFsaRate:
    """Admin sets one cell (``cents``) or clears the override (``None`` → computed price)."""
    code = normalize_fsa(dest_fsa)
    row = next((r for r in _rows(db, merchant_id) if r.dest_fsa == code), None)
    if row is None:
        raise LookupError("fsa_cell_not_found")
    config = dict(row.config or {})
    if cents is None:
        config.pop("override", None)
        row.flat_cents = int(config["computed_cents"])
    else:
        if cents <= 0:
            raise ValueError("fsa_cell_invalid")
        config["override"] = True
        row.flat_cents = int(cents)
    row.config = config
    db.commit()
    return row


def rate_card(db: Session, merchant_id: str) -> dict[str, Any]:
    """The merchant's card (regenerated first if the pickup moved), priced by PricingEngine."""
    from porterchain_pricing.policy import MODEL_FSA

    from porterchain_api.pricing_engine import get_pricing_service

    rows = sorted(generate(db, merchant_id), key=lambda r: r.dest_fsa)
    pickup = default_pickup(db, merchant_id)
    assert pickup is not None  # generate() refused otherwise
    merchant = db.get(Merchant, merchant_id)
    card = card_settings(db)
    centroids = {d["code"]: d for d in gta_drop_fsas(card)}
    service = get_pricing_service(db)
    base_request = _request(merchant_id, pickup, rows[0], centroids, 1) if rows else None
    context = service.repository.load_context(base_request) if base_request else None
    on_fsa = bool(context and context.merchant_policy and context.merchant_policy.pricing_model == MODEL_FSA)

    cells = []
    for row in rows:
        config = row.config or {}
        tiers: dict[str, int] = {}
        if on_fsa:
            for n in card["tier_columns"]:
                quote = service.calculate(_request(merchant_id, pickup, row, centroids, n), context=context)
                if not quote.metadata.get("custom_quote"):
                    tiers[str(n)] = int(quote.subtotal_cents)
        cells.append(
            {
                "dest_fsa": row.dest_fsa,
                "price_cents": row.flat_cents,
                "computed_cents": config.get("computed_cents"),
                "override": bool(config.get("override")),
                "km": config.get("km"),
                "minutes": config.get("minutes"),
                "downtown": row.dest_fsa in card["downtown_fsas"],
                "parcel_tiers_cents": tiers,
            }
        )
    return {
        "merchant_id": merchant_id,
        "company_name": merchant.company_name if merchant else None,
        "pickup": {"formatted": pickup.formatted, "fsa": pickup.fsa} if pickup else None,
        "pricing_model_is_fsa": on_fsa,
        "tier_columns": card["tier_columns"],
        "currency": "CAD",
        "taxes": "HST extra",
        "cells": cells,
    }


def _request(merchant_id: str, pickup: Pickup, row: PricingFsaRate, centroids: dict, parcels: int) -> PricingRequest:
    drop = centroids.get(row.dest_fsa) or {}
    config = row.config or {}
    return PricingRequest(
        pickup=GeoPoint(
            lat=pickup.lat,
            lng=pickup.lng,
            formatted=pickup.formatted,
            postal=pickup.fsa,
        ),
        dropoff=GeoPoint(
            lat=drop.get("lat"),
            lng=drop.get("lng"),
            formatted=row.dest_fsa,
            postal=row.dest_fsa,
        ),
        vehicle_class=CARD_VEHICLE,
        channel="merchant",
        merchant_id=merchant_id,
        service_type="scheduled",
        schedule_mode="later",
        distance_meters=int(float(config.get("km") or 0) * 1000),
        estimated_duration_minutes=int(config.get("minutes") or 0),
        parcel_count=parcels,
    )


def to_csv(card: dict[str, Any]) -> str:
    buf = io.StringIO()
    cols = [str(n) for n in card["tier_columns"]]
    writer = csv.writer(buf)
    writer.writerow(
        [
            "drop_fsa",
            "price_cad",
            *[f"{n}_parcels_cad" for n in cols],
            "drive_km",
            "drive_min",
            "downtown",
            "override",
        ]
    )
    for c in card["cells"]:
        tiers = c["parcel_tiers_cents"]
        writer.writerow(
            [
                c["dest_fsa"],
                f"{c['price_cents'] / 100:.2f}",
                *[f"{tiers[n] / 100:.2f}" if n in tiers else "" for n in cols],
                c["km"],
                c["minutes"],
                "yes" if c["downtown"] else "",
                "yes" if c["override"] else "",
            ]
        )
    return buf.getvalue()


def to_pdf(card: dict[str, Any]) -> bytes:
    """One-page-per-~45-rows printable card (reportlab)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    cols = [str(n) for n in card["tier_columns"]]
    head = ["Drop FSA", "1 parcel", *[f"{n} parcels" for n in cols], "Drive"]
    body = [
        [
            c["dest_fsa"] + (" *" if c["downtown"] else ""),
            f"${c['price_cents'] / 100:.2f}",
            *[f"${c['parcel_tiers_cents'][n] / 100:.2f}" if n in c["parcel_tiers_cents"] else "quote" for n in cols],
            f"{c['km']} km · {c['minutes']} min",
        ]
        for c in card["cells"]
    ]
    styles = getSampleStyleSheet()
    pickup = (card.get("pickup") or {}).get("formatted") or "pickup"
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="PorterChain FSA rate card")
    table = Table([head, *body], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b2545")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f2f5f9")],
                ),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    doc.build(
        [
            Paragraph(
                f"PorterChain delivery rate card — {card.get('company_name') or ''}",
                styles["Title"],
            ),
            Paragraph(
                f"From {pickup}. Prices in CAD per drop, HST extra. * downtown core.",
                styles["Normal"],
            ),
            Spacer(1, 8),
            table,
        ]
    )
    return buf.getvalue()
