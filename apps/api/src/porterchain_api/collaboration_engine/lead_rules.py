"""Leads P0 rules (doc 78 §3, §8): business-hours SLA, spam flags, transparent rules score.

Pure functions; no AI, no network. Spam is flagged to a "Possible spam" view, never dropped.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
OPEN_HOUR, CLOSE_HOUR = 8, 20
SLA_IN_HOURS = timedelta(hours=1)
SLA_OUT_OF_HOURS = timedelta(hours=4)
MIN_FILL_SECONDS = 3
MAX_LINKS = 2

DISPOSABLE_DOMAINS = frozenset(
    {
        "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com", "temp-mail.org",
        "yopmail.com", "trashmail.com", "sharklasers.com", "getnada.com", "dispostable.com",
        "maildrop.cc", "throwawaymail.com", "fakeinbox.com", "mohmal.com", "emailondeck.com",
    }
)
FREE_MAIL = frozenset({"gmail.com", "yahoo.com", "yahoo.ca", "hotmail.com", "outlook.com", "live.com", "icloud.com", "aol.com", "proton.me", "protonmail.com"})


def in_business_hours(at: datetime) -> bool:
    local = at.astimezone(TORONTO)
    return OPEN_HOUR <= local.hour < CLOSE_HOUR


def sla_due_at(created: datetime) -> datetime:
    """First-response target: 1 business hour (08:00–20:00 Toronto), 4 h outside."""
    return created + (SLA_IN_HOURS if in_business_hours(created) else SLA_OUT_OF_HOURS)


def sla_state(created: datetime, now: datetime, responded_at: datetime | None = None) -> str:
    """ok → amber at 75 % of the window → red at breach. Responded leads are 'met' or 'late'."""
    due = sla_due_at(created)
    if responded_at is not None:
        return "met" if responded_at <= due else "late"
    window = (due - created).total_seconds()
    used = (now - created).total_seconds()
    if used >= window:
        return "red"
    if used >= 0.75 * window:
        return "amber"
    return "ok"


_URL = re.compile(r"https?://|www\.", re.I)


def spam_flags(
    *, honeypot: str | None = None, fill_ms: int | None = None, email: str | None = None, message: str | None = None,
) -> list[str]:
    flags: list[str] = []
    if (honeypot or "").strip():
        flags.append("honeypot")
    if fill_ms is not None and fill_ms < MIN_FILL_SECONDS * 1000:
        flags.append("too_fast")
    domain = (email or "").rsplit("@", 1)[-1].strip().lower() if email and "@" in email else ""
    if domain in DISPOSABLE_DOMAINS:
        flags.append("disposable_email")
    if len(_URL.findall(message or "")) > MAX_LINKS:
        flags.append("many_links")
    return flags


_FIT = {"shopify_merchant": 25, "warehouse_3pl": 25, "supply_chain": 25, "import_export_cha": 20, "small_shop": 15,
        "logistics_partner": 10, "courier_partner": 10, "retail_customer": 5}


def rules_score(
    *, business_type: str | None = None, in_service_area: bool | None = None, monthly_volume: int | None = None,
    email: str | None = None, phone: str | None = None, name: str | None = None, replied: bool = False,
    spam: list[str] | None = None,
) -> dict[str, Any]:
    """Hot ≥ 70, Warm 40–69, Cold < 40, with the reasons shown on the lead."""
    reasons: list[dict[str, Any]] = []

    def add(label: str, pts: int) -> None:
        reasons.append({"label": label, "points": pts})

    add(f"Business type: {business_type or 'unknown'}", _FIT.get((business_type or "").lower(), 0))
    if in_service_area is True:
        add("In service area (Toronto + 150 km)", 20)
    elif in_service_area is False:
        add("Outside service area", -25)
    vol = int(monthly_volume or 0)
    add(f"Stated volume {vol}/month", 25 if vol >= 200 else 15 if vol >= 50 else 5 if vol > 0 else 0)
    complete = sum(bool(x) for x in (email, phone, name))
    add("Complete contact" if complete == 3 else f"Contact {complete}/3", 10 if complete == 3 else 3 * complete)
    domain = (email or "").rsplit("@", 1)[-1].lower() if email and "@" in email else ""
    if domain and domain not in FREE_MAIL and domain not in DISPOSABLE_DOMAINS:
        add("Business email domain", 10)
    if replied:
        add("Replied", 10)
    if spam:
        add("Spam signals: " + ", ".join(spam), -40)
    score = max(0, min(100, sum(r["points"] for r in reasons)))
    band = "hot" if score >= 70 else "warm" if score >= 40 else "cold"
    return {"score": score, "band": band, "reasons": reasons}
