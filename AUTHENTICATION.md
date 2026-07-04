# Porterchain — Authentication Architecture

**Document version:** 3.0  
**Date:** July 1, 2026  
**Authority:** [masterrule.md](./masterrule.md) §15

> **Clerk is the sole authentication provider** for Porterchain users. See [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md), [AUTHENTICATION_FLOW.md](./AUTHENTICATION_FLOW.md), [SSO.md](./SSO.md), and [RBAC.md](./RBAC.md).

---

## Overview

Porterchain uses **Clerk** as the only identity provider for end-user authentication. The Porterchain API validates Clerk JWTs and enforces RBAC. Fleetbase Sanctum and dispatcher API keys are used only for logistics execution integration — not for Porterchain user login.

```
┌──────────────────────────────────────────────────────────────────┐
│                     AUTHENTICATION PROVIDERS                      │
├─────────────────────────────┬────────────────────────────────────┤
│   Clerk (JWT/JWKS)          │  Fleetbase Sanctum / API key       │
├─────────────────────────────┼────────────────────────────────────┤
│ Website retail booking      │ Dispatcher / control tower bridge  │
│ Merchant portal             │                                    │
│ Admin portal                │                                    │
│ Driver web + mobile         │                                    │
└─────────────────────────────┴────────────────────────────────────┘
```

---

## Clerk responsibilities

Clerk handles **only** authentication concerns:

| Capability | Owner |
|------------|-------|
| Signup | Clerk |
| Login | Clerk |
| Password reset | Clerk |
| MFA | Clerk |
| Email verification | Clerk |
| Phone verification | Clerk |
| OAuth | Clerk |
| Session | Clerk |
| Logout | Clerk |

No Supabase, Twilio Verify, custom OTP, or alternate IdP is used for user authentication.

---

## Configuration

| Variable | Purpose |
|----------|---------|
| `CLERK_PUBLISHABLE_KEY` / `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Frontend SDK |
| `CLERK_SECRET_KEY` | Server-side verification |
| `CLERK_JWKS_URL` | JWT public key rotation |
| `CLERK_DEV_BYPASS` | **Local only** (`APP_ENV=local` **and** `CLERK_DEV_BYPASS=true`) — never in staging/production |

### Enterprise: separate Clerk apps per user class

For production blast-radius isolation, create **four Clerk applications** in [Clerk Dashboard](https://dashboard.clerk.com):

| Clerk app | User class | Frontend(s) | API env prefix |
|-----------|------------|-------------|----------------|
| `porterchain-customer` | Retail customers | Website, customer portal, customer mobile | `CLERK_CUSTOMER_*` |
| `porterchain-merchant` | B2B merchants | Merchant portal | `CLERK_MERCHANT_*` |
| `porterchain-admin` | Internal staff | Admin portal | `CLERK_ADMIN_*` |
| `porterchain-driver` | Drivers | Driver portal, driver mobile | `CLERK_DRIVER_*` |

**API (`apps/api/.env`):** set all four `CLERK_{CLASS}_SECRET_KEY` and `CLERK_{CLASS}_JWKS_URL` values. JWT verification tries each JWKS URL until the token validates; invitations use the matching class secret.

**Frontends:** each app uses its own `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (or `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` on mobile) — no code changes, only env.

**Local dev:** leave per-class keys empty and set legacy `CLERK_SECRET_KEY` + `CLERK_JWKS_URL` only — the API registry applies that single instance to all four classes.

Authorization remains **Porterchain DB rows** (`admin_users`, `merchant_users`, `drivers`, `customers`) — separate Clerk apps isolate identity blast radius only.

### Production Clerk Dashboard checklist

