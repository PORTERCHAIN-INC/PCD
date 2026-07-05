# Clerk Integration Report

**Last verified:** 2026-07-04  
**Authority:** [masterrule.md](./masterrule.md) §15  
**Canonical:** [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)

---

## Executive summary

Clerk is the **sole identity provider** across Porterchain. Every authenticated API request syncs into canonical `porterchain_users`. **No passwords in Porterchain DB** — Clerk owns credentials, MFA, and verification.

Supabase/Twilio OTP paths removed (see [AUTHENTICATION_CLEANUP.md](./AUTHENTICATION_CLEANUP.md)).

---

## Application verification

| Application     | Port | Clerk SDK           | Route protection                             | API auth                 |
| --------------- | ---- | ------------------- | -------------------------------------------- | ------------------------ |
| Website         | 3000 | `@clerk/nextjs`     | `clerkMiddleware` + i18n                     | Clerk JWT → API          |
| Merchant        | 3001 | `@clerk/nextjs`     | `auth.protect()`                             | `get_merchant_context`   |
| Admin           | 3002 | `@clerk/nextjs`     | `auth.protect()`                             | `get_admin_context`      |
| Driver web      | 3003 | `@clerk/nextjs`     | Sign-in + session                            | Clerk → Porterchain JWT  |
| Customer        | 3004 | `@clerk/nextjs`     | `middleware.ts` (protect all except sign-in) | `/v1/customers/*`        |
| Driver mobile   | Expo | `@clerk/clerk-expo` | `ClerkBridge`                                | Clerk → driver API login |
| Customer mobile | Expo | `@clerk/clerk-expo` | App providers                                | Clerk JWT → API          |

### Customer app (`apps/customer/`)

Dedicated retail portal at **`:3004`** (website links via `NEXT_PUBLIC_CUSTOMER_PORTAL_URL`). Legacy website embed at `/portal/customer` remains — prefer dedicated app for new work.

### Driver surfaces

- Web: Clerk `SignIn` → `driverApi.login(email, clerkToken)` → Porterchain session JWT
- Mobile: `getClerkBearerToken()` → API login
- Subsequent calls: Porterchain JWT via `get_driver_context` — not a second IdP

---

## Canonical user registry

### Table: `porterchain_users`

| Column           | Purpose                  |
| ---------------- | ------------------------ |
| `clerk_user_id`  | Unique Clerk `sub`       |
| `email`, `phone` | From Clerk claims        |
| `role`, `status` | Primary RBAC + lifecycle |
| `profile`        | Name, org metadata       |
| `last_synced_at` | Sync timestamp           |

**Migration:** `j1k2l3m4n5o6_porterchain_users.py`

### Sync service

**Path:** `auth/user_sync_service.py`

`UserSyncService.sync(db, claims)` on every `get_clerk_claims`:

1. Link pending domain records by email
2. `PrincipalResolver` → platform principal
3. Upsert `porterchain_users` + `identity_links`

Also invoked from `DriverAuthService.login()` after Clerk verification.

---

## Portal guard

**Path:** `auth/portal_guard.py`

- `assert_clerk_id_exclusive` — prevent cross-portal Clerk ID reuse
- `require_clerk_app_for_portal` — separate Clerk apps per portal when configured
- Used in `auth/admin.py`, `merchant.py`, `customer.py`, driver auth

---

## Password policy

| Rule                   | Implementation                  |
| ---------------------- | ------------------------------- |
| Never store passwords  | No password columns             |
| Clerk owns credentials | Hosted sign-up / reset / MFA    |
| Driver session JWT     | Issued after Clerk login only   |
| Dev bypass             | `CLERK_DEV_BYPASS` — local only |

---

## API authentication flow

```
Frontend → Clerk sign-in → Bearer JWT
         → get_clerk_claims() → JWKS verify
         → UserSyncService.sync() → porterchain_users
         → Context resolver (admin / merchant / customer / driver)
         → *_engine service
```

### Key modules

| Module                                                     | Role                                       |
| ---------------------------------------------------------- | ------------------------------------------ |
| `auth/clerk.py`                                            | JWKS + sync hook                           |
| `auth/user_sync_service.py`                                | Canonical upsert                           |
| `auth/principal_resolver.py`                               | Clerk → principal                          |
| `auth/admin.py`, `merchant.py`, `customer.py`, `driver.py` | Context                                    |
| `routers/auth.py`                                          | `/v1/auth/me`, admin access, Fleetbase SSO |

---

## Environment variables

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md):

| Variable                            | Surfaces           |
| ----------------------------------- | ------------------ |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Next.js apps       |
| `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` | Mobile             |
| `CLERK_SECRET_KEY`                  | API + Next server  |
| `CLERK_JWKS_URL`                    | API verification   |
| Per-portal `CLERK_*_SECRET_KEY`     | Optional isolation |
| `CLERK_DEV_BYPASS`                  | Local only         |

---

## Gaps (non-blocking)

| Gap                                            | Priority                            |
| ---------------------------------------------- | ----------------------------------- |
| Clerk webhook for `user.updated`               | Low — sync on each request suffices |
| Backfill legacy users into `porterchain_users` | Medium — occurs on next login       |
| Deprecate website embedded customer portal     | Low — use `apps/customer/`          |

---

## Related

| Document                                                                               | Purpose              |
| -------------------------------------------------------------------------------------- | -------------------- |
| [docs/architecture/AUTHENTICATION_FLOW.md](./docs/architecture/AUTHENTICATION_FLOW.md) | Flow diagrams        |
| [SSO.md](./SSO.md)                                                                     | Fleetbase SSO bridge |
