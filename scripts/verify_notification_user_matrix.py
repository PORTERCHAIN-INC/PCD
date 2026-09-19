#!/usr/bin/env python3
"""Seed + verify one in-app notification per template × user type against local DB/API.

Usage (from apps/api with venv):
  PYTHONPATH=src:../../shared/python:... python ../../scripts/verify_notification_user_matrix.py
  # or via monorepo helper if wired

Prints a pass/fail matrix and optional HTTP inbox checks when API is up with CLERK_DEV_BYPASS.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
for p in (
    API / "src",
    ROOT / "shared" / "python",
    ROOT / "services" / "event-bus",
    ROOT / "services" / "driver-platform",
    ROOT / "services" / "pricing-engine",
    ROOT / "services" / "fleetbase-adapter",
    ROOT / "services" / "python",
):
    sys.path.insert(0, str(p))

os.chdir(API)

from porterchain_api.db import SessionLocal, init_db  # noqa: E402
from porterchain_api.admin_models import AdminUser, Driver  # noqa: E402
from porterchain_api.merchant_models import Merchant  # noqa: E402
from porterchain_api.booking_models import Customer  # noqa: E402
from porterchain_api.notification_engine.engine import get_notification_engine  # noqa: E402
from porterchain_api.notification_engine.templates import TEMPLATE_META, TEMPLATES  # noqa: E402

API_BASE = os.environ.get("PORTERCHAIN_API_URL", "http://localhost:8001").rstrip("/")

# Representative templates per portal persona (product-relevant subset + one of each category).
ROLE_TEMPLATES: dict[str, list[str]] = {
    "admin": [
        "system_alert",
        "booking_confirmed",
        "order_booked",
        "driver_assigned",
        "driver_alert",
        "delivered",
        "pod_uploaded",
        "claim_opened",
        "support_ticket_created",
        "temp_excursion",
    ],
    "merchant": [
        "merchant_welcome",
        "booking_confirmed",
        "order_booked",
        "driver_assigned",
        "payment_receipt",
        "merchant_invoice_ready",
        "temp_excursion",
    ],
    "driver": [
        "driver_assigned",
        "driver_accepted",
        "delivered",
        "pod_uploaded",
        "driver_route_changed",
        "driver_alert",
        "claim_opened",
        "support_ticket_created",
        "delivery_update",
    ],
    "customer": [
        "booking_draft_created",
        "booking_confirmed",
        "checkout_recovery",
        "order_booked",
        "payment_started",
        "payment_receipt",
        "payment_failed",
        "driver_assigned",
        "in_transit",
        "near_delivery",
        "delivered",
        "invoice_ready",
        "refund_processed",
        "claim_opened",
        "support_ticket_created",
        "otp",
    ],
}

FULL_CONTEXT = {
    "tracking_number": "TRK-LIVE-001",
    "order_number": "ORD-LIVE-001",
    "quote_id": "Q-LIVE-001",
    "recovery_url": "http://localhost:3004/book",
    "amount_display": "$28.50",
    "invoice_number": "INV-LIVE-001",
    "merchant_name": "Live Merchant",
    "claim_number": "CLM-LIVE",
    "claim_type": "delay",
    "status": "open",
    "ticket_number": "TKT-LIVE",
    "subject": "Live matrix test",
    "message": "Live notification matrix test",
    "title": "Live alert",
    "body": "Live notification matrix test",
    "reset_url": "http://localhost:3000/reset",
    "code": "654321",
    "celsius": "4.2",
    "route_id": "RTE-LIVE",
    "stops_count": "2",
}


def resolve_recipients(db) -> dict[str, str]:
    admin = db.query(AdminUser).filter(AdminUser.is_active.is_(True)).first()
    merchant = db.query(Merchant).first()
    driver = db.query(Driver).first()
    customer = db.query(Customer).first()
    out: dict[str, str] = {}
    if admin:
        out["admin"] = admin.id
    if merchant:
        out["merchant"] = merchant.id
    if driver:
        out["driver"] = driver.id
    if customer:
        out["customer"] = customer.id
    # Fallback synthetic IDs still verify engine paths (won't show in signed-in UI)
    for role in ROLE_TEMPLATES:
        out.setdefault(role, f"synthetic-{role}-{uuid.uuid4().hex[:8]}")
    return out


def http_inbox(role: str, token: str = "dev", org_id: str | None = None) -> dict | None:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if org_id:
        headers["X-Merchant-Id"] = org_id
    req = Request(f"{API_BASE}/v1/notifications/inbox?limit=50", headers=headers)
    try:
        with urlopen(req, timeout=8) as res:
            return json.loads(res.read().decode())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def main() -> int:
    init_db()
    db = SessionLocal()
    engine = get_notification_engine()
    recipients = resolve_recipients(db)
    merchant_id = recipients.get("merchant")

    print("=== Notification user-type matrix (in_app) ===\n")
    print(f"{'role':<10} {'template':<28} {'category':<12} result")
    print("-" * 70)

    failures = 0
    seeded = 0
    for role, templates in ROLE_TEMPLATES.items():
        rid = recipients[role]
        for key in templates:
            if key not in TEMPLATES:
                print(f"{role:<10} {key:<28} {'?':<12} FAIL missing template")
                failures += 1
                continue
            cat = TEMPLATE_META[key]["category"]
            ctx = {**FULL_CONTEXT, "message": f"[{role}] {key}"}
            try:
                rec = engine.dispatch(
                    db,
                    event_type="verify.user_matrix",
                    template_key=key,
                    channel="in_app",
                    recipient_type=role,
                    recipient_id=rid,
                    context=ctx,
                    priority="normal",
                )
                db.commit()
                if not rec:
                    # Marketing defaults OFF (preference_service) — suppress is correct.
                    if cat == "marketing":
                        print(f"{role:<10} {key:<28} {cat:<12} OK suppressed")
                        continue
                    print(f"{role:<10} {key:<28} {cat:<12} FAIL dispatch None")
                    failures += 1
                    continue
                inbox = engine.inbox_payload(db, user_role=role, user_id=rid, limit=100)
                ok = any(i["id"] == rec.id for i in inbox["items"])
                print(f"{role:<10} {key:<28} {cat:<12} {'OK' if ok else 'FAIL inbox'}")
                if not ok:
                    failures += 1
                else:
                    seeded += 1
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                print(f"{role:<10} {key:<28} {cat:<12} FAIL {exc}")
                failures += 1

    print("\n=== Catalog coverage ===")
    print(f"templates catalog: {len(TEMPLATES)}")
    print(f"categories: {sorted({v['category'] for v in TEMPLATE_META.values()})}")
    print(f"seeded in_app rows: {seeded}")
    print(f"recipients: {json.dumps(recipients, indent=2)}")

    print("\n=== HTTP inbox smoke (Bearer dev) ===")
    # Local `dev` token resolves to AdminUser (and may also match merchant via bypass org).
    data = http_inbox("admin")
    if data is None:
        print("  admin: SKIP (API / auth)")
    else:
        print(f"  admin (Bearer dev): unread={data.get('unread_count')} items={len(data.get('items') or [])}")
    if merchant_id:
        data_m = http_inbox("merchant", org_id=merchant_id)
        if data_m is None:
            merchant_summary = "SKIP"
        else:
            merchant_summary = (
                f"unread={data_m.get('unread_count')} items={len(data_m.get('items') or [])}"
            )
        print(
            f"  merchant header X-Merchant-Id={merchant_id}: {merchant_summary}"
            "  (dev JWT prefers admin when AdminUser exists)"
        )
    print("  driver/customer inbox HTTP: use portal JWTs (not shared Bearer dev)")
    print("  Engine matrix above already verified inbox for all four DB recipient IDs.")

    db.close()
    if failures:
        print(f"\nFAILED: {failures}")
        return 1
    print("\nALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
