"""Merchant-facing quote picture — line items only, no routing vendor keys."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from porterchain_api.domain.catalog_labels import QUOTE_LINE_ORDER, quote_line_label

QUOTE_PICTURE_KEYS: frozenset[str] = frozenset(
    {
        "subtotal_cents",
        "tax_cents",
        "final_cents",
        "amount_cents",
        "currency",
        "items",
        "line_items",
        "distance_meters",
    }
)

_VENDOR_KEYS = frozenset(
    {
        "metadata",
        "summary",
        "routing_source",
        "route_geometry",
        "_merchant",
        "driver_share_pct",
        "platform_share_pct",
        "driver_payout_mode",
        "driver_payout_cents_preview",
    }
)

_QUOTE_ORDER_INDEX = {code: i for i, code in enumerate(QUOTE_LINE_ORDER)}


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def flatten_quote_breakdown(breakdown: dict[str, Any] | None) -> dict[str, Any]:
    """Collapse stored Quote.pricing_breakdown `{items, summary}` into one dict."""
    raw = _as_dict(breakdown)
    summary = _as_dict(raw.get("summary"))
    meta = _as_dict(summary.get("metadata"))
    meta.update(_as_dict(raw.get("metadata")))
    items = raw.get("items") or raw.get("line_items") or summary.get("items") or summary.get("line_items") or []
    amount = (
        raw.get("final_cents")
        if raw.get("final_cents") is not None
        else raw.get("amount_cents")
        if raw.get("amount_cents") is not None
        else summary.get("final_cents")
        if summary.get("final_cents") is not None
        else summary.get("amount_cents")
        if summary.get("amount_cents") is not None
        else raw.get("total_cents")
        if raw.get("total_cents") is not None
        else summary.get("total_cents")
    )
    subtotal = (
        raw.get("subtotal_cents") if raw.get("subtotal_cents") is not None else summary.get("subtotal_cents")
    )
    tax = raw.get("tax_cents") if raw.get("tax_cents") is not None else summary.get("tax_cents")
    currency = raw.get("currency") or summary.get("currency") or "cad"
    dist = raw.get("distance_meters")
    if dist is None:
        dist = summary.get("distance_meters")
    if dist is None:
        dist = meta.get("distance_meters")
    return {
        "items": items if isinstance(items, list) else [],
        "final_cents": amount,
        "amount_cents": amount,
        "subtotal_cents": subtotal,
        "tax_cents": tax,
        "currency": currency,
        "distance_meters": dist,
        "vehicle_class": raw.get("vehicle_class") or summary.get("vehicle_class"),
        "package_type": raw.get("package_type") or summary.get("package_type"),
        "duration_seconds": raw.get("duration_seconds"),
        "total_pickups": raw.get("total_pickups"),
        "total_drops": raw.get("total_drops"),
    }


def merchant_line_items(breakdown: dict[str, Any] | None) -> list[dict[str, Any]]:
    flat = flatten_quote_breakdown(breakdown)
    items = flat.get("items") or []
    out: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        amount = _int_or_none(item.get("amount_cents"))
        if amount is None:
            continue
        code = item.get("code")
        out.append(
            {
                "code": code,
                "label": quote_line_label(str(code) if code is not None else None, item.get("label")),
                "amount_cents": amount,
            }
        )
    out.sort(
        key=lambda row: (
            _QUOTE_ORDER_INDEX.get(str(row.get("code") or ""), len(_QUOTE_ORDER_INDEX)),
            str(row.get("code") or ""),
        )
    )
    return out


def merchant_quote_picture(
    breakdown: dict[str, Any] | None,
    *,
    vehicle_class: str | None = None,
    package_type: str | None = None,
    distance_meters: Any = None,
    quoted_at: datetime | None = None,
) -> dict[str, Any]:
    flat = flatten_quote_breakdown(breakdown)
    dist = distance_meters if distance_meters is not None else flat.get("distance_meters")
    when = quoted_at or datetime.now(UTC)
    lines = merchant_line_items(breakdown)
    return {
        "amount_cents": _int_or_none(flat.get("final_cents")),
        "subtotal_cents": _int_or_none(flat.get("subtotal_cents")),
        "tax_cents": _int_or_none(flat.get("tax_cents")),
        "currency": str(flat.get("currency") or "cad").lower(),
        "vehicle_class": vehicle_class or flat.get("vehicle_class"),
        "package_type": package_type or flat.get("package_type"),
        "distance_meters": _int_or_none(dist),
        "line_items": lines,
        "quoted_at": when.isoformat(),
    }


def sanitize_pricing_breakdown(breakdown: dict[str, Any] | None) -> dict[str, Any] | None:
    if not breakdown:
        return None
    picture = merchant_quote_picture(breakdown)
    if (
        picture["amount_cents"] is None
        and picture["subtotal_cents"] is None
        and picture["tax_cents"] is None
        and not picture["line_items"]
        and picture["distance_meters"] is None
    ):
        return None
    return {
        "subtotal_cents": picture["subtotal_cents"],
        "tax_cents": picture["tax_cents"],
        "final_cents": picture["amount_cents"],
        "amount_cents": picture["amount_cents"],
        "currency": picture["currency"],
        "items": picture["line_items"],
        "line_items": picture["line_items"],
        "distance_meters": picture["distance_meters"],
        "vehicle_class": picture.get("vehicle_class"),
        "package_type": picture.get("package_type"),
    }


def merchant_facing_quote(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """Route/bulk quote blob: same picture plus stop counts, no vendor keys."""
    if not raw:
        return None
    picture = sanitize_pricing_breakdown(raw)
    if not picture:
        return None
    for key in ("duration_seconds", "total_pickups", "total_drops"):
        value = raw.get(key)
        if value is not None:
            picture[key] = value
    for banned in _VENDOR_KEYS:
        picture.pop(banned, None)
    return picture
