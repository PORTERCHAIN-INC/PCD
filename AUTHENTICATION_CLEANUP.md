# Authentication Cleanup

**Date:** July 1, 2026  
**Objective:** Clerk as the **only** authentication provider  
**Authority:** [masterrule.md](./masterrule.md) §15

---

## Summary

Removed all Supabase, Twilio, and booking-OTP authentication scaffolding from code, environment templates, and user-facing legal copy. Retained SMTP variables for **transactional email** (notifications). Replaced `peter@porterchain.com` with `ravi@porterchain.com` and moved public contact email to `NEXT_PUBLIC_CONTACT_EMAIL`.

---

## Code changes

### `website/src/lib/env.ts`

- Removed `supabaseUrl`, `supabaseAnonKey`, `bookingOtpSkipVerify`
- Removed `isSupabaseConfigured()`
- Added `contactEmail` from `NEXT_PUBLIC_CONTACT_EMAIL` (default `ravi@porterchain.com`)

### `website/src/components/`

- `ContactInquiryForm.tsx`, `InquiryForm.tsx`, `HeroSection.tsx` — mailto uses `publicEnv.contactEmail`
- `website/src/data/careers.ts` — `CAREERS_APPLY_EMAIL` from env

### `shared/python/porterchain_shared/config/settings.py`

- Removed `twilio_account_sid`, `twilio_auth_token`, `twilio_from_number`
- Retained `smtp_*` for transactional notifications

### `apps/api/src/porterchain_api/notification_engine/delivery_service.py`

- Removed Twilio `Client` import and send path
- SMS channel is **log-only** until a notification SMS provider is chosen

### `apps/api/src/porterchain_api/admin_engine/settings_service.py`

- SMS integration health reports `log_only` with Clerk note

---

## Environment template changes

| File | Removed |
|------|---------|
| `env/api.env.example` | `PORTERCHAIN_WEBSITE_OTP_KEY`, `BOOKING_OTP_*`, `BOOKING_OTP_SMTP_*`, `SUPABASE_*`, `TWILIO_*` |
| `apps/api/env.example` | Same |
| `env/website.env.example` | `NEXT_PUBLIC_SUPABASE_*`, `NEXT_PUBLIC_BOOKING_OTP_SKIP_VERIFY` |
| `website/env.example` | Same |
| `env/worker.env.example` | `TWILIO_*` |
| `env/fleetbase.env.example` | `PORTERCHAIN_WEBSITE_OTP_KEY`, `TWILIO_*` |
| `services/fleetbase/env.example` | Same |
| `env/compose.env.example` | Twilio comment reference |

### Added

| Variable | File | Purpose |
|----------|------|---------|
| `NEXT_PUBLIC_CONTACT_EMAIL` | `env/website.env.example`, `website/env.example`, `env/.env` | Public contact email |

### Local `env/.env`

- Removed Supabase URL/keys, OTP bridge key, Twilio credentials, `BOOKING_OTP_SMTP_*`
- Removed legacy personal SMTP credentials
- Kept `MAIL_*` transactional placeholders (empty username/password)

---

## Configuration / integration registry

### `integrations.yaml`

- Removed `supabase_booking_otp`
- Removed `twilio`

---

## Documentation updates

| File | Change |
|------|--------|
| `AUTHENTICATION.md` | Rewritten for Clerk-only (v3.0) |
| `AUTHENTICATION_AUDIT.md` | Created — pre-cleanup inventory |
| `AUTHENTICATION_ARCHITECTURE.md` | Created — target architecture |
| `AUTHENTICATION_CLEANUP.md` | This document |

### Legal / i18n

| File | Change |
|------|--------|
| `website/messages/legal-en.json` | Clerk-only cookies; `peter@` → `ravi@` |
| `website/messages/legal-fr.json` | Same |
| `website/messages/corporate-*.json` | `peter@` → `ravi@` |
| `website/messages/site-footer-*.json` | `peter@` → `ravi@` |
| `PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md` | `peter@` → `ravi@` |

---

## Not changed (intentional)

| Item | Reason |
|------|--------|
| Driver POD OTP (`pod.py`, mobile `OTP_VERIFY`) | Delivery proof — not user authentication |
| Porterchain driver session JWT | Session bridge after Clerk login |
| Fleetbase Sanctum / dispatcher key | Execution engine integration |
| Dev seed emails (`marco@porterchain.com`, etc.) | Test fixtures — not contact/auth |
| `AUTHENTICATION_FLOW.md`, `RBAC.md`, `SSO.md` | Separate focused docs — update in follow-up if stale |

---

## Follow-up recommended

1. Rotate any credentials that were in `env/.env` for Supabase/Twilio/OTP SMTP (removed from file but may exist in git history).
2. Wire website `book/continue` to Clerk sign-in per masterrule §10.1.
3. Update `ENVIRONMENT_VARIABLES.md`, `TECH_STACK.md`, `INTEGRATIONS.md` to remove OTP/Supabase/Twilio rows.
4. Add Clerk Expo SDK to `apps/mobile-driver` and remove dev default emails from sign-in screens.

---

_Related: [AUTHENTICATION_AUDIT.md](./AUTHENTICATION_AUDIT.md), [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)_
