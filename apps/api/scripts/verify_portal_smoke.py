#!/usr/bin/env python3
"""Local portal smoke — HTTP checks for dev layer (§2.1.9)."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("PORTERCHAIN_API_URL", "http://localhost:8001").rstrip("/")
PORTALS = (
    ("website", os.environ.get("WEBSITE_URL", "http://localhost:3000")),
    ("merchant", os.environ.get("MERCHANT_URL", "http://localhost:3001")),
    ("admin", os.environ.get("ADMIN_URL", "http://localhost:3002")),
    ("driver", os.environ.get("DRIVER_URL", "http://localhost:3003")),
    ("customer", os.environ.get("CUSTOMER_URL", "http://localhost:3004")),
)


def _get(url: str, headers: dict | None = None) -> int:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> int:
    failures: list[str] = []

    health = _get(f"{API}/health/ready")
    if health != 200:
        failures.append(f"API health {health}")

    admin = _get(f"{API}/v1/auth/admin/access", {"Authorization": "Bearer dev"})
    if admin != 200:
        failures.append(f"admin API gate {admin}")

    merchant = _get(f"{API}/v1/merchant/dashboard", {"Authorization": "Bearer dev"})
    if merchant != 200:
        failures.append(f"merchant API gate {merchant}")

    for name, base in PORTALS:
        code = _get(base)
        if code not in (200, 307, 308):
            failures.append(f"{name} portal {code} ({base})")

    print("Portal smoke (§2.1.9)")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  PASS: API gates + portal HTTP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