Configure in [Clerk Dashboard](https://dashboard.clerk.com) for **each** Clerk application (or the shared local instance):

1. **Sign-up mode:** Allow public sign-up for **customers only** (or restrict with email verification + rate limits).
2. **Admin / merchant / driver:** Disable public sign-up; use **Invitations** only (`InvitationService` in API).
3. **Email verification:** Required for customer accounts in production.
4. **OAuth:** Enable Google (and others) for customer + mobile apps as needed.
5. **Sessions:** Use default session lifetime; enable MFA for admin staff in Clerk when ready.

### Local dev bypass (gated)

Dev shortcuts activate **only** when **both** are set:

```bash
APP_ENV=local
CLERK_DEV_BYPASS=true
```

This enables: empty `Authorization` → synthetic dev user, `Bearer dev` token, `X-Admin-Role` header (admin portal local only), driver email-only login, mobile dev email panels.

**Default:** `CLERK_DEV_BYPASS=false` — production-safe out of the box.

### Surfaces

| Application | Port | Clerk integration |
|-------------|------|-------------------|
| Website | 3000 | Retail booking auth |
| Merchant portal | 3001 | Sign-in / sign-up |
| Admin | 3002 | Sign-in + RBAC |
| Driver portal | 3003 | Sign-in + invite flow |
| Driver mobile | Expo | Clerk session → API bridge |

---

## Verification flow

```
Client → Clerk session → JWT in Authorization header
  → Porterchain API (auth/clerk.py)
  → Fetch JWKS from all configured CLERK_*_JWKS_URL values (or legacy CLERK_JWKS_URL)
  → Verify signature + expiry + issuer
  → Extract sub, org_id, email, metadata
  → Authorize route (RBAC)
```

### Portal access gates

Each portal verifies Clerk identity **and** Porterchain provisioning:

| Portal | Middleware | API gate |
|--------|------------|----------|
| Admin | `auth.protect()` | `GET /v1/auth/admin/access` → `admin_users` |
| Merchant | `auth.protect()` | `GET /v1/auth/merchant/access` → `merchant_users` |
| Customer (app + website) | `auth.protect()` | `GET /v1/auth/customer/access` → auto-provision `customers` |
| Driver web | Porterchain JWT cookie | Clerk at `/login` → `POST /driver-api/v1/auth/login` |

Authorization uses **database rows only** in production — Clerk `public_metadata` role fallback is disabled unless local dev bypass is active.

### JWT claims (expected)

| Claim | Use |
|-------|-----|
| `sub` | Clerk user ID |
| `org_id` | Merchant organization |
| `email` | Contact email |
| Custom metadata | Merchant status, driver link, admin roles |

---

## Canonical user registry

Every Clerk-authenticated request syncs into `porterchain_users` via `UserSyncService` (see [CLERK_INTEGRATION_REPORT.md](./CLERK_INTEGRATION_REPORT.md)).

---

Drivers authenticate through **Clerk**. After Clerk verification, the API issues short-lived Porterchain session tokens for mobile/offline API access:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login` | POST | Clerk token + email → driver session |
| `/auth/refresh` | POST | Refresh Porterchain session token |
| `/auth/driver-invite/accept` | POST | Invite token + Clerk password setup |

`DriverAuthService` (`driver_engine/auth_service.py`) requires a valid Clerk bearer token in all non-dev environments.

---

## Fleetbase authentication (execution only)

| Method | Header | Use |
|--------|--------|-----|
| Sanctum bearer | `Authorization: Bearer <token>` | Fleetbase console session |
| API key | `X-Dispatcher-Api-Key` | Porterchain ↔ Fleetbase dispatch bridge |

Not used for Porterchain portal user login.

---

## Roles and permissions

| Role | Surface | Provider | Permissions |
|------|---------|----------|-------------|
| **Merchant (owner)** | Merchant portal | Clerk | Full account, billing, shipments, API keys |
| **Merchant (user)** | Merchant portal | Clerk | Scoped by org role |
| **Driver** | Mobile / driver web | Clerk + session bridge | Routes, POD, location |
| **Admin** | Admin portal | Clerk + RBAC | Ops, CRM, finance |
| **Dispatcher** | Fleetbase console | Fleetbase session | Dispatch only |

RBAC: `admin_engine/rbac.py`, `merchant_engine/rbac.py`, `packages/auth/`.

---

## Delivery OTP (not authentication)

Proof-of-delivery recipient codes (`otp_required`, `delivery_otp_hash`) are **operational verification** at dropoff — not user authentication. Clerk remains the only identity provider.

---

## Transactional email

SMTP environment variables (`MAIL_*`, `SMTP_*`) are retained for **notification delivery** (invoices, ops mail). They are not used for authentication or OTP.

---

## Public order tracking

`GET /v1/orders/{tracking_number}` is intentionally unauthenticated — tracking number only.

---

## Related documents

| Document | Purpose |
|----------|---------|
| [AUTHENTICATION_AUDIT.md](./AUTHENTICATION_AUDIT.md) | Pre-cleanup inventory |
| [AUTHENTICATION_CLEANUP.md](./AUTHENTICATION_CLEANUP.md) | Changes applied |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) | Target architecture |
| [SECURITY.md](./SECURITY.md) | Secrets, JWT hardening |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) | Env var reference |
