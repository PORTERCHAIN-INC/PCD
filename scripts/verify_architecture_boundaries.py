#!/usr/bin/env python3
"""§3.1.2–3.1.4 — architecture boundary guards (no vendor dispatch HTTP, Stripe, UI API)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"

WEB_APP_ROOTS = (
    ROOT / "apps/admin/src",
    ROOT / "apps/merchant-portal/src",
    ROOT / "apps/driver-portal/src",
    ROOT / "apps/customer/src",
    ROOT / "website/src",
)

UI_API_LIB = (
    ROOT / "apps/admin/src/lib/api.ts",
    ROOT / "apps/merchant-portal/src/lib/api.ts",
    ROOT / "apps/driver-portal/src/lib/api.ts",
    ROOT / "apps/customer/src/lib/api.ts",
    ROOT / "website/src/lib/api.ts",
)

# Config may still hold retired FLEETBASE_* field names until a later migration.
_FLEETBASE_URL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "config.py",
        "admin_engine/diagnostics_health.py",
        "auth/sso_service.py",
    }
)

_STRIPE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "services/python/porterchain_services/stripe/sdk.py",
        "apps/api/scripts/verify_p0_loop.py",
    }
)

_STRIPE_SCAN_ROOTS: tuple[Path, ...] = (
    API_SRC,
    ROOT / "services/python/porterchain_services",
    ROOT / "apps/api/scripts",
)

_UI_FLEETBASE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "apps/admin/src/lib/system-links.ts",
    }
)

_API_BASE_MARKERS = (
    "porterchainApiUrl",
    "PORTERCHAIN_API_URL",
    "getPorterchainApiBase",
    "localhost:8001",
    "api.porterchain.com",
    "/api/driver",
)


def _rel_api(path: Path) -> str:
    return str(path.relative_to(API_SRC))


def _check_fleetbase_http() -> list[str]:
    failures: list[str] = []
    for path in sorted(API_SRC.rglob("*.py")):
        rel = _rel_api(path)
        if rel in _FLEETBASE_URL_ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "import httpx" not in text and "httpx." not in text:
            continue
        if "fleetbase_api_url" in text or re.search(r":8000", text):
            failures.append(f"§3.1.2 Fleetbase HTTP outside adapter allowlist: {rel}")
    return failures


def _check_stripe_services() -> list[str]:
    failures: list[str] = []
    for root in _STRIPE_SCAN_ROOTS:
        if not root.exists():
            failures.append(f"§3.1.3 missing Stripe scan root: {root.relative_to(ROOT)}")
            continue
        for path in sorted(root.rglob("*.py")):
            rel = str(path.relative_to(ROOT))
            if rel in _STRIPE_ALLOWLIST:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"(^|\n)\s*import stripe|from stripe", text):
                failures.append(f"§3.1.3 stripe import outside SDK allowlist: {rel}")
    return failures


def _check_ui_fleetbase() -> list[str]:
    failures: list[str] = []
    for root in WEB_APP_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
                continue
            rel = str(path.relative_to(ROOT))
            if rel in _UI_FLEETBASE_ALLOWLIST:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if ":8000" in text and "NEXT_PUBLIC_FLEETBASE" not in text:
                failures.append(f"§3.1.2 UI references Fleetbase :8000: {rel}")
            if re.search(r"fetch\([^)]*fleetbase", text, re.IGNORECASE):
                failures.append(f"§3.1.2 UI fetch to Fleetbase: {rel}")
    return failures


def _check_ui_api_base() -> list[str]:
    failures: list[str] = []
    for path in UI_API_LIB:
        if not path.is_file():
            failures.append(f"§3.1.4 missing portal API client: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not any(marker in text for marker in _API_BASE_MARKERS):
            failures.append(f"§3.1.4 lib/api.ts missing Porterchain API base: {path.relative_to(ROOT)}")

    forbidden_api_ports = (":8000", ":3000/api", ":3002/api")
    for root in WEB_APP_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = str(path.relative_to(ROOT))
            if rel in _UI_FLEETBASE_ALLOWLIST or "/api/driver/" in rel:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "fetch(" not in text:
                continue
            for port in forbidden_api_ports:
                if port in text and "system-links" not in rel:
                    failures.append(f"§3.1.4 UI fetch via forbidden port {port}: {rel}")
                    break
    return failures


# Wave 3 — cut aliases must not return in routers or portal clients.
_BANNED_HTTP_ALIASES: tuple[str, ...] = (
    "/driver/location",
    "/v1/merchant/tracking/orders/",
    "/billing/invoices/{invoice_id}/resend",
    "/billing/invoices/${invoiceId}/resend",
)


def _check_banned_http_aliases() -> list[str]:
    failures: list[str] = []
    scan_roots = (API_SRC / "routers",) + WEB_APP_ROOTS
    for root in scan_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            text = path.read_text(encoding="utf-8")
            rel = str(path.relative_to(ROOT))
            for needle in _BANNED_HTTP_ALIASES:
                if needle in text:
                    failures.append(f"banned HTTP alias {needle!r} in {rel}")
    return failures


def main() -> int:
    failures = (
        _check_fleetbase_http()
        + _check_stripe_services()
        + _check_ui_fleetbase()
        + _check_ui_api_base()
        + _check_banned_http_aliases()
    )
    if failures:
        print("Architecture boundary guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Architecture boundary guard passed (§3.1.2–3.1.4).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
