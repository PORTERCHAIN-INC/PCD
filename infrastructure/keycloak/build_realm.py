#!/usr/bin/env python3
"""Generate realm-porterchain.json (L36, doc 74 §2-3). Realm as code, NO secrets.

IdP secrets are `${VAR}` placeholders filled by render-realm.sh from SOPS at import time.
Run: python3 infrastructure/keycloak/build_realm.py  (rewrites realm-porterchain.json)
"""
from __future__ import annotations

import json
from pathlib import Path

LOCAL = "http://localhost"
SITES = {
    # client_id: (public base URLs, local port)
    "pc-website": (["https://porterchain.com", "https://www.porterchain.com"], 3000),
    "pc-merchant-portal": (["https://merchant.porterchain.com"], 3001),
    "pc-customer-portal": (["https://customer.porterchain.com"], 3004),
    "pc-driver-portal": (["https://driver.porterchain.com"], 3003),
    "pc-admin": (["https://admin.porterchain.com"], 3002),
}
MOBILE = {
    "pc-customer-app": "porterchain-customer://auth",
    "pc-driver-app": "porterchain-driver://auth",
}
STAFF_ROLES = ["super_admin", "admin", "dispatcher", "support", "support_lead", "sales",
               "sales_manager", "finance", "compliance", "developer", "marketing", "read_only",
               "fleet_manager"]
PERSONA_ROLES = ["customer", "driver", "merchant_owner", "merchant_admin", "merchant_dispatcher",
                 "merchant_viewer", "reviewer"]
MFA_ROLE = "mfa_required"


def public_pkce_client(client_id: str, redirects: list[str], origins: list[str]) -> dict:
    return {
        "clientId": client_id, "name": client_id, "enabled": True, "protocol": "openid-connect",
        "publicClient": True, "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
        "implicitFlowEnabled": False, "serviceAccountsEnabled": False,
        "redirectUris": redirects, "webOrigins": origins,
        "attributes": {"pkce.code.challenge.method": "S256", "post.logout.redirect.uris": "+"},
        # Built-in default scopes (basic/profile/email/roles/web-origins/acr) apply automatically;
        # PorterChain claims are client mappers so the realm import keeps Keycloak's built-ins.
        "protocolMappers": pc_mappers(),
    }


def clients() -> list[dict]:
    out = []
    for cid, (bases, port) in SITES.items():
        bases_all = bases + [f"{LOCAL}:{port}", f"http://127.0.0.1:{port}"]
        # L214: invite / setup emails return to the portal's sign-in entry (exact paths, no wildcard).
        landing = ["/auth/callback", "/auth/login", "/login", "/sign-in", "/sign-up"]
        c = public_pkce_client(cid, [f"{b}{p}" for b in bases_all for p in landing], bases_all)
        # L164: "Back to application" on Keycloak info pages (verify link opened in another browser).
        c["baseUrl"] = bases[0] + "/"
        out.append(c)
    for cid, uri in MOBILE.items():
        out.append(public_pkce_client(cid, [uri], []))
    out.append({  # API: resource server only (audience); validates JWTs via JWKS.
        "clientId": "pc-api", "name": "PorterChain API", "enabled": True, "bearerOnly": True,
        "publicClient": False, "standardFlowEnabled": False, "directAccessGrantsEnabled": False,
        "protocol": "openid-connect",
    })
    out.append({  # API service account: provisions staff users (invite / MFA reset / disable).
        "clientId": "pc-api-admin", "name": "PorterChain API staff provisioning", "enabled": True,
        "publicClient": False, "clientAuthenticatorType": "client-secret",
        "secret": "${KEYCLOAK_ADMIN_CLIENT_SECRET}", "serviceAccountsEnabled": True,
        "standardFlowEnabled": False, "directAccessGrantsEnabled": False,
        "implicitFlowEnabled": False, "protocol": "openid-connect",
    })
    return out


def service_account_users() -> list[dict]:
    return [{
        "username": "service-account-pc-api-admin", "enabled": True,
        "serviceAccountClientId": "pc-api-admin",
        "clientRoles": {"realm-management": ["manage-users", "view-users", "query-users", "view-realm"]},
    }]


def pc_mappers() -> list[dict]:
    return [
            {"name": "aud-pc-api", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
             "config": {"included.client.audience": "pc-api", "access.token.claim": "true", "id.token.claim": "false"}},
            {"name": "pc-roles", "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-realm-role-mapper",
             "config": {"claim.name": "pc_roles", "multivalued": "true", "access.token.claim": "true",
                        "id.token.claim": "true", "jsonType.label": "String"}},
            {"name": "pc-groups", "protocol": "openid-connect", "protocolMapper": "oidc-group-membership-mapper",
             "config": {"claim.name": "pc_groups", "full.path": "true", "access.token.claim": "true", "id.token.claim": "false"}},
            {"name": "pc-org", "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-attribute-mapper",
             "config": {"user.attribute": "org_id", "claim.name": "org_id", "access.token.claim": "true", "jsonType.label": "String"}},
    ]


