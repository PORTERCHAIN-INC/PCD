#!/usr/bin/env python3
"""§7.1.7 — OAuth 2.0 third-party router guard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OAUTH_ROUTER = ROOT / "apps/api/src/porterchain_api/routers/oauth.py"
OAUTH_SERVICE = ROOT / "apps/api/src/porterchain_api/oauth_engine/oauth_service.py"
MAIN = ROOT / "apps/api/src/porterchain_api/main.py"
MERCHANT_API_AUTH = ROOT / "apps/api/src/porterchain_api/auth/merchant_api.py"


def main() -> int:
    failures: list[str] = []

    for rel in (OAUTH_ROUTER, OAUTH_SERVICE, MAIN, MERCHANT_API_AUTH):
        if not rel.is_file():
            failures.append(f"missing {rel.relative_to(ROOT)}")

    if OAUTH_ROUTER.is_file():
        text = OAUTH_ROUTER.read_text(encoding="utf-8")
        for needle in (
            'prefix="/v1/oauth"',
            "/token",
            "/authorize",
            ".well-known/oauth-authorization-server",
            "client_credentials",
            "authorization_code",
        ):
            if needle not in text:
                failures.append(f"oauth router missing {needle}")

    if MERCHANT_API_AUTH.is_file():
        if "resolve_bearer_token" not in MERCHANT_API_AUTH.read_text(encoding="utf-8"):
            failures.append("merchant_api auth missing Bearer OAuth token support")

    if MAIN.is_file() and "oauth.router" not in MAIN.read_text(encoding="utf-8"):
        failures.append("main.py does not register oauth.router")

    print("OAuth third-party guard (§7.1.7)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: /v1/oauth authorize + token + metadata registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
