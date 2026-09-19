#!/usr/bin/env python3
"""Server-side driver field-proof — FCM readiness + GPS ping path.

Closes what we can without a physical device:
  - Firebase credentials configured
  - Push send flags on
  - /communications reports fcm_configured
  - POST /location accepts a ping (Fleetbase bridge may no-op)

Still requires one human device for: real FCM token register + locked-screen GPS.

Env:
  DRIVER_API_BASE   default http://127.0.0.1:8001
  DRIVER_API_TOKEN  default dev
  DRIVER_FIELD_EMAIL  optional — list devices via send_test_push path when API venv available
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("DRIVER_API_BASE", "http://127.0.0.1:8001").rstrip("/")
TOKEN = os.environ.get("DRIVER_API_TOKEN", "dev")
PUSH_TS = ROOT / "apps/mobile-driver/src/push.ts"
FCM_PY = ROOT / "apps/api/src/porterchain_api/notification_engine/fcm_service.py"


def _assert_job_offer_category_pins() -> None:
    """EAS/live ring proof requires matching Expo category + FCM categoryId."""
    push = PUSH_TS.read_text()
    fcm = FCM_PY.read_text()
    if 'JOB_OFFER_CATEGORY = "job_offer"' not in push:
        raise SystemExit("FAIL: mobile push.ts missing JOB_OFFER_CATEGORY=job_offer")
    if 'JOB_OFFER_CATEGORY_ID = "job_offer"' not in fcm:
        raise SystemExit("FAIL: fcm_service missing JOB_OFFER_CATEGORY_ID=job_offer")
    if "setNotificationCategoryAsync" not in push:
        raise SystemExit("FAIL: mobile push.ts missing lock-screen Accept/Decline category")
    print("  OK job_offer category pins (push.ts ↔ fcm_service)")


def _call(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode()
            try:
                return res.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return res.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return exc.code, raw
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def main() -> int:
    failures: list[str] = []
    print(f"Driver field-proof live ({BASE})")

    try:
        _assert_job_offer_category_pins()
    except SystemExit as exc:
        failures.append(str(exc))

    code, comms = _call("GET", "/driver-api/v1/communications")
    if code != 200 or not isinstance(comms, dict):
        failures.append(f"communications hub failed: {code} {comms!r}")
        push: dict = {}
    else:
        push = comms.get("push") or {}
        print(f"  OK  push firebase_enabled={push.get('firebase_enabled')} fcm_configured={push.get('fcm_configured')}")
        print(f"  OK  registered_devices={push.get('registered_devices', 0)}")
        if not push.get("fcm_configured"):
            failures.append("fcm_configured is false — set FIREBASE_PROJECT_ID + credentials")
        if push.get("firebase_enabled") is False:
            failures.append("firebase_enabled is false")

    # GPS ingest path (Toronto downtown)
    ping_body = {
        "lat": 43.6532,
        "lng": -79.3832,
        "accuracy_m": 12.0,
        "heading": 90.0,
        "speed_mps": 0.0,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    code, loc = _call("POST", "/driver-api/v1/location", ping_body)
    if code != 200:
        failures.append(f"POST /location failed: {code} {loc!r}")
    else:
        print(f"  OK  POST /location accepted ({type(loc).__name__})")

    # Optional: list devices for a known driver via send_test_push
    email = os.environ.get("DRIVER_FIELD_EMAIL", "marco@porterchain.com")
    api = ROOT / "apps/api"
    venv_py = api / ".venv/bin/python"
    script = api / "scripts/send_test_push.py"
    if venv_py.is_file() and script.is_file():
        proc = subprocess.run(
            [str(venv_py), str(script), "--email", email, "--list-only"],
            cwd=str(api),
            capture_output=True,
            text=True,
            check=False,
        )
        print(proc.stdout or "", end="")
        if proc.returncode not in (0, 2):
            failures.append(f"send_test_push --list-only exit {proc.returncode}: {proc.stderr.strip()}")
        elif proc.returncode == 2:
            print("  WARN no FCM devices registered for driver — expected until native app opens")
        else:
            print("  OK  at least one FCM device registered — run send without --list-only to fire")

    print()
    print("  HUMAN (closes #19) — once per platform:")
    print("    1. eas build --profile development-device (iOS) / development (Android)")
    print("    2. Install on phone · open app · Sign in · allow Notifications + Location Always")
    print("    3. Go on duty · lock screen 2 min · confirm dispatch map moves")
    print("    4. cd apps/api && .venv/bin/python scripts/send_test_push.py --email <driver>")
    print("    5. Confirm banner arrives · tap opens job/route")
    print("    6. Optional: MAESTRO_RUN=1 maestro test apps/mobile-driver/maestro/login-and-track.yaml")

    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1

    devices = int(push.get("registered_devices") or 0) if push else 0
    if devices == 0:
        print("  PASS: server FCM+GPS path ready (device registration still pending)")
        return 0

    print(f"  PASS: server ready AND {devices} device(s) registered — fire send_test_push to finish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