def roles() -> dict:
    realm = [{"name": MFA_ROLE, "description": "TOTP required at login (staff admin tiers only)"}]
    for r in STAFF_ROLES:
        role = {"name": r, "description": f"Staff: {r}"}
        if r in ("super_admin", "admin"):
            role["composite"] = True
            role["composites"] = {"realm": [MFA_ROLE]}
        realm.append(role)
    realm += [{"name": r, "description": f"Persona: {r}"} for r in PERSONA_ROLES]
    return {"realm": realm}


def groups() -> list[dict]:
    return [
        {"name": "staff", "subGroups": [{"name": r, "realmRoles": [r]} for r in STAFF_ROLES]},
        {"name": "customers", "realmRoles": ["customer"]},
        {"name": "drivers", "realmRoles": ["driver"]},
        {"name": "merchants", "subGroups": [{"name": r, "realmRoles": [r]} for r in PERSONA_ROLES if r.startswith("merchant_")]},
        {"name": "reviewers", "realmRoles": ["reviewer"]},
    ]


# New-device email code (email-otp-authenticator v1.8.1). Device trust = per user+realm cookie; IP trust off.
NEW_DEVICE_CODE = {
    "code-length": "6", "code-alphabet": "0123456789", "code-lifetime": "600",
    "device-trust-enabled": "true", "device-trust-duration": "180", "ip-trust-enabled": "false",
    "trust-only-when-sole": "false", "resend-cooldown": "60", "issuance-limit": "5", "issuance-limit-window": "900",
}


def browser_flow() -> list[dict]:
    """Cookie | IdP redirector | (password or passkey), then:
    - non-staff: email code ONLY on a new/unrecognised browser (email-otp-authenticator device-trust cookie),
    - staff (role mfa_required): TOTP, never the email code."""
    return [
        {"alias": "pc-browser", "providerId": "basic-flow", "topLevel": True, "builtIn": False,
         "description": "PorterChain browser login: email code only on a new device (non-staff); staff admin TOTP",
         "authenticationExecutions": [
             {"authenticator": "auth-cookie", "requirement": "ALTERNATIVE", "priority": 10, "autheticatorFlow": False},
             {"authenticator": "identity-provider-redirector", "requirement": "ALTERNATIVE", "priority": 20, "autheticatorFlow": False},
             {"flowAlias": "pc-forms", "requirement": "ALTERNATIVE", "priority": 30, "autheticatorFlow": True},
         ]},
        {"alias": "pc-forms", "providerId": "basic-flow", "topLevel": False, "builtIn": False,
         "authenticationExecutions": [
             {"flowAlias": "pc-first-factor", "requirement": "REQUIRED", "priority": 10, "autheticatorFlow": True},
             {"flowAlias": "pc-new-device-code", "requirement": "CONDITIONAL", "priority": 15, "autheticatorFlow": True},
             {"flowAlias": "pc-staff-otp", "requirement": "CONDITIONAL", "priority": 20, "autheticatorFlow": True},
         ]},
        # Needs the Unlicense email-otp-authenticator extension (render-realm.sh drops this subflow when
        # EMAIL_OTP_ENABLED=false, e.g. in tests on the stock image).
        {"alias": "pc-new-device-code", "providerId": "basic-flow", "topLevel": False, "builtIn": False,
         "description": "Email code on a new/unrecognised browser (not staff)",
         "authenticationExecutions": [
             {"authenticator": "conditional-user-role", "requirement": "REQUIRED", "priority": 10,
              "autheticatorFlow": False, "authenticatorConfig": "pc-not-staff"},
             {"authenticator": "email-otp-form", "requirement": "REQUIRED", "priority": 20,
              "autheticatorFlow": False, "authenticatorConfig": "pc-new-device-code-cfg"},
         ]},
        {"alias": "pc-first-factor", "providerId": "basic-flow", "topLevel": False, "builtIn": False,
         "authenticationExecutions": [
             {"authenticator": "auth-username-password-form", "requirement": "ALTERNATIVE", "priority": 10, "autheticatorFlow": False},
             {"authenticator": "webauthn-authenticator-passwordless", "requirement": "ALTERNATIVE", "priority": 20, "autheticatorFlow": False},
         ]},
        {"alias": "pc-staff-otp", "providerId": "basic-flow", "topLevel": False, "builtIn": False,
         "authenticationExecutions": [
             {"authenticator": "conditional-user-role", "requirement": "REQUIRED", "priority": 10,
              "autheticatorFlow": False, "authenticatorConfig": "pc-mfa-role"},
             {"authenticator": "auth-otp-form", "requirement": "REQUIRED", "priority": 20, "autheticatorFlow": False},
         ]},
    ]


