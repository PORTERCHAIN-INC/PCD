# ADR-017: Enterprise SAML & SCIM (§11.2.1–11.2.2)

**Status:** Accepted (dev MVP — Clerk Enterprise configuration)  
**Date:** 2026-07-09

## Context

Enterprise merchants require SSO (SAML 2.0) and automated user provisioning (SCIM). Porterchain uses **Clerk** for authentication only; authorization remains in Porterchain RBAC tables.

## Decision

| Capability           | Approach                                                                    |
| -------------------- | --------------------------------------------------------------------------- |
| **SAML 2.0**         | Clerk Enterprise SAML connection per portal (merchant, admin)               |
| **SCIM**             | Clerk Enterprise SCIM — deferred Phase 2; document contract now             |
| **JIT provisioning** | `merchant_users` / `admin_users` rows created on first JWT after SAML login |
| **Fleetbase SSO**    | Separate Porterchain-issued JWT — see [SSO.md](../../SSO.md)                |

## SAML flow (merchant portal)

1. Enterprise IdP (Okta/Azure AD) → Clerk SAML connection
2. User signs in at Clerk-hosted or embedded SAML
3. Merchant portal receives Clerk session JWT
4. API resolves `merchant_users.clerk_user_id` → `MerchantContext`
5. `require_module()` enforces Porterchain permissions

## SCIM (Phase 2)

- **In scope later:** group → `MerchantRole` mapping table
- **Out of scope:** Clerk Organizations as permission source (masterrule)
- **MVP:** manual team invite via `POST /v1/merchant/team/invite` + admin merchant invites

## Configuration checklist (ops)

- [ ] Clerk Enterprise plan enabled
- [ ] SAML connection per enterprise merchant (Clerk dashboard)
- [ ] `clerk_merchant_*` keys in Doppler prod
- [ ] Merchant domain allowlist in Clerk

## Consequences

- No custom SAML code in Porterchain API — reduces security surface
- ENT-G2 satisfied when SAML pilot merchant is live + audit export (§11.1.7 done)

## References

- [RBAC_MATRIX.md](../../RBAC_MATRIX.md)
- [Clerk SAML docs](https://clerk.com/docs/authentication/saml/overview)
