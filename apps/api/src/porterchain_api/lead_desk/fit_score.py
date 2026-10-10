"""Deterministic lead fit score (0-100) with human-readable reasons.

Rules only — same lead in, same score out. Weights (max): industry 30,
volume 25, GTA coverage 15, channel 15, engagement 15. An optional LLM note
(``LEAD_AI_ENABLED``) may add a 0-point reason; it never changes the number.
"""

from __future__ import annotations

import re
from typing import Any

SCORE_VERSION = "fit-v1"

# Target verticals (Ravi, 2026-10). Keyword → canonical label.
TARGET_INDUSTRIES: dict[str, tuple[str, ...]] = {
    "Shopify / e-commerce": (
        "shopify",
        "ecommerce",
        "e-commerce",
        "online store",
        "dtc",
    ),
    "Pharmacy": ("pharmacy", "pharma", "drugstore", "apothecary", "chemist"),
    "Labs / medical": (
        "lab",
        "labs",
        "laboratory",
        "clinic",
        "medical",
        "dental",
        "specimen",
    ),
    "Warehouse / 3PL": (
        "warehouse",
        "warehouses",
        "3pl",
        "fulfil",
        "fulfill",
        "distribution centre",
    ),
    "Traders / wholesale": (
        "wholesale",
        "trader",
        "traders",
        "distributor",
        "import",
        "export",
    ),
    "Construction": ("construction", "contractor", "jobsite", "builder", "renovation"),
    "Plumbing / electrical": (
        "plumbing",
        "plumber",
        "electrical",
        "electrician",
        "hvac",
        "trade supply",
    ),
}
_ADJACENT = (
    "furniture",
    "florist",
    "bakery",
    "restaurant",
    "retail",
    "auto parts",
    "print",
)

_CHANNEL_POINTS: dict[str, tuple[int, str]] = {
    "calculator": (15, "Priced a lane on the calculator"),
    "whatsapp": (13, "Messaged on WhatsApp"),
    "phone": (13, "Called in"),
    "app_install": (12, "Installed the Shopify app"),
    "merchant_signup": (12, "Signed up for a merchant account"),
    "email": (11, "Emailed sales@"),
    "website": (10, "Website inquiry"),
    "google_ads": (9, "Google Ads lead form"),
    "referral": (12, "Referral"),
    "manual": (6, "Added by staff"),
}


def _text(lead: Any) -> str:
    cf = (
        lead.custom_fields
        if isinstance(getattr(lead, "custom_fields", None), dict)
        else {}
    )
    tags = lead.tags if isinstance(getattr(lead, "tags", None), list) else []
    bits = [
        getattr(lead, "industry", None),
        getattr(lead, "business_type", None),
        getattr(lead, "company_name", None),
        getattr(lead, "source", None),
        cf.get("industry"),
        *[str(t) for t in tags],
    ]
    return " ".join(str(b) for b in bits if b).lower().replace("-", " ")


def _pattern(word: str) -> str:
    w = re.escape(word)
    return rf"\b{w}" if len(word) >= 6 else rf"\b{w}s?\b"


def industry_fit(lead: Any) -> tuple[int, str]:
    text = _text(lead)
    for label, words in TARGET_INDUSTRIES.items():
        if any(re.search(_pattern(w), text) for w in words):
            return 30, f"Target industry: {label}"
    if any(w in text for w in _ADJACENT):
        return 15, "Adjacent industry (regular local deliveries)"
    if getattr(lead, "industry", None) or (
        getattr(lead, "custom_fields", None) or {}
    ).get("industry"):
        return 6, "Industry outside the target list"
    return 8, "Industry unknown"


def monthly_volume(lead: Any) -> int:
    n = int(getattr(lead, "estimated_deliveries_per_month", 0) or 0)
    if n:
        return n
    raw = str((getattr(lead, "custom_fields", None) or {}).get("monthly_volume") or "")
    return {"1-20": 10, "21-100": 60, "101-500": 300, "500+": 750}.get(raw, 0)


def volume_points(lead: Any) -> tuple[int, str]:
    n = monthly_volume(lead)
    if n >= 500:
        return 25, f"High volume (~{n}/month)"
    if n >= 100:
        return 20, f"Solid volume (~{n}/month)"
    if n >= 20:
        return 14, f"Regular volume (~{n}/month)"
    if n > 0:
        return 7, f"Low volume (~{n}/month)"
    return 5, "Volume unknown"


