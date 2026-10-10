"""Ontario ESA Part XI.1 written electronic monitoring policy (single source).

Served to drivers (onboarding acknowledgment, settings view, GPS consent prompt link) and
admin (Settings > Compliance). docs/legal/electronic-monitoring-policy.md mirrors this text;
bump POLICY_VERSION whenever it changes so drivers are asked to acknowledge again.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

POLICY_VERSION = "2026-10"
POLICY_DATE = "2026-10-10"
POLICY_TITLE = "Electronic Monitoring Policy"

POLICY_SECTIONS: list[dict[str, Any]] = [
    {
        "heading": "Does PorterChain monitor workers electronically?",
        "body": "Yes. This policy explains how, when and why, as required by Ontario's "
        "Employment Standards Act (Part XI.1). It applies to employees and contract drivers.",
    },
    {
        "heading": "What we monitor, how, when and why",
        "items": [
            "Driver location (GPS): the driver app or portal sends your phone's location only "
            "while you are on shift, for dispatch, routing, safety, customer arrival times and "
            "proof of service.",
            "Road-matched route trail: our own servers snap location points to roads so "
            "dispatch can see the last few hours of a shift, for accurate arrival times and "
            "investigating delivery issues.",
            "Proof of delivery: photo, signature, timestamps and location at each stop, to "
            "prove delivery and handle claims.",
            "Delivery app events: arrive, deliver and fail actions with timestamps, for arrival "
            "times, pay and service quality.",
            "Staff admin systems: sign-in records and audit logs of settings changes, for "
            "security and accountability.",
        ],
    },
    {
        "heading": "Controls",
        "items": [
            "Location is never collected off shift.",
            "PorterChain can turn live location off for all drivers or one driver; the app "
            "then stops sending location and the live position is deleted immediately.",
            "You are asked to agree before location is collected. If you withdraw, you are "
            "not tracked.",
            "Customers see only an arrival time and stop status, never your location history.",
            "Location history is deleted after 30 days; proof-of-delivery records after 365 days.",
        ],
    },
    {
        "heading": "How the information may be used",
        "body": "To plan and assign work, calculate pay and mileage, investigate complaints, "
        "claims or safety incidents, and meet legal obligations. It is not used for any other "
        "purpose.",
    },
    {
        "heading": "Questions",
        "body": "Ravi Chauhan, Owner (accountable for privacy): privacy@porterchain.com or "
        "sales@porterchain.com.",
    },
]


def policy() -> dict[str, Any]:
    return {"title": POLICY_TITLE, "version": POLICY_VERSION, "date": POLICY_DATE,
            "sections": POLICY_SECTIONS}


def acknowledgment_of(driver: Any) -> dict[str, Any] | None:
    rec = (getattr(driver, "documents", None) or {}).get("monitoring_policy_ack")
    return rec if isinstance(rec, dict) and rec.get("version") == POLICY_VERSION else None


def acknowledge(driver: Any, *, source: str = "portal") -> dict[str, Any]:
    """Timestamped, versioned acknowledgment on the driver record (history kept)."""
    docs = dict(driver.documents or {})
    rec = {"version": POLICY_VERSION, "at": datetime.now(UTC).isoformat(), "source": source[:16]}
    docs["monitoring_policy_ack"] = rec
    docs["monitoring_policy_ack_history"] = list(docs.get("monitoring_policy_ack_history") or [])[-19:] + [rec]
    driver.documents = docs
    return rec


def driver_view(driver: Any) -> dict[str, Any]:
    ack = acknowledgment_of(driver)
    return {**policy(), "acknowledged": ack is not None, "acknowledgment": ack}


def ack_summary(db: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import Driver

    drivers = db.query(Driver).all()
    acked = sum(1 for d in drivers if acknowledgment_of(d))
    return {"drivers": len(drivers), "acknowledged": acked, "pending": len(drivers) - acked}
