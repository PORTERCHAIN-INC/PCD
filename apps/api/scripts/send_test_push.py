#!/usr/bin/env python3
"""Send a test push to a driver — §0.1.3 device push verification.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/send_test_push.py --email priya.sharma@porterchain.com
    cd apps/api && PYTHONPATH=src python scripts/send_test_push.py --driver-id <uuid> --list-only

On production droplet:
    docker compose exec -T api python -w /app/apps/api scripts/send_test_push.py \\
      --email priya.sharma@porterchain.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from porterchain_api.admin_models import Driver
from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.notification_engine.device_service import DeviceService
from porterchain_api.notification_engine.fcm_service import FCMService, firebase_credentials_configured
from porterchain_shared.config.settings import get_platform_settings


def _resolve_driver(db, *, email: str | None, driver_id: str | None) -> Driver | None:
    if driver_id:
        return db.get(Driver, driver_id)
    if email:
        return db.query(Driver).filter(Driver.email == email).first()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Send test FCM push to a driver's registered devices")
    parser.add_argument("--email", help="Driver email (e.g. priya.sharma@porterchain.com)")
    parser.add_argument("--driver-id", help="Driver UUID")
    parser.add_argument("--title", default="Porterchain test", help="Notification title")
    parser.add_argument("--body", default="Push test from send_test_push.py", help="Notification body")
    parser.add_argument("--list-only", action="store_true", help="List devices without sending")
    args = parser.parse_args()

    if not args.email and not args.driver_id:
        parser.error("Provide --email or --driver-id")

    init_db()
    settings = get_settings()
    platform = get_platform_settings()
    devices_svc = DeviceService()
    fcm = FCMService()

    with SessionLocal() as db:
        driver = _resolve_driver(db, email=args.email, driver_id=args.driver_id)
        if not driver:
            print(f"✗ driver not found (email={args.email!r}, id={args.driver_id!r})")
            return 1

        devices = devices_svc.list_active(db, user_role="driver", user_id=driver.id)
        print(f"Driver: {driver.email} ({driver.id})")
        print(f"Push: enabled={platform.push_enabled} send={platform.push_send} firebase={firebase_credentials_configured()}")
        print(f"Active devices: {len(devices)}")
        for d in devices:
            token_preview = d.fcm_token[:28] + "…" if len(d.fcm_token) > 28 else d.fcm_token
            print(f"  - {d.id} {d.platform} {token_preview} last_seen={d.last_seen_at}")

        if args.list_only:
            return 0 if devices else 2

        if not devices:
            print("✗ no active devices — open driver app on device and tap Settings → Register push")
            return 2

        if not platform.push_send and settings.app_env not in ("local", "development", "test"):
            print("✗ PORTERCHAIN_PUSH_SEND is false — enable in prod .env / GitHub vars")
            return 3

        sent = 0
        failed = 0
        for d in devices:
            if d.platform == "web" and not d.fcm_token.startswith("web-"):
                pass  # still try — some web tokens are real FCM
            ok, err, invalid = fcm.send(
                d.fcm_token,
                title=args.title,
                body=args.body,
                data={"type": "test", "source": "send_test_push"},
            )
            if invalid:
                devices_svc.invalidate_token(db, d.fcm_token)
            if ok:
                sent += 1
                print(f"✓ sent to {d.platform} {d.id}")
            else:
                failed += 1
                print(f"✗ failed {d.platform} {d.id}: {err}")

        db.commit()
        print(f"Done: {sent} sent, {failed} failed")
        return 0 if sent and not failed else (4 if failed else 5)


if __name__ == "__main__":
    raise SystemExit(main())
