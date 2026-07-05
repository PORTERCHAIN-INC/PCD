#!/usr/bin/env python3
"""Verify D2 surface contracts — customer + driver API alignment."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# D2 deletions — must stay absent (Appendix D2 accidental complexity).
FORBIDDEN_PATHS: tuple[Path, ...] = (
    ROOT / "apps/admin/src/app/(ops)/crm",
    ROOT / "apps/admin/src/app/(ops)/routes",
    ROOT / "apps/admin/src/app/(ops)/reports",
    ROOT / "apps/admin/src/components/routes",
    ROOT / "website/src/app/[locale]/portal/customer",
    ROOT / "apps/merchant",
    ROOT / "apps/driver",
    ROOT / "apps/api/src/porterchain_api/reporting_engine",
)

CRM_CLIENT = ROOT / "apps/admin/src/lib/crm.ts"

CUSTOMER_WEB = ROOT / "apps/customer/src/lib/api.ts"
CUSTOMER_MOBILE = ROOT / "shared/api/src/customer.ts"
DRIVER_WEB_PROXY = ROOT / "apps/driver-portal/src/app/api/driver/[...path]/route.ts"
DRIVER_MOBILE = ROOT / "shared/api/src/driver.ts"


def _customer_paths(path: Path) -> set[str]:
    text = path.read_text()
    paths = set(re.findall(r"/v1/customers/me/[a-z/_${}]+", text))
    paths |= {m.replace("${v1}", "/v1") for m in re.findall(r"\$\{v1\}/customers/me/[a-z/_${}-]+", text)}
    return paths


def _driver_paths(path: Path) -> set[str]:
    text = path.read_text()
    raw = set(re.findall(r"\$\{base\}/[a-z0-9_/${}-]+", text))
    return {p.replace("${base}", "/driver-api/v1") for p in raw}


def _check_filesystem() -> list[str]:
    failures: list[str] = []
    for path in FORBIDDEN_PATHS:
        if path.exists():
            failures.append(f"forbidden path present: {path.relative_to(ROOT)}")
    if CRM_CLIENT.exists():
        text = CRM_CLIENT.read_text()
        if 'const B = "/v1/admin/crm"' in text or "export const crm" in text:
            failures.append("crm.ts still contains dead /v1/admin/crm client")
    return failures


def main() -> int:
    failures: list[str] = _check_filesystem()

    web_customer = _customer_paths(CUSTOMER_WEB)
    mobile_customer = _customer_paths(CUSTOMER_MOBILE)

    for required in ("/v1/customers/me/dashboard", "/v1/customers/me/support"):
        if required not in web_customer:
            failures.append(f"customer web missing {required}")
        if required not in mobile_customer:
            failures.append(f"customer mobile missing {required}")

    driver_proxy = DRIVER_WEB_PROXY.read_text()
    if "/driver-api/v1" not in driver_proxy:
        failures.append("driver-portal proxy missing /driver-api/v1")

    mobile_driver = _driver_paths(DRIVER_MOBILE)
    required_driver = {
        "/driver-api/v1/auth/login",
        "/driver-api/v1/jobs",
        "/driver-api/v1/me",
        "/driver-api/v1/dashboard",
    }
    missing_driver = required_driver - mobile_driver
    if missing_driver:
        failures.append(f"mobile-driver missing paths: {sorted(missing_driver)}")

    print("D2 verification (filesystem + contracts)")
    if not failures:
        print(f"  filesystem: {len(FORBIDDEN_PATHS)} forbidden paths absent")
    print(f"  customer web: {sorted(web_customer)}")
    print(f"  customer mobile: {sorted(mobile_customer)}")
    print(f"  driver mobile sample: {len(mobile_driver)} paths")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  PASS: customer + driver surfaces share Porterchain API contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
