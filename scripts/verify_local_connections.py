#!/usr/bin/env python3
"""Local connection health — no secret values printed.

Required stack for this Mac. Optional vendors (NVIDIA, Shopify, Zoho, Checkr,
Sentry, lead webhooks, Apple ASC) are not probed. :5433 is not PorterChain.
"""

from __future__ import annotations

import socket
import sys
import urllib.error
import urllib.request

CHECKS: list[tuple[str, str]] = [
    ("Postgres", "tcp://127.0.0.1:5432"),
    ("Redis", "tcp://127.0.0.1:6379"),
    ("Mailpit SMTP", "tcp://127.0.0.1:1025"),
    ("Mailpit UI", "http://127.0.0.1:8025"),
    ("SpiceDB", "tcp://127.0.0.1:50051"),
    ("Valhalla", "http://127.0.0.1:8002/status"),
    ("OSRM loopback", "http://127.0.0.1:5000/health"),
    ("PorterChain API", "http://127.0.0.1:8001/health"),
]


def tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            code = getattr(resp, "status", 200)
            return 200 <= code < 500, str(code)
    except urllib.error.HTTPError as exc:
        # Service is up if it answers (401/404 still means the port is ours).
        return exc.code < 500, str(exc.code)
    except Exception as exc:  # noqa: BLE001 — health probe
        return False, type(exc).__name__


def main() -> int:
    failed = 0
    print("PorterChain local connections (docs/CONNECTIONS.md)")
    for label, target in CHECKS:
        if target.startswith("tcp://"):
            host, port_s = target.removeprefix("tcp://").rsplit(":", 1)
            ok = tcp_open(host, int(port_s))
            detail = "open" if ok else "closed"
        else:
            ok, detail = http_ok(target)
        mark = "OK" if ok else "DOWN"
        if not ok:
            failed += 1
        print(f"  {mark:4}  {label:22}  {target}  ({detail})")

    crm = tcp_open("127.0.0.1", 5433)
    print(
        f"  {'note':4}  {'crm-postgres :5433':22}  "
        f"{'listening — not PorterChain' if crm else 'not listening'}"
    )
    if failed:
        print(f"\n{failed} required check(s) down. See docs/CONNECTIONS.md.")
        return 1
    print("\nRequired local connections are up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
