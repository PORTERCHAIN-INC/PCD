#!/usr/bin/env python3
"""Wave 10 w10-4 guard — Clerk OAuth-capable merchant portal (not acquisition-page SSO)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUSINESS_HERO = ROOT / "website/src/components/business/sections/BusinessHero.tsx"
BUSINESS_FINAL = ROOT / "website/src/components/business/sections/FinalCta.tsx"
LOGIN = ROOT / "website/src/app/[locale]/login/page.tsx"
UNIFIED = ROOT / "website/src/components/portal/UnifiedSignIn.tsx"
OAUTH_PAGE = ROOT / "apps/merchant-portal/src/app/sign-in/oauth/[provider]/page.tsx"
MERCHANT_SIGNIN = ROOT / "apps/merchant-portal/src/app/sign-in/[[...sign-in]]/page.tsx"
MERCHANT_SIGNUP = ROOT / "apps/merchant-portal/src/app/sign-up/[[...sign-up]]/page.tsx"
CLERK_APPEARANCE = ROOT / "website/src/lib/clerk-appearance.ts"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("BusinessHero", BUSINESS_HERO),
        ("FinalCta", BUSINESS_FINAL),
    ):
        text = path.read_text(encoding="utf-8")
        if "MerchantSsoButtons" in text or "Already onboarding" in text:
            failures.append(f"{label} must not expose merchant SSO on capacity acquisition page")

    login = LOGIN.read_text(encoding="utf-8")
    if "PostAuthPortalRedirect" not in login and "login/continue" not in login:
        failures.append("login page missing post-auth continue / module routing")
    if "MerchantSsoButtons" in login or "LoginBrandPanel" in login:
        failures.append("login page must not use portal picker / MerchantSsoButtons chrome")

    unified = UNIFIED.read_text(encoding="utf-8")
    if "MerchantSsoButtons" in unified:
        failures.append("UnifiedSignIn must use Clerk SignIn only — no duplicate OAuth buttons")
    if "<SignIn" not in unified or "porterchainClerkAppearance" not in unified:
        failures.append("UnifiedSignIn missing Clerk SignIn with themed appearance")

    oauth = OAUTH_PAGE.read_text(encoding="utf-8")
    if "authenticateWithRedirect" not in oauth or "oauth_google" not in oauth:
        failures.append("merchant OAuth kickoff page missing authenticateWithRedirect")

    signin = MERCHANT_SIGNIN.read_text(encoding="utf-8")
    if "porterchainClerkAppearance" not in signin or "<SignIn" not in signin:
        failures.append("merchant SignIn missing themed Clerk widget")

    signup = MERCHANT_SIGNUP.read_text(encoding="utf-8")
    if "<SignUp" not in signup or "porterchainClerkAppearance" not in signup:
        failures.append("merchant SignUp missing OAuth-capable Clerk widget")

    appearance = CLERK_APPEARANCE.read_text(encoding="utf-8")
    if "porterchainClerkAppearance" not in appearance:
        failures.append("clerk-appearance.ts missing shared theme export")

    print("Wave 10 w10-4 guard (Clerk SSO — portal only, not /business acquisition)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: Clerk-themed merchant portal sign-in; no SSO on /business quote paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
