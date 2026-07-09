#!/usr/bin/env python3
"""§3.1.1 — router business-logic audit (reports legacy debt + blocks new violations)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SCRIPTS = ROOT / "apps/api/scripts"
sys.path.insert(0, str(API_SCRIPTS))

from verify_d2_contracts import (  # noqa: E402
    _LEGACY_ROUTER_LOGIC,
    _LEGACY_ROUTER_LOC,
    _check_router_business_logic,
    _check_router_raw_sql,
    _check_router_star_imports,
    _check_router_thinness,
    _router_scan_files,
    _rel_router,
)


def main() -> int:
    routers = _router_scan_files()
    logic_legacy = sorted(_LEGACY_ROUTER_LOGIC)
    loc_legacy = sorted(_LEGACY_ROUTER_LOC)

    print("Router audit (§3.1.1)")
    print(f"  router modules scanned: {len(routers)}")
    print(f"  legacy business-logic allowlist: {len(logic_legacy)}")
    for rel in logic_legacy:
        print(f"    - {rel}")
    print(f"  legacy LOC allowlist (>350): {len(loc_legacy)}")

    failures = (
        _check_router_star_imports()
        + _check_router_raw_sql()
        + _check_router_business_logic()
        + _check_router_thinness()
    )

    clean = [rel for rel in sorted({_rel_router(p) for p in routers}) if rel not in _LEGACY_ROUTER_LOGIC]
    print(f"  thin routers (no legacy logic debt): {len(clean)}")

    if failures:
        print("  FAIL:")
        for item in failures:
            print(f"    - {item}")
        return 1

    print("  PASS: no new router business logic / SQL / star-import violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
