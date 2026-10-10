"""Bell deep links: every in-app item opens the right page in the recipient's portal.

A stored ``deep_link`` that is a relative path wins. Otherwise the link is built from
the record's ids (context / search_tags) for the portal that persona uses.
"""

from __future__ import annotations

from typing import Any

#: persona -> (entity key -> path template). First entity found wins.
ROUTES: dict[str, list[tuple[str, str]]] = {
    "admin": [
        ("lead_id", "/leads/{lead_id}"),
        ("claim_id", "/claims/{claim_id}"),
        ("ticket_id", "/support/{ticket_id}"),
        ("invoice_id", "/finance/invoices/{invoice_id}"),
        ("order_id", "/orders/{order_id}"),
    ],
    "merchant": [
        ("invoice_id", "/billing/invoices/{invoice_id}"),
        ("job_id", "/routes/{job_id}"),
        ("order_id", "/orders/{order_id}"),
    ],
    "customer": [
        ("invoice_id", "/invoices/{invoice_id}"),
        ("tracking_number", "/track/{tracking_number}"),
    ],
    "driver": [("order_id", "/jobs/{order_id}")],
}
#: Template-level destinations when there is no entity.
TEMPLATE_ROUTES: dict[str, dict[str, str]] = {
    "admin": {
        "notification_health_alert": "/notifications/delivery",
        "ops_daily_digest": "/notifications/delivery",
    },
    "driver": {"payout_sent": "/profile"},
}
FALLBACK = {"admin": "/notifications", "merchant": "/notifications", "customer": "/notifications", "driver": "/jobs"}
_GROUP_KEYS = ("order_id", "tracking_number", "lead_id", "claim_id", "ticket_id", "invoice_id", "job_id")


def _ids(record: Any) -> dict[str, str]:
    merged: dict[str, Any] = {}
    for src in (getattr(record, "search_tags", None), getattr(record, "context", None)):
        if isinstance(src, dict):
            for k, v in src.items():
                if v not in (None, "") and k not in merged:
                    merged[k] = v
    return {k: str(v) for k, v in merged.items() if isinstance(v, (str, int))}


def href_for(record: Any) -> str:
    stored = getattr(record, "deep_link", None)
    if isinstance(stored, str) and stored.startswith("/") and not stored.startswith("//"):
        return stored
    persona = "customer" if record.recipient_type == "consignee" else record.recipient_type
    tpl = TEMPLATE_ROUTES.get(persona, {}).get(record.template_key)
    if tpl:
        return tpl
    ids = _ids(record)
    for key, pattern in ROUTES.get(persona, []):
        if ids.get(key):
            return pattern.format(**{key: ids[key]})
    return FALLBACK.get(persona, "/notifications")


def group_for(record: Any) -> str | None:
    """Same entity -> one group in the bell ("3 updates for PC-1234")."""
    ids = _ids(record)
    for key in _GROUP_KEYS:
        if ids.get(key):
            return f"{key}:{ids[key]}"
    return None


def label_for(record: Any) -> str | None:
    ids = _ids(record)
    return ids.get("tracking_number") or ids.get("order_number") or ids.get("invoice_number") or None
