#!/usr/bin/env python3
"""§2.5.3 / DD-23 — Stripe webhook idempotency persisted in Postgres."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "apps/api/src/porterchain_api/booking_models.py"
SERVICE = ROOT / "apps/api/src/porterchain_api/booking_engine/stripe_webhook_idempotency.py"
WEBHOOK = ROOT / "apps/api/src/porterchain_api/booking_engine/stripe_webhook_service.py"
MIGRATION = ROOT / "apps/api/alembic/versions/o3p4q5r6s7t8_stripe_webhook_events.py"
TEST = ROOT / "apps/api/tests/test_stripe_webhook_idempotency.py"


def main() -> int:
    failures: list[str] = []

    for path in (MODEL, SERVICE, WEBHOOK, MIGRATION, TEST):
        if not path.is_file():
            failures.append(f"§2.5.3 missing {path.relative_to(ROOT)}")

    if MODEL.is_file():
        text = MODEL.read_text(encoding="utf-8", errors="ignore")
        if "class StripeWebhookEvent" not in text or "stripe_webhook_events" not in text:
            failures.append("§2.5.3 booking_models.py missing StripeWebhookEvent")

    if SERVICE.is_file():
        svc = SERVICE.read_text(encoding="utf-8", errors="ignore")
        for needle in ("claim_stripe_event", "complete_stripe_event", "on_conflict_do_nothing"):
            if needle not in svc:
                failures.append(f"§2.5.3 stripe_webhook_idempotency.py missing {needle}")

    if WEBHOOK.is_file():
        wh = WEBHOOK.read_text(encoding="utf-8", errors="ignore")
        if "claim_stripe_event" not in wh:
            failures.append("§2.5.3 stripe_webhook_service.py must use claim_stripe_event")

    if MIGRATION.is_file():
        mig = MIGRATION.read_text(encoding="utf-8", errors="ignore")
        if "stripe_webhook_events" not in mig:
            failures.append("§2.5.3 migration missing stripe_webhook_events table")

    if failures:
        print("Stripe webhook idempotency guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Stripe webhook idempotency guard passed (§2.5.3 — Postgres table + claim/release).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