def lead_fsa(lead: Any) -> str | None:
    cf = (
        lead.custom_fields
        if isinstance(getattr(lead, "custom_fields", None), dict)
        else {}
    )
    addr = lead.address if isinstance(getattr(lead, "address", None), dict) else {}
    for raw in (
        cf.get("pickup_fsa"),
        getattr(lead, "service_area", None),
        addr.get("postal"),
        addr.get("postal_code"),
    ):
        code = str(raw or "").strip().upper().replace(" ", "")[:3]
        if re.fullmatch(r"[A-Z]\d[A-Z]", code):
            return code
    return None


def area_points(lead: Any) -> tuple[int, str]:
    from porterchain_api.marketing_site.fsa_geo import fsa_centroid

    fsa = lead_fsa(lead)
    if not fsa:
        return 6, "Area unknown"
    if fsa_centroid(fsa):
        return 15, f"In coverage ({fsa}, GTA)"
    return 0, f"Outside coverage ({fsa})"


def channel_points(lead: Any) -> tuple[int, str]:
    cf = (
        lead.custom_fields
        if isinstance(getattr(lead, "custom_fields", None), dict)
        else {}
    )
    key = (
        "calculator"
        if cf.get("form") == "calculator"
        else (getattr(lead, "channel", None) or "website")
    )
    pts, label = _CHANNEL_POINTS.get(key, (7, f"Channel: {key}"))
    return pts, label


def engagement_points(lead: Any, visitor: Any = None) -> tuple[int, list[str]]:
    cf = (
        lead.custom_fields
        if isinstance(getattr(lead, "custom_fields", None), dict)
        else {}
    )
    pts, why = 0, []
    if getattr(lead, "phone", None) and getattr(lead, "email", None):
        pts += 5
        why.append("Phone + email")
    elif getattr(lead, "phone", None) or getattr(lead, "email", None):
        pts += 2
    if cf.get("estimate_cents") or cf.get("pickup_fsa"):
        pts += 5
        why.append("Asked for a price")
    if getattr(lead, "last_inbound_at", None) or getattr(lead, "awaiting_reply", False):
        pts += 5
        why.append("Wrote to us")
    if str(cf.get("intent") or "").lower() in {
        "quote",
        "call",
        "meeting",
        "demo",
        "book",
    }:
        pts += 5
        why.append(f"Asked to {str(cf.get('intent')).lower()}")
    if visitor is not None and (
        getattr(visitor, "quote_generated", False)
        or int(getattr(visitor, "intent_score", 0) or 0) >= 60
    ):
        pts += 5
        why.append("Built a quote on the site")
    return min(pts, 15), why


def fit_score(lead: Any, visitor: Any = None) -> dict[str, Any]:
    """{score, reasons:[{label, points}], version}. Deterministic."""
    if (getattr(lead, "intent_type", "") or "") == "driver_partner":
        return {
            "score": 0,
            "reasons": [{"label": "Driver applicant (not a buyer)", "points": 0}],
            "version": SCORE_VERSION,
        }
    reasons: list[dict[str, Any]] = []
    total = 0
    for fn in (industry_fit, volume_points, area_points, channel_points):
        pts, label = fn(lead)
        total += pts
        reasons.append({"label": label, "points": pts})
    epts, ewhy = engagement_points(lead, visitor)
    total += epts
    reasons.append(
        {"label": "Engagement: " + (", ".join(ewhy) or "none yet"), "points": epts}
    )
    return {
        "score": max(0, min(100, total)),
        "reasons": reasons,
        "version": SCORE_VERSION,
    }


def ai_note(lead: Any, result: dict[str, Any]) -> str | None:
    """Optional one-line LLM summary (flag + NIM key). Never affects the score."""
    from porterchain_api.lead_desk.ai import complete_text

    reasons = "; ".join(r["label"] for r in result.get("reasons", []))
    return complete_text(
        "In one short sentence, say why this delivery lead is or is not a good fit. "
        f"Company: {getattr(lead, 'company_name', '')}. Signals: {reasons}."
    )
