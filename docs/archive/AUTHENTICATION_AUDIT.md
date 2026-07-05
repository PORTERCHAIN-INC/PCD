# Authentication Audit

**Date:** July 1, 2026  
**Last verified:** 2026-07-04  
**Status:** Historical — cleanup completed

This document records the **pre-cleanup inventory** from the July 2026 Clerk-only migration. For current auth architecture, use **[AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)**.

---

## Executive summary

Prior to cleanup, documentation and env templates described a multi-provider model (Clerk + Supabase OTP + Porterchain driver JWT + Fleetbase). Runtime had partially migrated to Clerk-only; Supabase/Twilio/booking OTP scaffolding was removed from code and templates.

**Outcome:** Clerk is the sole user identity provider. Supabase and Twilio OTP paths removed. Driver session JWT remains an API session bridge after Clerk login — not a second IdP.

---

## Removed providers (historical)

| Provider | Finding | Action taken |
| -------- | ------- | ------------ |
| Supabase | Env templates + docs only; no `@supabase/supabase-js` in repo | Removed from env, website, legal copy |
| Twilio OTP | Optional SMS import in notification delivery; not in API deps | Removed auth/OTP use; SMS log-only |
| Booking OTP | Env-templated but no API router | Removed env vars and docs |

See [AUTHENTICATION_CLEANUP.md](./AUTHENTICATION_CLEANUP.md) for file-level change log.

---

## Retained (Clerk-aligned)

| Component | Path | Role |
| --------- | ---- | ---- |
| Clerk JWT verification | `apps/api/src/porterchain_api/auth/clerk.py` | API middleware |
| Admin auth context | `apps/api/src/porterchain_api/auth/admin.py` | Admin RBAC gate |
| Driver Clerk login | `apps/api/src/porterchain_api/driver_engine/auth_service.py` | Clerk → session bridge |
| Merchant API auth | `apps/api/src/porterchain_api/auth/merchant_api.py` | API key (machine auth) |
| SSO to Fleetbase | `apps/api/src/porterchain_api/auth/sso_service.py` | Console SSO JWT |
| Portal Clerk SDK | `website/`, `apps/admin/`, `apps/merchant-portal/`, `apps/driver-portal/`, `apps/customer/` | Frontend sessions |
| Mobile Clerk | `apps/mobile-driver/`, `apps/mobile-customer/` | `@clerk/clerk-expo` |

---

## Gaps at audit time → current status

| Gap (July 1) | Status (July 2026) |
| ------------ | ------------------ |
| Website booking Clerk wiring | **Implemented** — Clerk middleware + customer portal sign-in |
| Driver mobile Clerk SDK | **Implemented** — `@clerk/clerk-expo` in mobile-driver |
| SMS notification provider | **Open** — log-only until provider selected |
| `otp_verifications` DB table | Verify in DB audit group if still present |

---

## Compliance with masterrule.md

| Rule | Status |
| ---- | ------ |
| §15 Clerk for authentication | Aligned |
| §10.1 Clerk auth + session merge in booking | Implemented on website |
| §3 Controllers resolve auth via Clerk helpers | Implemented on protected routes |

---

_Related: [AUTHENTICATION_CLEANUP.md](./AUTHENTICATION_CLEANUP.md), [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)_
