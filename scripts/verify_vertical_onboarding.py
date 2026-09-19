#!/usr/bin/env python3
"""§8.1.12 — Merchant onboarding vertical selector."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERTICALS = ROOT / "apps/api/src/porterchain_api/merchant_engine/verticals.py"
ONBOARDING = ROOT / "apps/api/src/porterchain_api/auth/merchant_onboarding.py"
AUTH_ROUTER = ROOT / "apps/api/src/porterchain_api/routers/auth.py"
SCHEMA = ROOT / "apps/api/src/porterchain_api/schemas_auth.py"
WEBSITE = ROOT / "website/src/lib/solutions-verticals.ts"
PORTAL_LIB = ROOT / "apps/merchant-portal/src/lib/onboarding.ts"
PORTAL_UI = ROOT / "apps/merchant-portal/src/components/onboarding/PortalOnboardingView.tsx"
TEST = ROOT / "apps/api/tests/test_merchant_verticals.py"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("verticals module", VERTICALS),
        ("onboarding eval", ONBOARDING),
        ("auth router", AUTH_ROUTER),
        ("auth schema", SCHEMA),
        ("website verticals", WEBSITE),
        ("portal lib", PORTAL_LIB),
        ("portal UI", PORTAL_UI),
        ("unit test", TEST),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    onboarding = ONBOARDING.read_text(encoding="utf-8")
    if "business_vertical" not in onboarding or "save_merchant_vertical" not in onboarding:
        failures.append("merchant_onboarding missing vertical step or save handler")

    router = AUTH_ROUTER.read_text(encoding="utf-8")
    if "/merchant/onboarding/vertical" not in router:
        failures.append("auth router missing PATCH /merchant/onboarding/vertical")

    website = WEBSITE.read_text(encoding="utf-8")
    for slug in ("construction", "medical", "food-beverage", "wholesale"):
        if slug not in website:
            failures.append(f"website solutions missing vertical {slug!r}")

    portal = PORTAL_UI.read_text(encoding="utf-8")
    if "Select your business vertical" not in portal or "onSaveVertical" not in portal:
        failures.append("PortalOnboardingView missing vertical picker")

    print("Vertical onboarding guard (§8.1.12)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — API vertical step, PATCH endpoint, merchant onboarding UI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
