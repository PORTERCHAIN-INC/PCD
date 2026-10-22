"""Delivery options: one shared set for every booking surface, the driver and the label.

Stored on the order's dropoff address as ``dropoff["delivery_options"]`` (JSON, no schema
change). Pure: no DB, no network. The TypeScript twin lives in
``packages/types/src/deliveryOptions.ts``; keep keys and labels in step.
"""

from __future__ import annotations

from typing import Any

KEY = "delivery_options"

# How the parcel is handed over at the door (one at a time).
DROP_METHODS: dict[str, str] = {
    "leave_at_door": "Leave at door",
    "hand_to_recipient": "Hand to recipient only",
    "concierge": "Leave with concierge / reception",
}
FLAGS: dict[str, str] = {
    "call_on_arrival": "Call on arrival",
    "load_help": "Needs help loading / unloading",
}
TEXT_LIMITS: dict[str, int] = {"unit": 40, "buzzer": 40, "note": 500}

# Merchant "Site access" (jobsite gate code, foreman contact) rides on the same dropoff.
SITE_ACCESS_KEY = "site_access_notes"


def _text(value: Any, limit: int) -> str | None:
    text = " ".join(str(value or "").split())[:limit]
    return text or None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def normalize(raw: Any) -> dict[str, Any] | None:
    """Clean user input into the stored shape; ``None`` when nothing was chosen."""
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = {}
    method = str(raw.get("drop_method") or "").strip().lower()
    if method in DROP_METHODS:
        out["drop_method"] = method
    for flag in FLAGS:
        if _truthy(raw.get(flag)):
            out[flag] = True
    for key, limit in TEXT_LIMITS.items():
        text = _text(raw.get(key), limit)
        if text:
            out[key] = text
    return out or None


def apply(dropoff: dict[str, Any] | None, raw: Any) -> dict[str, Any] | None:
    """Return a copy of ``dropoff`` with normalized options set (or removed when empty)."""
    if dropoff is None:
        return None
    data = dict(dropoff)
    clean = normalize(raw)
    if clean:
        data[KEY] = clean
    else:
        data.pop(KEY, None)
    return data


def of(dropoff: Any) -> dict[str, Any]:
    if not isinstance(dropoff, dict):
        return {}
    return normalize(dropoff.get(KEY)) or {}


def summary_lines(dropoff: Any) -> list[str]:
    """Short human lines for the driver and the label, most important first."""
    opts = of(dropoff)
    lines: list[str] = []
    if opts.get("drop_method"):
        lines.append(DROP_METHODS[opts["drop_method"]])
    if opts.get("unit"):
        lines.append(f"Unit {opts['unit']}")
    if opts.get("buzzer"):
        lines.append(f"Buzzer {opts['buzzer']}")
    for flag, label in FLAGS.items():
        if opts.get(flag):
            lines.append(label)
    if opts.get("note"):
        lines.append(opts["note"])
    site = _text(dropoff.get(SITE_ACCESS_KEY), 300) if isinstance(dropoff, dict) else None
    if site:
        lines.append(f"Site access: {site}")
    return lines


def label_line(dropoff: Any, limit: int = 90) -> str | None:
    """One line for the thermal label (no free-text note: it can be long / personal)."""
    opts = of(dropoff)
    bits = [DROP_METHODS[opts["drop_method"]]] if opts.get("drop_method") else []
    if opts.get("unit"):
        bits.append(f"Unit {opts['unit']}")
    if opts.get("buzzer"):
        bits.append(f"Buzz {opts['buzzer']}")
    if opts.get("call_on_arrival"):
        bits.append("Call on arrival")
    if opts.get("load_help"):
        bits.append("Load help")
    text = " · ".join(bits)
    return (text[: limit - 1] + "…" if len(text) > limit else text) or None


def from_shopify(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Shopper's order note + common cart attributes (delivery instructions apps)."""
    raw: dict[str, Any] = {}
    note = _text(payload.get("note"), TEXT_LIMITS["note"])
    attrs: dict[str, str] = {}
    for attr in payload.get("note_attributes") or []:
        if isinstance(attr, dict):
            name = str(attr.get("name") or "").strip().lower().replace(" ", "_").replace("-", "_")
            value = _text(attr.get("value"), 200)
            if name and value:
                attrs[name] = value
    extra = attrs.get("delivery_instructions") or attrs.get("delivery_notes") or attrs.get("instructions")
    raw["note"] = " — ".join(x for x in (note, extra) if x) or None
    raw["buzzer"] = attrs.get("buzzer") or attrs.get("buzzer_code") or attrs.get("door_code")
    raw["unit"] = attrs.get("unit") or attrs.get("apartment") or attrs.get("suite")
    return normalize(raw)
