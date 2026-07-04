# Authentication Audit

**Date:** July 1, 2026  
**Scope:** Full Porterchain monorepo — pre-cleanup inventory  
**Authority:** [masterrule.md](./masterrule.md) §15

---

## Executive summary

Prior to this cleanup, Porterchain documentation and environment templates described a **multi-provider authentication model** (Clerk + Supabase OTP + Porterchain driver JWT + Fleetbase). Runtime code had **partially migrated** to Clerk-only driver auth, but **legacy scaffolding** for Supabase booking OTP, Twilio SMS OTP, and dedicated booking SMTP remained in env templates, docs, and website `env.ts`.

**Finding:** No `@supabase/supabase-js` package or Supabase client code was present in the repo. Twilio was referenced only in notification delivery (optional SMS channel) and env templates — not as a declared API dependency. Booking OTP was **documented and env-templated but not implemented** in API routers.

---

## Inventory — removed authentication providers

### Supabase

| Location | Finding |
|----------|---------|
| `website/src/lib/env.ts` | `NEXT_PUBLIC_SUPABASE_*`, `isSupabaseConfigured()` |
| `env/website.env.example` | Supabase URL + anon key |
| `website/env.example` | Supabase vars |
| `env/.env` | Live Supabase project URL + anon key |
| `integrations.yaml` | `supabase_booking_otp` integration |
| `AUTHENTICATION.md` | Supabase OTP flow documented |
| `ENVIRONMENT_VARIABLES.md` | OTP bridge vars |
| `website/messages/legal-*.json` | Cookie policy referenced Supabase |
| `PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md` | Supabase listed as auth provider |

**Packages:** None installed.

### Twilio

| Location | Finding |
|----------|---------|
| `shared/python/porterchain_shared/config/settings.py` | `twilio_*` settings fields |
| `apps/api/.../delivery_service.py` | Optional `twilio.rest.Client` import for SMS |
| `apps/api/.../settings_service.py` | Integration health `sms` status from Twilio SID |
| `env/api.env.example`, `env/worker.env.example` | `TWILIO_*` vars |
| `env/fleetbase.env.example`, `services/fleetbase/env.example` | Twilio optional block |
| `env/.env` | Live Twilio credentials |
| `integrations.yaml` | `twilio` integration entry |
| `TECH_STACK.md`, `AUTHENTICATION.md` | SMS OTP documentation |

**Packages:** No `twilio` in `apps/api/pyproject.toml` — import was dynamic and would fail if Twilio vars were set without manual install.

### Booking / email / phone OTP (custom)

| Location | Finding |
|----------|---------|
| `env/api.env.example` | `PORTERCHAIN_WEBSITE_OTP_KEY`, `BOOKING_OTP_*`, `BOOKING_OTP_SMTP_*` |
| `env/.env` | OTP bridge key, Zoho SMTP creds tied to OTP, skip-verify flags |
| `website/src/lib/env.ts` | `NEXT_PUBLIC_BOOKING_OTP_SKIP_VERIFY` |
| `DATABASE_ARCHITECTURE.md` | `otp_verifications` table (planned) |

**Runtime:** No API router or service implemented booking OTP send/verify.

---

## Inventory — retained (Clerk-aligned)

| Component | Path | Role |
|-----------|------|------|
| Clerk JWT verification | `apps/api/src/porterchain_api/auth/clerk.py` | API middleware |
| Admin auth context | `apps/api/src/porterchain_api/auth/admin.py` | Admin RBAC gate |
| Driver Clerk login | `apps/api/src/porterchain_api/driver_engine/auth_service.py` | Clerk → session bridge |
| Merchant API auth | `apps/api/src/porterchain_api/auth/merchant_api.py` | API key (not user auth) |
| SSO to Fleetbase | `apps/api/src/porterchain_api/auth/sso_service.py` | Console SSO JWT |
| RBAC package | `packages/auth/` | Role helpers |
| Portal Clerk SDK | `apps/admin/`, `apps/merchant-portal/`, `apps/driver-portal/`, `website/` | Frontend sessions |

---

## Inventory — non-auth (explicitly out of scope)

| Item | Reason kept |
|------|-------------|
| Delivery POD OTP (`pod.py`, driver routes) | Recipient proof-of-delivery — not user identity |
| Fleetbase Sanctum / dispatcher API key | Logistics execution bridge |
| Porterchain driver session JWT | API session after Clerk login — not alternate IdP |
| SMTP / `MAIL_*` vars | Transactional notifications only |

---

## Email audit

| Pattern | Count (pre-cleanup) | Action |
|---------|---------------------|--------|
| `peter@porterchain.com` | 24 files | Replace with `ravi@porterchain.com` |
| Hardcoded mailto in React | 3 components | Use `NEXT_PUBLIC_CONTACT_EMAIL` |
| `BOOKING_OTP_SMTP_*` | Env templates | Remove — duplicate of transactional SMTP |
| Legacy `SMTP_*` with personal creds | `env/.env` | Remove |

---

## Gaps after cleanup

| Gap | Risk | Remediation |
|-----|------|-------------|
| Website booking flow Clerk wiring | Medium | Wire `book/continue` to Clerk session (Phase B) |
| Driver mobile Clerk SDK | Medium | Replace dev email-only login with Clerk Expo |
| SMS notification provider | Low | Select provider when transactional SMS is needed |
| `otp_verifications` DB table | Low | Drop or repurpose if migration exists |

---

## Compliance with masterrule.md

| Rule | Status |
|------|--------|
| §15 Clerk for authentication | **Aligned** after cleanup |
| §10.1 Clerk auth + session merge in booking | Documented; website wiring pending |
| §3 Controllers resolve auth via `get_clerk_user_id` | Implemented on protected routes |

---

_Related: [AUTHENTICATION_CLEANUP.md](./AUTHENTICATION_CLEANUP.md), [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)_
