# Authentication Cleanup

**Date:** July 1, 2026  
**Last verified:** 2026-07-04  
**Status:** Completed

Historical log of the Clerk-only authentication cleanup. Current architecture: **[AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)**.

---

## Summary

Removed Supabase, Twilio, and booking-OTP authentication scaffolding from code, environment templates, and legal copy. Retained SMTP for **transactional email** (notifications). Replaced `peter@porterchain.com` with `ravi@porterchain.com`; public contact via `NEXT_PUBLIC_CONTACT_EMAIL`.

---

## Code changes (applied)

| Area | Change |
| ---- | ------ |
| `website/src/lib/env.ts` | Removed Supabase + booking OTP vars; added `contactEmail` |
| `website/src/components/` | Mailto uses `publicEnv.contactEmail` |
| `shared/python/porterchain_shared/config/settings.py` | Removed Twilio settings |
| `apps/api/.../delivery_service.py` | SMS channel log-only |
| `apps/api/.../settings_service.py` | SMS health reports `log_only` |

---

## Environment templates (applied)

Removed from examples: `NEXT_PUBLIC_SUPABASE_*`, `PORTERCHAIN_WEBSITE_OTP_KEY`, `BOOKING_OTP_*`, `TWILIO_*`.

Added: `NEXT_PUBLIC_CONTACT_EMAIL`.

---

## Documentation (applied)

| File | Change |
| ---- | ------ |
| `AUTHENTICATION_ARCHITECTURE.md` | Canonical Clerk-only architecture |
| `AUTHENTICATION.md` | Pointer to architecture doc |
| `AUTHENTICATION_AUDIT.md` | Pre-cleanup inventory (historical) |
| Legal / i18n | Clerk-only cookies; contact email updates |

---

## Intentionally unchanged

| Item | Reason |
| ---- | ------ |
| Driver POD OTP | Delivery proof — not user authentication |
| Porterchain driver session JWT | Session bridge after Clerk login |
| Fleetbase Sanctum / dispatcher key | Execution engine integration |

---

## Follow-up (post-cleanup)

1. Rotate credentials that were in `env/.env` for removed providers (check git history).
2. ~~Wire website booking to Clerk~~ — done.
3. ~~Add Clerk Expo to mobile-driver~~ — done.
4. Select SMS provider when transactional SMS is needed.

---

_Related: [AUTHENTICATION_AUDIT.md](./AUTHENTICATION_AUDIT.md), [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)_
