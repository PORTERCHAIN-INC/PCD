#!/usr/bin/env python3
"""Wave 10 w10-4 guard — Clerk OAuth-capable merchant portal (not acquisition-page SSO)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUSINESS_HERO = ROOT / "website/src/components/business/sections/BusinessHero.tsx"
BUSINESS_FINAL = ROOT / "website/src/components/business/sections/FinalCta.tsx"
LOGIN = ROOT / "website/src/app/[locale]/login/[[...sign-in]]/page.tsx"
UNIFIED = ROOT / "website/src/components/portal/UnifiedSignIn.tsx"
MERCHANT_SIGNIN = ROOT / "apps/merchant-portal/src/app/sign-in/[[...sign-in]]/page.tsx"
MERCHANT_SIGNUP = ROOT / "apps/merchant-portal/src/app/sign-up/[[...sign-up]]/page.tsx"
SHARED_APPEARANCE = ROOT / "packages/auth/src/clerkAppearance.ts"
PORTAL_AUTH_SCREEN = ROOT / "packages/auth/src/PortalAuthScreen.tsx"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("BusinessHero", BUSINESS_HERO),
        ("FinalCta", BUSINESS_FINAL),
    ):
        text = path.read_text(encoding="utf-8")
        # Regression: deleted merchant SSO chrome must not return on capacity pages
        if "MerchantSsoButtons" in text or "Already onboarding" in text:
            failures.append(f"{label} must not expose merchant SSO on capacity acquisition page")

    login = LOGIN.read_text(encoding="utf-8")
    if "PostAuthPortalRedirect" not in login and "login/continue" not in login:
        failures.append("login page missing post-auth continue / module routing")
    if "LoginBrandPanel" in login:
        failures.append("login page must not use deleted LoginBrandPanel chrome")

    unified = UNIFIED.read_text(encoding="utf-8")

    if "<SignIn" not in unified or "porterchainClerkAppearance" not in unified:
        failures.append("UnifiedSignIn missing Clerk SignIn with themed appearance")
    login_catch_all = ROOT / "website/src/app/[locale]/login/[[...sign-in]]/page.tsx"
    if not login_catch_all.is_file():
        failures.append("website login missing [[...sign-in]] catch-all for Clerk path routing")

    if not SHARED_APPEARANCE.is_file() or "porterchainClerkAppearance" not in SHARED_APPEARANCE.read_text(
        encoding="utf-8"
    ):
        failures.append("packages/auth clerkAppearance missing shared theme")

    if not PORTAL_AUTH_SCREEN.is_file() or "PortalAuthScreen" not in PORTAL_AUTH_SCREEN.read_text(
        encoding="utf-8"
    ):
        failures.append("packages/auth PortalAuthScreen missing shared auth chrome")

    signin = MERCHANT_SIGNIN.read_text(encoding="utf-8")
    if "porterchainClerkAppearance" not in signin or "<SignIn" not in signin:
        failures.append("merchant SignIn missing themed Clerk widget")
    if "PortalAuthScreen" not in signin:
        failures.append("merchant SignIn must use PortalAuthScreen shell")

    signup = MERCHANT_SIGNUP.read_text(encoding="utf-8")
    if "<SignUp" not in signup or "porterchainClerkAppearance" not in signup:
        failures.append("merchant SignUp missing OAuth-capable Clerk widget")
    if "PortalAuthScreen" not in signup:
        failures.append("merchant SignUp must use PortalAuthScreen shell")

    print("Wave 10 w10-4 guard (Clerk SSO — portal only, not /business acquisition)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: Clerk-themed merchant portal sign-in; shared PortalAuthScreen; no SSO on /business")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
