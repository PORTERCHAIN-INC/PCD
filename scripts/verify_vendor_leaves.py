#!/usr/bin/env python3
"""Wave 4 — vendor black boxes and persona leaves.

- Unlabeled public OSRM demo is banned in env/compose/CI.
- VROOM client must not appear under PorterChain engines.
- Mobile leaves fetch PorterChain API only (no Fleetbase / SocketCluster).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"
MAPS = ROOT / "services/python/porterchain_services/maps/service.py"

PUBLIC_OSRM = "router.project-osrm.org"
_PUBLIC_OSRM_ALLOW: frozenset[str] = frozenset(
    {
        "ARCHITECTURE.md",
        "services/python/porterchain_services/maps/service.py",
        "scripts/verify_vendor_leaves.py",
        "integrations.yaml",
        "INTEGRATIONS.md",
    }
)

_VROOM_IMPORT = re.compile(r"(^|\n)\s*(import vroom|from vroom)(\s|$)", re.MULTILINE)

_MOBILE_ROOTS = (
    ROOT / "apps/mobile-driver/src",
    ROOT / "apps/mobile-customer/src",
)


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _check_public_osrm() -> list[str]:
    failures: list[str] = []
    if MAPS.is_file() and "OSRM_PUBLIC_DEMO_LAST_RESORT" not in MAPS.read_text(encoding="utf-8"):
        failures.append("MapsService missing labeled OSRM_PUBLIC_DEMO_LAST_RESORT")

    scan_roots = (
        ROOT / "env",
        ROOT / "infrastructure",
        ROOT / ".github",
        ROOT / "apps/api",
    )
    extra_files = (ROOT / "apps/api/env.example",)
    paths: list[Path] = list(extra_files)
    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".yml", ".yaml", ".env", ".example", ".sh", ".md", ".py"}:
                if path.name not in {"env.example", "nightly-e2e.yml"}:
                    continue
            paths.append(path)

    seen: set[Path] = set()
    for path in paths:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        rel = _rel(path)
        if rel in _PUBLIC_OSRM_ALLOW:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if PUBLIC_OSRM in text:
            failures.append(f"unlabeled public OSRM demo in {rel}")
    return failures


def _check_vroom_client() -> list[str]:
    failures: list[str] = []
    for path in sorted(API_SRC.rglob("*.py")):
        rel = _rel(path)
        if "fleetbase_engine" in rel.replace("\\", "/"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _VROOM_IMPORT.search(text):
            failures.append(f"VROOM client import under engine/API: {rel}")
    return failures


def _check_mobile_leaves() -> list[str]:
    failures: list[str] = []
    for root in _MOBILE_ROOTS:
        if not root.is_dir():
            failures.append(f"missing mobile src: {root.relative_to(ROOT)}")
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = _rel(path)
            text = path.read_text(encoding="utf-8", errors="ignore")
            if ":8000" in text:
                failures.append(f"mobile leaf references Fleetbase :8000: {rel}")
            if re.search(r"socketcluster", text, re.IGNORECASE):
                failures.append(f"mobile leaf imports SocketCluster: {rel}")
            if re.search(r"fetch\([^)]*fleetbase", text, re.IGNORECASE):
                failures.append(f"mobile leaf fetch to Fleetbase: {rel}")
    driver_api = ROOT / "apps/mobile-driver/src/api.ts"
    customer_api = ROOT / "apps/mobile-customer/src/api.ts"
    if driver_api.is_file() and "/driver-api/v1" not in driver_api.read_text(encoding="utf-8"):
        failures.append("mobile-driver api.ts missing /driver-api/v1")
    if customer_api.is_file() and "/v1/orders/" not in customer_api.read_text(encoding="utf-8"):
        failures.append("mobile-customer api.ts missing public /v1/orders/")
    return failures


def main() -> int:
    failures = _check_public_osrm() + _check_vroom_client() + _check_mobile_leaves()
    print("Vendor / leaf contract guard (Wave 4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: local OSRM default; no VROOM client in engines; mobile → :8001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
