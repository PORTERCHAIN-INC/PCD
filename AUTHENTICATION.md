# Porterchain — Authentication Architecture

**Document version:** 2.0  
**Date:** June 29, 2026  

> **Updated:** Clerk is now the single identity provider for Porterchain users. See [AUTHENTICATION_FLOW.md](./AUTHENTICATION_FLOW.md), [SSO.md](./SSO.md), and [RBAC.md](./RBAC.md).

---

## Overview

Porterchain uses a **multi-provider authentication model**. There is no single SSO product across all surfaces. Each client application authenticates against the appropriate provider, with the Porterchain API as the central authorization enforcement point.

```
┌──────────────────────────────────────────────────────────────────┐
│                     AUTHENTICATION PROVIDERS                      │
├─────────────┬─────────────┬──────────────┬───────────────────────┤
│   Clerk     │  Supabase   │ Porterchain  │  Fleetbase Sanctum    │
│  (JWT/JWKS) │  (OTP)      │  JWT         │  (API key / bearer)   │
├─────────────┼─────────────┼──────────────┼───────────────────────┤
│ Merchant    │ Website     │ Driver app   │ Dispatcher /          │
│ portal      │ retail      │ (mobile)     │ control tower         │
│ Driver web  │ booking     │              │                       │
└─────────────┴─────────────┴──────────────┴───────────────────────┘
```

---

## Single Sign-On strategy (target)

| Goal | Approach |
|------|----------|
| Unified merchant identity | Clerk as IdP for merchant portal |
| Retail anonymous booking | Supabase OTP — no persistent account required |
| Driver identity | Porterchain-issued JWT after `/auth/login` or invite flow |
| Ops / dispatch | Fleetbase session + `PORTERCHAIN_DISPATCHER_API_KEY` |
| Future SSO | Evaluate Clerk Organizations for multi-tenant merchant teams |

**True SSO across merchant + driver + admin is not implemented today.** Clerk handles web portal users; drivers use Porterchain credentials.

---

## Clerk

### Configuration

| Variable | Purpose |
|----------|---------|
| `CLERK_PUBLISHABLE_KEY` | Frontend SDK |
| `CLERK_SECRET_KEY` | Server-side verification |
| `CLERK_JWKS_URL` | JWT public key rotation |

### Used by

- Merchant portal sign-in / sign-up
- Driver web portal (invite password setup at `/auth/driver-invite`)
- Admin users (where Clerk is integrated)

### Verification flow

```
Client → Clerk session → JWT in Authorization header
  → Porterchain API middleware
  → Fetch JWKS from CLERK_JWKS_URL
  → Verify signature + expiry + issuer
  → Extract user_id, org_id, roles
  → Authorize route
```

### JWT claims (expected)

| Claim | Use |
|-------|-----|
| `sub` | Clerk user ID |
| `org_id` | Merchant organization |
| `email` | Contact email |
| Custom metadata | Merchant status, driver link |

---

## Porterchain JWT (driver app)

### Issuance

| Endpoint | Method | Body |
|----------|--------|------|
| `/auth/login` | POST | `{ email, password }` |
| `/auth/refresh` | POST | Refresh token |
| `/auth/driver-invite/accept` | POST | Invite token + password |

### Response (required fields)

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<optional>",
  "driver_id": "<uuid>"
}
```

### Request headers (authenticated)

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer <access_token>` | Yes |
| `X-User-Id` | User ID string | Yes |
| `X-Roles` | `driver` | Yes |
| `X-Driver-Id` | Driver UUID | Driver-scoped routes |

### Token storage (mobile)

- `expo-secure-store` — never AsyncStorage for tokens
- Keys: `porterchain_driver_access_token`, `porterchain_driver_refresh_token`, `porterchain_driver_driver_id`

---

## Supabase Auth (website booking OTP)

### Flow

| Booking type | OTP channel |
|--------------|-------------|
| Business | Email OTP via Zoho SMTP (`BOOKING_OTP_SMTP_*`) |
| Personal | SMS OTP via Twilio |

### Configuration

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Client SDK |
| `PORTERCHAIN_WEBSITE_OTP_KEY` | Server HMAC bridge |
| `BOOKING_OTP_SKIP_VERIFY` | Dev bypass (server) |
| `NEXT_PUBLIC_BOOKING_OTP_SKIP_VERIFY` | Dev bypass (client) |

### Status in PCD repo

**Not implemented** — booking widget is client-side only. Supabase integration is planned per platform docs.

