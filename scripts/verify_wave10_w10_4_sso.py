#!/usr/bin/env python3
"""Wave 10 w10-4 guard — Keycloak OAuth-capable merchant portal (not acquisition-page SSO)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUSINESS_HERO = ROOT / "website/src/components/marketing/business/sections/BusinessHero.tsx"
BUSINESS_FINAL = ROOT / "website/src/components/marketing/business/sections/FinalCta.tsx"
LOGIN = ROOT / "website/src/app/[locale]/login/[[...sign-in]]/page.tsx"
UNIFIED = ROOT / "website/src/components/portal/UnifiedSignIn.tsx"
MERCHANT_SIGNIN = ROOT / "apps/merchant-portal/src/app/sign-in/[[...sign-in]]/page.tsx"
MERCHANT_SIGNUP = ROOT / "apps/merchant-portal/src/app/sign-up/[[...sign-up]]/page.tsx"
SHARED_PANEL = ROOT / "packages/auth/src/KeycloakSignInPanel.tsx"
KEYCLOAK_THEMES = ROOT / "infrastructure/keycloak/themes"
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

    # Keycloak hosted login (OIDC redirect): the shared panel starts the flow; the look
    # comes from the Porterchain Keycloak theme, not an embedded widget appearance prop.
    if "KeycloakSignInPanel" not in unified:
        failures.append("UnifiedSignIn missing shared KeycloakSignInPanel")
    login_catch_all = ROOT / "website/src/app/[locale]/login/[[...sign-in]]/page.tsx"
    if not login_catch_all.is_file():
        failures.append("website login missing [[...sign-in]] catch-all for Keycloak path routing")

    if not SHARED_PANEL.is_file() or "export function KeycloakSignInPanel" not in SHARED_PANEL.read_text(
        encoding="utf-8"
    ):
        failures.append("packages/auth KeycloakSignInPanel missing shared sign-in entry")
    if not KEYCLOAK_THEMES.is_dir() or not any(KEYCLOAK_THEMES.iterdir()):
        failures.append("infrastructure/keycloak/themes missing Porterchain login theme")

    if not PORTAL_AUTH_SCREEN.is_file() or "PortalAuthScreen" not in PORTAL_AUTH_SCREEN.read_text(
        encoding="utf-8"
    ):
        failures.append("packages/auth PortalAuthScreen missing shared auth chrome")

    signin = MERCHANT_SIGNIN.read_text(encoding="utf-8")
    if "KeycloakSignInPanel" not in signin:
        failures.append("merchant SignIn missing shared KeycloakSignInPanel")
    if "PortalAuthScreen" not in signin and "MerchantAuthScreen" not in signin:
        failures.append("merchant SignIn must use PortalAuthScreen or MerchantAuthScreen shell")

    signup = MERCHANT_SIGNUP.read_text(encoding="utf-8")
    if "KeycloakSignInPanel" not in signup or 'mode="sign-up"' not in signup:
        failures.append("merchant SignUp missing Keycloak sign-up (registration) panel")
    if "PortalAuthScreen" not in signup and "MerchantAuthScreen" not in signup:
        failures.append("merchant SignUp must use PortalAuthScreen or MerchantAuthScreen shell")

    print("Wave 10 w10-4 guard (Keycloak SSO — portal only, not /business acquisition)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: Keycloak-themed merchant portal sign-in; shared PortalAuthScreen; no SSO on /business")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
