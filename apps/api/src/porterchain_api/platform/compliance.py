"""Compliance registers: region profile (CA / AT), retention schedule, GDPR Art. 30
records of processing, subprocessors, DPIA note for GPS, breach log (72 h clock) and
the data-subject request log (GDPR Art. 15-22 / PIPEDA). All stored in system_config,
editable in Settings → Compliance. Nothing here sends anything.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

STORAGE_KEY = "compliance"
BREACH_KEY = "breach_log"
REQUESTS_KEY = "privacy_requests"

REGIONS: dict[str, dict[str, Any]] = {
    "CA": {
        "label": "Canada (Ontario)", "currency": "CAD", "locale": "en-CA", "languages": ["en", "fr"],
        "tax": {"name": "HST", "rate_pct": 13.0, "registration_label": "GST/HST no."},
        "privacy_law": "PIPEDA + CASL", "request_days": 30, "breach_notify_hours": None,
        "invoice_retention_years": 6, "cookie_banner": False, "data_residency": "ca-central",
        "einvoice": None,
    },
    "AT": {
        "label": "Austria (EU)", "currency": "EUR", "locale": "de-AT", "languages": ["de", "en"],
        "tax": {"name": "USt", "rate_pct": 20.0, "registration_label": "UID-Nr."},
        "privacy_law": "GDPR + DSG + TKG 2021", "request_days": 30, "breach_notify_hours": 72,
        "invoice_retention_years": 7, "cookie_banner": True, "data_residency": "eu-central",
        "einvoice": "ebInterface / PEPPOL (B2G mandatory; UStG §11 invoice fields)",
    },
}

RETENTION = [
    {"data": "Invoices, payments, ledger", "keep": "CA 6 y (CRA) · AT 7 y (BAO §132)", "basis": "Legal obligation"},
    {"data": "Orders (addresses, contacts)", "keep": "Contacts erased on request; order kept for invoices", "basis": "Contract / legal"},
    {"data": "GPS breadcrumbs", "keep": "30 days (Dispatch → retention), live pin deleted when GPS off", "basis": "Legitimate interest / consent"},
    {"data": "Proof of delivery (photo, signature)", "keep": "365 days after delivery (claims window)", "basis": "Contract"},
    {"data": "Support tickets", "keep": "3 years after close", "basis": "Legitimate interest"},
    {"data": "Marketing consent + leads", "keep": "Until withdrawal; proof of consent 3 y (CASL)", "basis": "Consent"},
    {"data": "Driver records", "keep": "Employment/contract + 6 y", "basis": "Legal obligation"},
    {"data": "Server logs", "keep": "30 days", "basis": "Legitimate interest (security)"},
]

ROPA = [
    {"activity": "Delivery booking & fulfilment", "subjects": "Merchants, senders, recipients",
     "data": "Name, address, phone, email, parcel details", "purpose": "Perform delivery contract", "basis": "Art. 6(1)(b)",
     "recipients": "Assigned driver, hosting, email/SMS providers", "transfer": "None outside region when residency set"},
    {"activity": "Live tracking & ETA", "subjects": "Drivers, recipients", "data": "Driver location on shift, stop status",
     "purpose": "Dispatch, ETA, customer tracking", "basis": "Art. 6(1)(f) / consent where required", "recipients": "Dispatch, recipient (ETA only)",
     "transfer": "Self-hosted maps (Valhalla/OSRM), no third party"},
    {"activity": "Billing & accounting", "subjects": "Merchants, customers", "data": "Billing identity, invoices, payments",
     "purpose": "Invoicing, tax", "basis": "Art. 6(1)(b),(c)", "recipients": "Payment processor, accountant", "transfer": "Stripe (SCCs)"},
    {"activity": "Driver management & pay", "subjects": "Drivers", "data": "Identity, documents, vehicle, pay",
     "purpose": "Contract, pay, safety", "basis": "Art. 6(1)(b),(c)", "recipients": "Payroll", "transfer": "None"},
    {"activity": "Marketing & leads", "subjects": "Prospects", "data": "Name, email, company",
     "purpose": "B2B outreach", "basis": "Consent (CASL / Art. 6(1)(a))", "recipients": "Email provider", "transfer": "Provider SCCs"},
    {"activity": "Support", "subjects": "All users", "data": "Messages, order references", "purpose": "Resolve issues",
     "basis": "Art. 6(1)(b),(f)", "recipients": "Support staff", "transfer": "None"},
]

SUBPROCESSORS = [
    {"name": "DigitalOcean", "purpose": "Hosting: API, database, Redis, self-hosted maps (Toronto)", "location": "Canada (TOR1); EU option FRA1", "dpa": True},
    {"name": "Clerk", "purpose": "Sign-in and user accounts", "location": "USA", "dpa": True},
    {"name": "Stripe", "purpose": "Card payments, payouts", "location": "USA / Ireland", "dpa": True},
    {"name": "ZeptoMail (Zoho)", "purpose": "Transactional and opt-in email", "location": "USA / EU / India (account region)", "dpa": True},
    {"name": "Twilio", "purpose": "SMS alerts (when enabled)", "location": "USA", "dpa": True},
    {"name": "Shopify", "purpose": "Merchant store integration (independent controller of shop data)", "location": "Canada / USA", "dpa": True},
    {"name": "Sentry", "purpose": "Error monitoring (no intentional personal data)", "location": "USA", "dpa": True},
    {"name": "Cloudflare (R2 / DNS)", "purpose": "Blog media storage, DNS", "location": "Global", "dpa": True},
    {"name": "Google Maps Platform", "purpose": "Address geocoding fallback (only if key set)", "location": "USA", "dpa": True},
    {"name": "Expo (EAS)", "purpose": "Driver app push notifications / builds", "location": "USA", "dpa": True},
    {"name": "Doppler", "purpose": "Secrets management (no customer data)", "location": "USA", "dpa": True},
]

DPIA_GPS = (
    "DPIA — driver live GPS. Processing: device location of drivers while on shift; derived road-matched "
    "trail and ETA. Necessity: dispatch, safety and customer ETA cannot work without position; frequency "
    "limited to the ping interval, on shift only. Risks: monitoring of workers outside duty, profiling, "
    "location history exposure. Measures: on-shift only; global and per-driver off switch; optional "
    "explicit consent with withdrawal (stops collection immediately); live pin deleted on switch-off; "
    "30-day breadcrumb retention; customers see ETA/stop status, not history; self-hosted maps (no "
    "third-party sharing); admin access by role. Residual risk: low. Review yearly or on change. "
    "AT: consult works council (ArbVG §96a) before rollout to employees."
)


# No privacy officer appointed: the owner is the accountable person (PIPEDA Principle 1).
DEFAULT_PRIVACY_CONTACT = (
    "Ravi Chauhan, Owner (accountable for privacy) - privacy@porterchain.com / sales@porterchain.com"
)


def default_compliance() -> dict[str, Any]:
    return {"region": "CA", "data_residency": None, "dpo_contact": DEFAULT_PRIVACY_CONTACT,
            "privacy_by_default": True}


def normalize_compliance(raw: Any) -> dict[str, Any]:
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("compliance must be an object")
    src = {**default_compliance(), **(raw or {})}
    if src["region"] not in REGIONS:
        raise ValueError("unknown_region")
    return {
        "region": src["region"],
        "data_residency": src.get("data_residency") or None,
        "dpo_contact": str(src.get("dpo_contact") or DEFAULT_PRIVACY_CONTACT)[:200],
        "privacy_by_default": bool(src.get("privacy_by_default", True)),
    }


def region_profile(cfg: dict[str, Any]) -> dict[str, Any]:
    prof = dict(REGIONS[cfg["region"]])
    if cfg.get("data_residency"):
        prof["data_residency"] = cfg["data_residency"]
    return {"code": cfg["region"], **prof}


# --- breach log -----------------------------------------------------------
def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def normalize_breaches(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("breach_log must be a list")
    out = []
    for b in raw:
        if not isinstance(b, dict) or not b.get("title") or not b.get("detected_at"):
            raise ValueError("breach needs title and detected_at")
        _parse(str(b["detected_at"]))
        out.append({
            "id": str(b.get("id") or uuid.uuid4()),
            "title": str(b["title"])[:200],
            "detected_at": str(b["detected_at"]),
            "description": str(b.get("description") or "")[:4000],
            "data_types": str(b.get("data_types") or "")[:500],
            "subjects_affected": int(b.get("subjects_affected") or 0),
            "risk": b.get("risk") if b.get("risk") in ("low", "medium", "high") else "medium",
            "authority_notified_at": b.get("authority_notified_at") or None,
            "subjects_notified_at": b.get("subjects_notified_at") or None,
            "measures": str(b.get("measures") or "")[:4000],
            **_pipeda_fields(b),
        })
    return out


def _lst(v: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{k: str(i.get(k) or "")[:1000] for k in keys} for i in (v or []) if isinstance(i, dict)][:200]


def _pipeda_fields(b: dict[str, Any]) -> dict[str, Any]:
    """PIPEDA s.10.1 record of breaches (kept >= 24 months) + OPC report fields."""
    detected = _parse(str(b["detected_at"]))
    floor = (detected + timedelta(days=731)).isoformat()
    retain = str(b.get("retain_until") or floor)
    rrosh = b.get("rrosh") if isinstance(b.get("rrosh"), dict) else {}
    return {
        "occurred_from": b.get("occurred_from") or None,
        "occurred_to": b.get("occurred_to") or None,
        "contained_at": b.get("contained_at") or None,
        "cause": str(b.get("cause") or "")[:2000],
        "records_affected": str(b.get("records_affected") or "")[:4000],
        "rrosh": {"sensitivity": str(rrosh.get("sensitivity") or "")[:1000],
                  "probability_of_misuse": str(rrosh.get("probability_of_misuse") or "")[:1000],
                  "real_risk": rrosh.get("real_risk") if rrosh.get("real_risk") in ("yes", "no", "undetermined") else "undetermined"},
        "opc_reported_at": b.get("opc_reported_at") or None,
        "timeline": _lst(b.get("timeline"), ("at", "note")),
        "notifications": _lst(b.get("notifications"), ("at", "to", "method", "note")),
        "retain_until": max(retain, floor),  # never shorter than 24 months
    }


def breach_clock(b: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """GDPR Art. 33: authority within 72 h of awareness. PIPEDA: 'as soon as feasible' if RROSH."""
    now = now or datetime.now(UTC)
    due = _parse(b["detected_at"]) + timedelta(hours=72)
    done = bool(b.get("authority_notified_at"))
    return {
        **b,
        "authority_due_at": due.isoformat(),
        "hours_left": None if done else round((due - now).total_seconds() / 3600, 1),
        "overdue": (not done) and now > due,
    }


# --- data-subject requests ---------------------------------------------------
REQUEST_TYPES = ("access", "rectification", "erasure", "restriction", "portability", "objection", "withdraw_consent")


def normalize_requests(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("privacy_requests must be a list")
    out = []
    for r in raw:
        if not isinstance(r, dict) or r.get("type") not in REQUEST_TYPES or not r.get("subject"):
            raise ValueError("request needs a valid type and subject")
        opened = str(r.get("opened_at") or datetime.now(UTC).isoformat())
        out.append({
            "id": str(r.get("id") or uuid.uuid4()),
            "type": r["type"],
            "subject": str(r["subject"])[:320],
            "opened_at": opened,
            "due_at": str(r.get("due_at") or (_parse(opened) + timedelta(days=30)).isoformat()),
            "status": r.get("status") if r.get("status") in ("open", "done", "refused") else "open",
            "notes": str(r.get("notes") or "")[:2000],
            "closed_at": r.get("closed_at") or None,
        })
    return out


def overview(db: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig

    def val(key: str) -> Any:
        row = db.get(SystemConfig, key)
        return row.value if row else None

    cfg = normalize_compliance(val(STORAGE_KEY))
    now = datetime.now(UTC)
    reqs = normalize_requests(val(REQUESTS_KEY))
    for r in reqs:
        r["overdue"] = r["status"] == "open" and now > _parse(r["due_at"])
    return {
        "config": cfg,
        "region": region_profile(cfg),
        "regions": {k: v["label"] for k, v in REGIONS.items()},
        "retention": RETENTION,
        "ropa": ROPA,
        "subprocessors": SUBPROCESSORS,
        "dpia_gps": DPIA_GPS,
        "monitoring_policy": _monitoring(db),
        "breaches": [breach_clock(b, now=now) for b in normalize_breaches(val(BREACH_KEY))],
        "requests": reqs,
        "request_types": list(REQUEST_TYPES),
    }


def public_region(db: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig

    row = db.get(SystemConfig, STORAGE_KEY)
    p = region_profile(normalize_compliance(row.value if row else None))
    return {k: p[k] for k in ("code", "currency", "locale", "languages", "tax", "cookie_banner")}


def _monitoring(db: Any) -> dict[str, Any]:
    from porterchain_api.platform.monitoring_policy import ack_summary, policy

    return {**policy(), **ack_summary(db)}
