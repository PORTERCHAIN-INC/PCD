#!/usr/bin/env python3
"""§3.4.1 — API replicas must not rely on in-process session or local-only state."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"
MAIN = API_SRC / "main.py"
RATE_LIMIT_MW = API_SRC / "platform/rate_limit_middleware.py"
RATE_LIMIT_CORE = API_SRC / "platform/rate_limit.py"
REALTIME = API_SRC / "notification_engine/realtime.py"
ADR = ROOT / "docs/architecture/ADR-012-scaling.md"


def _scan_forbidden_imports() -> list[str]:
    failures: list[str] = []
    forbidden = (
        "starlette.middleware.sessions",
        "fastapi.middleware.sessions",
    )
    for path in sorted(API_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for mod in forbidden:
            if mod in text:
                rel = path.relative_to(ROOT)
                failures.append(f"§3.4.1 forbidden session middleware import in {rel}")
    return failures


def _check_wiring() -> list[str]:
    failures: list[str] = []
    main_text = MAIN.read_text(encoding="utf-8", errors="ignore")
    if "SessionMiddleware" in main_text:
        failures.append("§3.4.1 main.py must not register SessionMiddleware")
    if "PortalRateLimitMiddleware" not in main_text:
        failures.append("§3.4.1 main.py missing PortalRateLimitMiddleware")
    if "require_redis_for_production" not in main_text:
        failures.append("§3.4.1 main.py must call require_redis_for_production on startup")

    # Redis client lives in rate_limit.py; middleware documents fail-closed + calls it.
    rate_core = RATE_LIMIT_CORE.read_text(encoding="utf-8", errors="ignore")
    rate_mw = RATE_LIMIT_MW.read_text(encoding="utf-8", errors="ignore")
    if "get_redis_client" not in rate_core:
        failures.append("§3.4.1 rate limit must use shared Redis client")
    if "check_fixed_window" not in rate_mw:
        failures.append("§3.4.1 PortalRateLimitMiddleware must call check_fixed_window")
    if "failing closed" not in rate_mw.lower() and "fail closed" not in rate_mw.lower():
        failures.append("§3.4.1 rate limit must document fail-closed behavior")

    rt_text = REALTIME.read_text(encoding="utf-8", errors="ignore")
    if 'CHANNEL = "porterchain:notifications:realtime"' not in rt_text:
        failures.append("§3.4.1 notification realtime missing Redis pub/sub channel")
    if "pubsub" not in rt_text.lower():
        failures.append("§3.4.1 notification realtime must use Redis pub/sub fanout")

    if ADR.is_file():
        adr = ADR.read_text(encoding="utf-8", errors="ignore")
        if "Stateless API prerequisites" not in adr:
            failures.append("§3.4.1 ADR-012 missing Stateless API prerequisites section")

    config_text = (API_SRC / "config.py").read_text(encoding="utf-8", errors="ignore")
    if re.search(r'database_url: str = "sqlite', config_text):
        failures.append("§3.4.1 config.py must not default to SQLite")

    return failures


def main() -> int:
    failures = _scan_forbidden_imports() + _check_wiring()
    if failures:
        print("API stateless guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("API stateless guard passed (§3.4.1 — JWT + Redis coordination, no server sessions).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
