#!/usr/bin/env python3
"""D3 prod smoke — Fowler Sprint F: thin clients reachable against live URLs.

Usage:
    pnpm validate:d3:prod
    python scripts/verify_d3_prod_smoke.py --api-url https://api.porterchain.com
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_API = "https://api.porterchain.com"

SURFACES: tuple[tuple[str, str, tuple[int, ...]], ...] = (
    ("Website (book)", "https://porterchain.com/en", (200,)),
    ("Customer portal", "https://customer.porterchain.com/sign-in", (200,)),
    ("Merchant portal", "https://merchant.porterchain.com/sign-in", (200,)),
    ("Admin portal", "https://admin.porterchain.com/sign-in", (200,)),
    ("Driver portal", "https://driver.porterchain.com", (200, 307, 308)),
    ("OpenAPI docs", "https://api.porterchain.com/docs", (200,)),
)


def _http(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 15.0,
) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = raw
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc.reason)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prod D3 surface smoke checks")
    parser.add_argument("--api-url", default=DEFAULT_API)
    args = parser.parse_args()
    api = args.api_url.rstrip("/")

    print("D3 prod smoke (Fowler Sprint F)")
    print("=" * 60)

    failures: list[str] = []
    warns: list[str] = []

    status, body = _http(f"{api}/health")
    ok = status == 200
    print(f"  [{'PASS' if ok else 'FAIL'}] API /health — HTTP {status}")
    if not ok:
        failures.append("API /health")

    status, ready = _http(f"{api}/health/ready")
    ok = status == 200 and isinstance(ready, dict)
    print(f"  [{'PASS' if ok else 'FAIL'}] API /health/ready — HTTP {status}")
    if ok:
        checks = ready.get("checks", {})
        for key in ("database", "redis", "stripe", "fleetbase", "firebase"):
            if key in checks:
                mark = "PASS" if checks[key] in ("ok", "configured", "bridge_disabled", "push_disabled") else "WARN"
                if mark == "WARN":
                    warns.append(f"ready.{key}={checks[key]}")
                print(f"         {key}: {checks[key]} [{mark}]")
    elif not ok:
        failures.append("API /health/ready")

    for label, url, codes in SURFACES:
        status, _ = _http(url)
        ok = status in codes
        print(f"  [{'PASS' if ok else 'FAIL'}] {label} — HTTP {status} ({url})")
        if not ok:
            failures.append(label)

    quote_body = {
        "pickup": {"formatted": "Prod Smoke Pickup, Toronto ON", "lat": 43.65, "lng": -79.38},
        "dropoff": {"formatted": "Prod Smoke Dropoff, Toronto ON", "lat": 43.66, "lng": -79.40},
        "vehicle_class": "cargoVan",
        "scheduled_at": "2026-07-05T18:00:00Z",
    }
    status, quote = _http(f"{api}/v1/quotes", method="POST", body=quote_body)
    ok = status in (200, 201) and isinstance(quote, dict) and quote.get("quote_id")
    print(
        f"  [{'PASS' if ok else 'FAIL'}] Customer quote path — HTTP {status}"
        + (f" quote_id={quote.get('quote_id')}" if ok else "")
    )
    if not ok:
        failures.append("Customer quote path")

    draft_status, _ = _http(
        f"{api}/v1/booking-drafts",
        method="POST",
        body={"session_id": "d3-prod-smoke"},
    )
    ok = draft_status in (200, 201)
    print(f"  [{'PASS' if ok else 'FAIL'}] Booking draft smoke — HTTP {draft_status}")
    if not ok:
        failures.append("Booking draft smoke")

    print("=" * 60)
    if failures:
        print(f"FAIL: {len(failures)} — {', '.join(failures)}")
        return 1
    if warns:
        print(f"PASS with {len(warns)} warn(s): {', '.join(warns)}")
    else:
        print("PASS: prod surfaces + quote + booking draft smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