def idps() -> list[dict]:
    return [
        {"alias": "google", "providerId": "google", "enabled": True, "trustEmail": True,
         "firstBrokerLoginFlowAlias": "first broker login",
         "config": {"clientId": "${GOOGLE_CLIENT_ID}", "clientSecret": "${GOOGLE_CLIENT_SECRET}",
                    "syncMode": "IMPORT", "defaultScope": "openid profile email"}},
        # Needs the Apache-2.0 keycloak-apple-social-identity-provider extension (render-realm.sh
        # drops this entry when APPLE_IDP_ENABLED!=true, e.g. in tests on the stock image).
        {"alias": "apple", "providerId": "apple", "enabled": True, "trustEmail": True,
         "firstBrokerLoginFlowAlias": "first broker login",
         "config": {"clientId": "${APPLE_SERVICES_ID}", "teamId": "${APPLE_TEAM_ID}",
                    "keyId": "${APPLE_KEY_ID}", "p8Content": "${APPLE_P8_KEY}",
                    "clientSecret": "unused-apple-signs-its-own", "syncMode": "IMPORT",
                    "defaultScope": "openid name email"}},
    ]


def realm() -> dict:
    return {
        "realm": "porterchain", "enabled": True, "displayName": "PorterChain",
        "registrationAllowed": True, "registrationEmailAsUsername": True, "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False, "resetPasswordAllowed": True, "rememberMe": True,
        "verifyEmail": True,  # L82: API trusts only a verified KC email; verified users see no extra login step
        "sslRequired": "external",
        "bruteForceProtected": True, "permanentLockout": False, "failureFactor": 10,
        "waitIncrementSeconds": 60, "maxFailureWaitSeconds": 900, "maxDeltaTimeSeconds": 43200,
        "minimumQuickLoginWaitSeconds": 60, "quickLoginCheckMilliSeconds": 1000,
        "passwordPolicy": "length(10) and notUsername and notEmail and passwordHistory(3)",
        "accessTokenLifespan": 300, "ssoSessionIdleTimeout": 2592000, "ssoSessionMaxLifespan": 7776000,
        "offlineSessionIdleTimeout": 7776000,
        "otpPolicyType": "totp", "otpPolicyAlgorithm": "HmacSHA1", "otpPolicyDigits": 6, "otpPolicyPeriod": 30,
        "webAuthnPolicyPasswordlessRpEntityName": "PorterChain",
        "webAuthnPolicyPasswordlessUserVerificationRequirement": "required",
        "webAuthnPolicyPasswordlessResidentKey": "Yes",
        "browserFlow": "pc-browser",
        "roles": roles(), "groups": groups(), "defaultRoles": ["customer"],
        "clients": clients(), "users": service_account_users(),
        "authenticationFlows": browser_flow(),
        "authenticatorConfig": [
            {"alias": "pc-mfa-role", "config": {"condUserRole": MFA_ROLE, "negate": "false"}},
            {"alias": "pc-not-staff", "config": {"condUserRole": MFA_ROLE, "negate": "true"}},
            {"alias": "pc-new-device-code-cfg", "config": NEW_DEVICE_CODE},
        ],
        "requiredActions": [
            {"alias": "VERIFY_EMAIL", "name": "Verify Email", "providerId": "VERIFY_EMAIL", "enabled": True, "defaultAction": False, "priority": 1},
            {"alias": "UPDATE_PASSWORD", "name": "Update Password", "providerId": "UPDATE_PASSWORD", "enabled": True, "defaultAction": False, "priority": 5},
            {"alias": "CONFIGURE_TOTP", "name": "Configure OTP", "providerId": "CONFIGURE_TOTP", "enabled": True, "defaultAction": False, "priority": 10},
            {"alias": "webauthn-register-passwordless", "name": "Passkey Register", "providerId": "webauthn-register-passwordless", "enabled": True, "defaultAction": False, "priority": 20},
        ],
        "identityProviders": idps(),
        "attributes": {"frontendUrl": "", "actionTokenGeneratedByUserLifespan.verify-email": "43200"},  # L84: 12 h verify link
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("realm-porterchain.json")
    out.write_text(json.dumps(realm(), indent=2) + "\n")
    print(f"wrote {out} (run: npx prettier --write {out.name})")
