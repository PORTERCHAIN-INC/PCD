# Porterchain ↔ Fleetbase Single Sign-On (SSO)

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Version:** 1.1  
**Goal:** Porterchain users never see the Fleetbase login screen

---

## Summary

| Aspect               | Approach                                                                 |
| -------------------- | ------------------------------------------------------------------------ |
| Identity provider    | **PorterChain staff IdP** (admin Redis session; Clerk retired for admin) |
| Trust broker         | **Porterchain API** (`POST /v1/auth/sso/fleetbase`)                      |
| Fleetbase auth       | Trusts **Porterchain-signed SSO JWT**                                    |
| User duplication     | **None** — one staff subject → one `identity_links` row → Fleetbase user |
| Password duplication | **None** — Fleetbase users provisioned without Porterchain passwords     |
| Permission sync      | AdminRole → Fleetbase IAM on each SSO exchange                           |

---

## Architecture

```
┌─────────────┐  staff_sess_* /    ┌──────────────────┐
│ Admin Portal│  pc_staff_sid ───► │ Porterchain API  │
│ (staff IdP) │                    │  SsoService      │
└─────────────┘                    │  ├─ staff session │
                                   │  ├─ SpiceDB role  │
                                   │  ├─ issue SSO JWT │
                                   │  └─ sync perms    │
                                   └────────┬─────────┘
                                            │ Porterchain SSO JWT
                                            ▼
                                   ┌──────────────────┐
                                   │ Fleetbase API    │
                                   │ /porterchain/sso │
                                   └────────┬─────────┘
                                            │ session
                                            ▼
                                   ┌──────────────────┐
                                   │ Fleetbase Console│
                                   │ (no login form)  │
                                   └──────────────────┘
```

---

## Porterchain SSO JWT

**Signed with:** `SSO_JWT_SECRET` (HS256)  
**Issuer:** `porterchain`  
**Audience:** `fleetbase`  
**TTL:** `SSO_TOKEN_TTL_SECONDS` (default 300)

### Claims

```json
{
  "iss": "porterchain",
  "aud": "fleetbase",
  "sub": "<platform_user_id>",
  "clerk_user_id": "user_...",
  "user_type": "dispatcher",
  "email": "ops@porterchain.com",
  "roles": ["dispatcher"],
  "permissions": ["dispatch:manage", "order:read", "order:write"],
  "jti": "<uuid>",
  "iat": 1719660000,
  "exp": 1719660300
}
```

Fleetbase SSO bridge validates:

1. Signature (`SSO_JWT_SECRET` / `PORTERCHAIN_SSO_JWT_SECRET`)
2. `aud === "fleetbase"`
3. `exp` not expired
4. `iss === "porterchain"`

---

## API endpoints

### Issue SSO session

```http
POST /v1/auth/sso/fleetbase
Authorization: Bearer <clerk_jwt>
```

**Authorized roles:** `dispatcher`, `admin`, `super_admin`, `fleet_manager`, `support`, `support_lead`

**Response:**

```json
{
  "sso_token": "eyJ...",
  "expires_in": 300,
  "console_url": "http://localhost:4200/porterchain/sso?token=eyJ...",
  "fleetbase_user_uuid": "uuid-or-null-until-bridge",
  "roles": ["dispatcher"],
  "permissions": ["dispatch:manage", "order:read"],
  "fleetbase_session": null
}
```

### Current user + SSO eligibility

```http
GET /v1/auth/me
Authorization: Bearer <clerk_jwt>
```

---

## Fleetbase trust bridge (extension endpoints)

Porterchain calls these Fleetbase internal endpoints (implemented via `porterchain-bridge` extension):

| Endpoint                                                | Purpose                                               |
| ------------------------------------------------------- | ----------------------------------------------------- |
| `POST /int/v1/porterchain/sso/exchange`                 | Validate SSO JWT, provision/find user, return session |
| `POST /int/v1/porterchain/sso/users/{uuid}/permissions` | Sync IAM permissions                                  |

### Exchange request

```json
{
  "sso_token": "<porterchain-jwt>",
  "email": "dispatcher@porterchain.com",
  "clerk_user_id": "user_abc",
  "company_uuid": "<fleetbase-company-uuid>",
  "fleetbase_permissions": ["fleet-ops dispatch order"],
  "fleetbase_roles": ["dispatcher"]
}
```

### Exchange response (expected)

```json
{
  "fleetbase_user_uuid": "...",
  "sanctum_token": "...",
  "roles_assigned": ["dispatcher"]
}
```

**Until the Fleetbase extension is fully deployed:** Porterchain issues `sso_token` and `console_url`; the Fleetbase console route `/porterchain/sso` consumes the token (see `services/fleetbase/porterchain_fleetbase/sso/`).

---

## Who cannot use SSO

Merchants, customers, and drivers receive **403** from `POST /v1/auth/sso/fleetbase`. Console access is ops-only per [auth-clerk-spicedb.md](./docs/architecture/auth-clerk-spicedb.md).

---

## User provisioning (no duplicates)

