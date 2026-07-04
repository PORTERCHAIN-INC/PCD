# Clerk Integration Report

**Date:** July 1, 2026  
**Authority:** [masterrule.md](./masterrule.md) §15  
**Status:** Implemented

---

## Executive summary

Clerk is the **sole identity provider** across all Porterchain surfaces. Every Clerk-authenticated API request synchronizes identity into the canonical `porterchain_users` table. **No passwords are stored in Porterchain** — Clerk owns credentials, MFA, and verification.

---

## Application verification

| Application         | Port | Clerk SDK           | Middleware                            | API auth                                  | Session model              |
| ------------------- | ---- | ------------------- | ------------------------------------- | ----------------------------------------- | -------------------------- |
| **Website**         | 3000 | `@clerk/nextjs`     | `clerkMiddleware` + locale routing    | Clerk JWT → API                           | Clerk session              |
| **Merchant**        | 3001 | `@clerk/nextjs`     | `auth.protect()` on private routes    | `get_merchant_context`                    | Clerk session              |
| **Admin**           | 3002 | `@clerk/nextjs`     | `auth.protect()` on private routes    | `get_admin_context`                       | Clerk session              |
| **Driver web**      | 3003 | `@clerk/nextjs`     | Login via Clerk; API uses session JWT | Clerk → `/auth/login` → Porterchain JWT   | Clerk + API session bridge |
| **Customer**        | 3004 | `@clerk/nextjs`     | `auth.protect()` on `/dashboard`      | Clerk JWT → `/v1/customers/*`             | Clerk session              |
| **Driver mobile**   | Expo | `@clerk/clerk-expo` | `ClerkBridge`                         | Clerk token → `/driver-api/v1/auth/login` | Clerk + API session bridge |
| **Customer mobile** | Expo | `@clerk/clerk-expo` | `ClerkBridge`                         | Clerk JWT → `/v1/auth/me`                 | Clerk session              |

### Website (`website/`)

- `AppClerkProvider` in `[locale]/layout.tsx`
- `clerkMiddleware` in `middleware.ts` (configured when keys present)
- Booking continue flow: `SignIn` from Clerk on `book/continue/page.tsx`
- Customer portal embed: `useAuth` on `portal/customer/page.tsx`

### Admin (`apps/admin/`)

- `AdminAuthProvider` + `AppClerkProvider`
- `middleware.ts` protects all routes except `/sign-in`
- `AdminAccessGate` calls `GET /v1/auth/admin/access`

### Merchant (`apps/merchant-portal/`)

- `AppClerkProvider` + `middleware.ts` protects non sign-in/up routes
- API calls attach Clerk bearer via client hooks

### Driver (`apps/driver-portal/`, `apps/mobile-driver/`)

- Web: `SignIn` from Clerk → `driverApi.login(email, clerkToken)` exchanges for Porterchain session JWT
- Mobile: `getClerkBearerToken()` → `api.login(email, clerkToken)`
- **No password field** in dev login UI (email-only local bypass when `CLERK_DEV_BYPASS=true`)
- Subsequent driver API calls use Porterchain JWT (`get_driver_context`) — not a second IdP

### Customer (`apps/customer/`)

- `AppClerkProvider` in root layout
- **Added** `middleware.ts` — protects `/dashboard` (home redirects there)
- Dashboard uses `getToken()` → Porterchain API

---

## Canonical user registry

### Table: `porterchain_users`

| Column           | Type            | Purpose                                                                      |
| ---------------- | --------------- | ---------------------------------------------------------------------------- |
| `id`             | UUID            | Porterchain user primary key                                                 |
| `clerk_user_id`  | string (unique) | Clerk `sub` claim                                                            |
| `email`          | string          | Primary email from Clerk                                                     |
| `phone`          | string          | From Clerk JWT or domain record                                              |
| `role`           | string          | Primary RBAC role (`super_admin`, `merchant_owner`, `driver`, `customer`, …) |
| `status`         | string          | `active`, `inactive`, `pending`, `suspended`                                 |
| `profile`        | JSON            | Name, platform_user_id, org_id, metadata                                     |
| `last_synced_at` | timestamp       | Last Clerk sync                                                              |

**Migration:** `apps/api/alembic/versions/j1k2l3m4n5o6_porterchain_users.py`

### Sync service

**Path:** `apps/api/src/porterchain_api/auth/user_sync_service.py`

