#!/usr/bin/env python3
"""Live driver-api contract smoke — Jeff Dean bar for localhost/API connectivity.

Requires API on :8001 (or DRIVER_API_BASE). Uses Bearer dev by default.
Exits 0 when all required probes succeed; expected 404s listed separately.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

BASE = os.environ.get("DRIVER_API_BASE", "http://127.0.0.1:8001").rstrip("/")
TOKEN = os.environ.get("DRIVER_API_TOKEN", "dev")
# When set, prefer local X-Driver-Id bypass (no Bearer) so an onboarded seed
# can be targeted — Bearer "dev" always binds .first() APPROVED driver.
DRIVER_ID = (os.environ.get("DRIVER_API_DRIVER_ID") or "").strip() or None

# (method, path, body|None, accept: set[int])
PROBES: list[tuple[str, str, dict[str, Any] | None, set[int]]] = [
    ("GET", "/health", None, {200}),
    ("GET", "/health/status", None, {200}),
    ("GET", "/driver-api/v1/me", None, {200}),
    ("GET", "/driver-api/v1/dashboard", None, {200}),
    ("GET", "/driver-api/v1/jobs", None, {200}),
    ("GET", "/driver-api/v1/shift", None, {200}),
    ("GET", "/driver-api/v1/profile", None, {200}),
    ("GET", "/driver-api/v1/wallet", None, {200}),
    ("GET", "/driver-api/v1/earnings", None, {200}),
    ("GET", "/driver-api/v1/earnings/today", None, {200}),
    ("GET", "/driver-api/v1/earnings/statements", None, {200}),
    ("GET", "/driver-api/v1/support/hub", None, {200}),
    ("GET", "/driver-api/v1/support/knowledge-base", None, {200}),
    ("GET", "/driver-api/v1/communications", None, {200}),
    ("GET", "/driver-api/v1/communications/notifications", None, {200}),
    ("GET", "/driver-api/v1/communications/notifications/history", None, {200}),
    ("GET", "/driver-api/v1/communications/offline", None, {200}),
    ("GET", "/driver-api/v1/routes/assigned", None, {200}),
    ("GET", "/driver-api/v1/navigation/session", None, {200}),
    ("GET", "/driver-api/v1/navigation/route", None, {200, 404}),  # 404 = no route
    ("GET", "/driver-api/v1/offline/pending", None, {200}),
    ("GET", "/driver-api/v1/onboarding", None, {200}),
    ("GET", "/driver-api/v1/vehicle", None, {200}),
    ("GET", "/driver-api/v1/insurance", None, {200}),
    ("GET", "/driver-api/v1/training", None, {200}),
    ("GET", "/driver-api/v1/documents", None, {200}),
    ("GET", "/driver-api/v1/bonuses", None, {200}),
    ("GET", "/driver-api/v1/ratings", None, {200}),
    ("GET", "/driver-api/v1/performance", None, {200}),
    ("GET", "/driver-api/v1/jobs/history", None, {200}),
    ("GET", "/driver-api/v1/incidents", None, {200}),
    ("GET", "/driver-api/v1/support", None, {200}),
    ("GET", "/driver-api/v1/support/claims", None, {200}),
    ("GET", "/driver-api/v1/support/emergency-contact", None, {200}),
    ("POST", "/driver-api/v1/availability", {"mode": "idle"}, {200}),
    ("POST", "/driver-api/v1/communications/notifications/mark-all-read", {}, {200}),
    ("POST", "/driver-api/v1/offline/sync", {}, {200}),
    ("POST", "/driver-api/v1/communications/offline/retry", {}, {200}),
    ("POST", "/driver-api/v1/push/unregister", {}, {200}),
    (
        "POST",
        "/driver-api/v1/location",
        {
            "lat": 43.6532,
            "lng": -79.3832,
            "accuracy_m": 15.0,
            "heading": 0.0,
            "speed_mps": 0.0,
        },
        {200},
    ),
]


def _call(method: str, path: str, body: dict[str, Any] | None) -> tuple[int, str]:
    data = None if body is None else json.dumps(body).encode()
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    # Health is public; driver routes need either Bearer or X-Driver-Id (local bypass).
    if not path.startswith("/health"):
        if DRIVER_ID:
            headers["X-Driver-Id"] = DRIVER_ID
        else:
            headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            return res.status, res.read().decode("utf-8", "replace")[:180]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:180]
    except Exception as exc:  # noqa: BLE001 — smoke surface
        return 0, str(exc)


def main() -> int:
    failures: list[str] = []
    auth_label = f"X-Driver-Id={DRIVER_ID!r}" if DRIVER_ID else f"token={TOKEN!r}"
    print(f"Driver API live smoke ({BASE}, {auth_label})")
    for method, path, body, accept in PROBES:
        code, snippet = _call(method, path, body)
        ok = code in accept
        mark = "OK" if ok else "FAIL"
        print(f"  {mark} {code:>3} {method:4} {path}")
        if not ok:
            failures.append(f"{method} {path} -> {code} (want {sorted(accept)}): {snippet}")

    # Soft check: mobile.driver policy present on health/status
    try:
        req = urllib.request.Request(f"{BASE}/health/status", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as res:
            payload = json.loads(res.read().decode())
        mobile = (payload.get("mobile") or {}).get("driver") or {}
        if not mobile.get("min_version"):
            failures.append("health/status missing mobile.driver.min_version")
        else:
            print(f"  OK  policy mobile.driver min_version={mobile.get('min_version')}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"health/status mobile.driver check failed: {exc}")

    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print(f"  PASS: {len(PROBES)} probes accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
