#!/usr/bin/env python3
"""Wave 3 — classify every FastAPI operation (Keep / banned-absent).

SSOT: docs/api/openapi.json (same spec as http://localhost:8001/docs).
Optional: OPENAPI_URL=http://127.0.0.1:8001/openapi.json for a live dump.

Every path+method must match a persona prefix. Banned aliases must be absent
(legacy /driver/location, duplicate merchant track, invoice /resend).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/api/openapi.json"

# One public interface per persona. New prefixes fail CI.
_KEEP_PREFIXES: tuple[str, ...] = (
    "/v1/admin",
    "/v1/merchant-api",
    "/v1/merchant",
    "/driver-api/v1",
    "/v1/auth",
    "/v1/notifications",
    "/v1/pricing",
    "/v1/public",
    "/v1/customers",
    "/v1/booking-drafts",
    "/v1/quotes",
    "/v1/bookings",
    "/v1/orders",
    "/v1/payments",
    "/v1/oauth",
    "/v1/integrations",
    "/v1/security",
    "/webhooks",
    "/health",
    "/metrics",
    "/internal",
)

# Proven extras (Wave 3). Must not reappear in OpenAPI.
_BANNED: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/driver/location"),
        ("GET", "/v1/merchant/tracking/orders/{order_id}"),
        ("POST", "/v1/merchant/billing/invoices/{invoice_id}/resend"),
    }
)

# Untagged ops are allowed only for probes. New untagged business paths fail.
_UNTAGGED_OK_PREFIXES: tuple[str, ...] = ("/health", "/metrics", "/internal")

_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def _load_spec() -> dict:
    url = (os.environ.get("OPENAPI_URL") or "").strip()
    if url:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    if not SNAPSHOT.is_file():
        raise SystemExit(f"missing OpenAPI snapshot: {SNAPSHOT}")
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def _persona(path: str) -> str | None:
    # Longest prefix wins so /v1/merchant-api is not swallowed by /v1/merchant.
    matches = [p for p in _KEEP_PREFIXES if path == p or path.startswith(p + "/")]
    if not matches:
        return None
    return max(matches, key=len)


def _iter_ops(spec: dict) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for path, item in sorted((spec.get("paths") or {}).items()):
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() not in _METHODS:
                continue
            tags = (op or {}).get("tags") or ["(untagged)"]
            rows.append((method.upper(), path, str(tags[0])))
    return rows


def main() -> int:
    spec = _load_spec()
    rows = _iter_ops(spec)
    failures: list[str] = []
    keep = 0
    by_prefix: dict[str, int] = {}

    for method, path, tag in rows:
        key = (method, path)
        if key in _BANNED:
            failures.append(f"banned alias still published: {method} {path} [{tag}]")
            continue
        prefix = _persona(path)
        if prefix is None:
            failures.append(f"unclassified prefix: {method} {path} [{tag}]")
            continue
        if tag == "(untagged)" and not any(
            path == p or path.startswith(p + "/") for p in _UNTAGGED_OK_PREFIXES
        ):
            failures.append(f"untagged path: {method} {path}")
            continue
        keep += 1
        by_prefix[prefix] = by_prefix.get(prefix, 0) + 1

    print("OpenAPI census (Wave 3 HTTP surface)")
    print(f"  source: {'OPENAPI_URL' if os.environ.get('OPENAPI_URL') else SNAPSHOT.relative_to(ROOT)}")
    print(f"  operations: {len(rows)}  keep: {keep}  banned_list: {len(_BANNED)}")
    for prefix, count in sorted(by_prefix.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:4d}  {prefix}")

    if failures:
        print("  FAIL:")
        for item in failures:
            print(f"    - {item}")
        return 1
    if keep != len(rows):
        print("  FAIL: keep count mismatch")
        return 1
    print("  PASS: every /docs operation classified; banned aliases absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