---

## Fleetbase authentication

### Dispatcher / control tower

| Method | Header |
|--------|--------|
| Sanctum bearer token | `Authorization: Bearer <token>` |
| API key | `X-Dispatcher-Api-Key: <PORTERCHAIN_DISPATCHER_API_KEY>` |

Used for dispatch bridge operations between Porterchain API and Fleetbase.

---

## Roles and permissions

### Role matrix

| Role | Surface | Provider | Permissions |
|------|---------|----------|-------------|
| **Merchant (owner)** | Merchant portal | Clerk | Full account, billing, shipments, API keys |
| **Merchant (user)** | Merchant portal | Clerk | Scoped by org role (future) |
| **Driver** | Mobile app | Porterchain JWT | Assigned routes, POD upload, location |
| **Dispatcher** | Fleetbase console | Fleetbase session | Route creation, assignment, optimization |
| **Admin** | Fleetbase / internal | Clerk + Fleetbase | Merchant approval, compliance review |
| **Support** | Internal tools | Clerk | Read-only shipment access (target) |
| **Sales** | CRM (PC-CRM) | Clerk | Lead management (external module) |

### Merchant lifecycle states

```
SIGN_UP → ONBOARDING → PENDING_REVIEW → ACTIVE | REJECTED
```

| State | Portal access |
|-------|---------------|
| ONBOARDING | Wizard only |
| PENDING_REVIEW | Limited — no shipments |
| ACTIVE | Full dashboard |
| REJECTED | Contact support |

### Driver lifecycle

```
INVITE_SENT → INVITE_ACCEPTED → ACTIVE → SUSPENDED
```

Invite link: `{DRIVER_PORTAL_BASE_URL}/auth/driver-invite?token=<opaque>`

---

## Authorization middleware (target)

### Porterchain API

```python
# Pseudocode — apps/api/src/middleware/auth.py
@router.get("/driver-api/v1/routes/assigned")
async def get_assigned_route(
    user: User = Depends(require_role("driver")),
    driver_id: str = Depends(require_driver_id),
):
    ...
```

### Website

Current middleware (`website/src/middleware.ts`) handles **locale routing only** — no auth.

---

## Rate limiting (auth endpoints)

| Endpoint | Limit | Variable |
|----------|-------|----------|
| `/auth/driver-invite/validate` | 30/min | `AUTH_DRIVER_INVITE_VALIDATE_MAX_ATTEMPTS_PER_MINUTE` |
| `/auth/driver-invite/accept` | 15/min | `AUTH_DRIVER_INVITE_ACCEPT_MAX_ATTEMPTS_PER_MINUTE` |
| `/auth/login` | 10/min per IP | Recommended — not yet documented |

Implement via Redis sliding window.

---

## Session vs token

| Surface | Model |
|---------|-------|
| Merchant portal | Clerk session cookies + JWT |
| Website booking | Stateless OTP → short-lived session token |
| Driver app | Bearer JWT + secure store |
| Fleetbase console | Laravel session + Sanctum |
| API integrations | API key or OAuth (future) |

---

## Security requirements

| Requirement | Implementation |
|-------------|----------------|
| HTTPS everywhere | Production TLS 1.2+ |
| JWT expiry | Access: 15–60 min; refresh: 7–30 days |
| Invite token expiry | `DRIVER_INVITE_TOKEN_EXPIRE_SECONDS=604800` (7 days) |
| Password policy | Min 12 chars, complexity (enforce in API) |
| MFA | Clerk MFA for merchant admins (recommended) |
| Secret rotation | Clerk, Stripe, Twilio keys quarterly |

---

## Authentication gaps (current)

| Gap | Risk | Remediation |
|-----|------|-------------|
| Website has no auth middleware | Low (marketing only) | Add when portal routes merge |
| `details.md` contains live Clerk secrets | **Critical** | Rotate + remove from git |
| No unified role RBAC in API repo | Medium | Implement in `apps/api` |
| Driver push uses FCM but app has no push | Low | Document as API-only for now |
| Support/Sales roles undefined in code | Medium | Define in Clerk metadata + API |

---

## Related documents

- [INTEGRATIONS.md](./INTEGRATIONS.md) — Clerk, Supabase, Firebase details
- [SECURITY.md](./SECURITY.md) — JWT hardening, secrets management
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) — Auth env vars

---

*Source: CONNECTIONS.md, details.md, PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md, website/src/middleware.ts*