`UserSyncService.sync(db, claims)` runs on **every** `get_clerk_claims` invocation:

1. Links pending domain records by email (`admin_users`, `merchant_users`, `drivers`)
2. Resolves platform principal via `PrincipalResolver`
3. Upserts `porterchain_users`
4. Upserts `identity_links` when provisioned

Also called from `DriverAuthService.login()` after Clerk verification.

---

## Password policy

| Rule                   | Implementation                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| Never store passwords  | No `password` column in any Porterchain table                                                 |
| Clerk owns credentials | Sign-up, reset, MFA in Clerk hosted UI                                                        |
| Driver session JWT     | API session token only — issued **after** Clerk login                                         |
| Dev bypass             | `CLERK_DEV_BYPASS` + email-only driver login — local only                                     |
| Provision script       | `provision_merchant_user.py` sets Clerk password via Clerk API — not stored in Porterchain DB |

---

## API authentication flow

```
Frontend → Clerk sign-in → session JWT
         → Authorization: Bearer <clerk_jwt>
         → get_clerk_claims()
              → verify_clerk_token() (JWKS)
              → UserSyncService.sync() → porterchain_users
         → Context resolver (admin / merchant / customer / driver)
         → Application Service
```

### Key modules

| Module                       | Role                                          |
| ---------------------------- | --------------------------------------------- |
| `auth/clerk.py`              | JWKS verification + sync hook                 |
| `auth/user_sync_service.py`  | Canonical user upsert                         |
| `auth/principal_resolver.py` | Clerk → platform principal                    |
| `auth/admin.py`              | Admin RBAC context                            |
| `auth/merchant.py`           | Merchant org context                          |
| `auth/driver.py`             | Porterchain JWT context (post-Clerk)          |
| `routers/auth.py`            | `/v1/auth/me`, `/admin/access`, Fleetbase SSO |

### `/v1/auth/me` response (extended)

Returns `clerk_user_id`, `email`, `phone`, `role`, `status`, `profile` from `porterchain_users` plus RBAC `permissions` from domain principal.

---

## Duplicate logic removed

| Before                                                            | After                                                         |
| ----------------------------------------------------------------- | ------------------------------------------------------------- |
| Admin email→clerk linking in `admin.py` + `principal_resolver.py` | Centralized in `UserSyncService._link_pending_domain_records` |
| Identity link upsert only on SSO                                  | Synced on every auth + SSO                                    |
| Separate OTP/Supabase/Twilio auth                                 | Removed (prior cleanup)                                       |

---

## Domain tables (RBAC — not duplicate auth)

Clerk syncs into `porterchain_users`; domain tables hold business RBAC:

| Table            | User type                            |
| ---------------- | ------------------------------------ |
| `admin_users`    | Admin, dispatcher, support, sales    |
| `merchant_users` | Merchant org members                 |
| `drivers`        | Driver operations profile            |
| `customers`      | Retail customer orders               |
| `identity_links` | Clerk ↔ platform ↔ Fleetbase mapping |

---

## Environment variables

| Variable                            | Surfaces             |
| ----------------------------------- | -------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | All Next.js apps     |
| `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` | Mobile apps          |
| `CLERK_SECRET_KEY`                  | API + Next.js server |
| `CLERK_JWKS_URL`                    | API JWT verification |
| `CLERK_DEV_BYPASS`                  | Local dev only       |

---

## Gaps and follow-up

| Gap                                                     | Priority | Notes                                                  |
| ------------------------------------------------------- | -------- | ------------------------------------------------------ |
| Backfill existing domain users into `porterchain_users` | Medium   | Run sync on next login or one-time migration script    |
| Customer auto-provision on first `/auth/me`             | Low      | Today requires `customers` row for dashboard data      |
| Driver API: Clerk JWT on every request                  | Low      | Session JWT bridge is intentional for mobile offline   |
| Clerk webhook for user.updated                          | Low      | Polling via sync on each request is sufficient for now |

---

## Related documents

- [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)
- [AUTHENTICATION.md](./AUTHENTICATION.md)
- [AUTHENTICATION_CLEANUP.md](./AUTHENTICATION_CLEANUP.md)
- [docs/architecture/AUTHENTICATION_FLOW.md](./docs/architecture/AUTHENTICATION_FLOW.md)

---

_Verified against masterrule.md §15 — Clerk for authentication; JWT validation on API; RBAC in engines._