| Step | Action                                                                             |
| ---- | ---------------------------------------------------------------------------------- |
| 1    | Clerk user signs into Porterchain admin                                            |
| 2    | Resolve `admin_users` by `clerk_user_id` + SpiceDB `platform#admin`                |
| 3    | `IdentityLink` created/updated with `clerk_user_id` as canonical key               |
| 4    | SSO exchange finds or creates Fleetbase user by `clerk_user_id` + `email`          |
| 5    | `admin_users.fleetbase_user_uuid` and `identity_links.fleetbase_user_uuid` updated |

Fleetbase user is linked — not a second login account with a separate password.

---

## Permission synchronization

On each `POST /v1/auth/sso/fleetbase`:

1. Resolve Porterchain admin role
2. Map to `fleetbase_permissions` via `ADMIN_TO_FLEETBASE_PERMISSIONS`
3. Store on `identity_links`
4. Push to Fleetbase via `/sso/users/{uuid}/permissions`

| Porterchain role              | Fleetbase sync                      |
| ----------------------------- | ----------------------------------- |
| Role change in Porterchain    | Next SSO exchange updates Fleetbase |
| User suspended in Porterchain | SSO returns 403 before exchange     |
| Merchant/driver/customer      | SSO endpoint returns 403            |

---

## Console integration (admin portal)

**Operations page** → **Open Fleetbase Console (SSO)**

1. Calls `POST /v1/auth/sso/fleetbase` with Clerk JWT
2. Opens `console_url` in new tab
3. Fleetbase console route `/porterchain/sso` validates token and establishes session

**Fleetbase Ember UI is not modified** in this repository — SSO entry route is a documented extension point for Fleetbase `porterchain-bridge` package.

---

## Environment configuration

### Porterchain API

```env
CLERK_JWKS_URL=https://....clerk.accounts.dev/.well-known/jwks.json
CLERK_SECRET_KEY=sk_...
SSO_JWT_SECRET=<shared-secret-with-fleetbase>
SSO_TOKEN_TTL_SECONDS=300
FLEETBASE_CONSOLE_URL=http://localhost:4200
FLEETBASE_SSO_ENABLED=true
FLEETBASE_API_URL=http://localhost:8000
FLEETBASE_API_KEY=flb_live_...
FLEETBASE_DEFAULT_COMPANY_UUID=...
```

### Fleetbase (extension)

```env
PORTERCHAIN_SSO_JWT_SECRET=<same-as-SSO_JWT_SECRET>
PORTERCHAIN_API_URL=http://localhost:8001
```

---

## Security checklist

| Item                                        | Status               |
| ------------------------------------------- | -------------------- |
| HTTPS in production                         | Required             |
| Short SSO token TTL (5 min)                 | Implemented          |
| Clerk JWKS verification                     | Implemented          |
| Fleetbase SSO signature verification        | Implemented (bridge) |
| Merchants blocked from console SSO          | Implemented          |
| No Fleetbase password for Porterchain users | By design            |
| Permission sync on SSO                      | Implemented          |

---

## Failure modes

| Scenario                      | Behavior                                                      |
| ----------------------------- | ------------------------------------------------------------- |
| Fleetbase bridge unavailable  | Returns `sso_token` + `console_url`; `fleetbase_session` null |
| User not in `admin_users`     | 403 `user_not_provisioned`                                    |
| Role lacks console access     | 403 `fleetbase_console_forbidden`                             |
| `SSO_JWT_SECRET` missing      | 503 `sso_jwt_secret_not_configured`                           |
| `FLEETBASE_SSO_ENABLED=false` | 503 `fleetbase_sso_disabled`                                  |

---

## Code references

| Component               | Path                                                                                          |
| ----------------------- | --------------------------------------------------------------------------------------------- |
| SSO service             | `apps/api/src/porterchain_api/auth/sso_service.py`                                            |
| Auth router             | `apps/api/src/porterchain_api/routers/auth.py`                                                |
| Identity links          | `apps/api/src/porterchain_api/identity_models.py`                                             |
| Fleetbase role map      | `apps/api/src/porterchain_api/auth/fleetbase_roles.py`                                        |
| Fleetbase SSO client    | `services/fleetbase-adapter/porterchain_fleetbase_adapter/auth/__init__.py`                   |
| Fleetbase bridge API    | `packages/porterchain-bridge` → `POST /int/v1/porterchain/sso/*`                              |
| Fleetbase console route | `packages/porterchain-bridge/console` → synced to `apps/fleetbase/console` `/porterchain/sso` |
| Admin SSO button        | `apps/admin/src/app/(ops)/operations/page.tsx`                                                |

---

## Related documents

| Document                                                                               | Purpose               |
| -------------------------------------------------------------------------------------- | --------------------- |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)                     | Auth policy           |
| [docs/architecture/AUTHENTICATION_FLOW.md](./docs/architecture/AUTHENTICATION_FLOW.md) | Flow diagrams         |
| [auth-clerk-spicedb.md](./docs/architecture/auth-clerk-spicedb.md)                     | Console access matrix |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                                 | Fleetbase bridge      |
| [FLEETBASE_MODULES.md](FLEETBASE_MODULES.md)                                           | Extension endpoints   |

---
