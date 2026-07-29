# Unified identity — impact report

**Status:** HISTORICAL (Phase 1 audit). Authorization SSOT is now [auth-clerk-spicedb.md](./auth-clerk-spicedb.md).

**Type:** WORKING  
**Date:** 2026-07-28  
**Constraint:** No production Clerk / Doppler / database mutations in this workstream.

Companion docs:

- [unified-identity-target.md](./unified-identity-target.md) (superseded stub)
- [auth-clerk-spicedb.md](./auth-clerk-spicedb.md) (**current**)
- [clerk-consolidation.md](../runbooks/clerk-consolidation.md)

---

## 1. Executive verdict

| Concern                           | Today                                                                          | Target direction                                             |
| --------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| Clerk apps                        | **4 isolated** (customer / merchant / admin / driver)                          | **1** “PorterChain Platform”                                 |
| Authorization SoT                 | PorterChain DB (`admin_users`, `merchant_users`, module matrices)              | Keep / extend — multi-role                                   |
| Clerk user IDs on business tables | **Yes** (`clerk_user_id` unique on admin/merchant/customer/drivers + registry) | Auth identities only; business FKs → internal UUID           |
| Multi-role same Clerk subject     | **Blocked** by `assert_clerk_id_exclusive`                                     | Required                                                     |
| Clerk webhooks                    | **Not implemented**                                                            | Required (signed + idempotent)                               |
| Mobile Clerk                      | **Blank Expo shells** — no SDK                                                 | Later (P2); sync already writes unused `EXPO_PUBLIC_CLERK_*` |

---

## 2. Dirty tree preserved (Phase 1 start)

Unrelated local changes left untouched:

- `apps/admin/next-env.d.ts`
- `apps/customer/next-env.d.ts`
- `apps/driver-portal/next-env.d.ts`
- `apps/merchant-portal/next-env.d.ts`
- `docs/ICP_15_SECOND_TEST_LOG.md`

No `git reset` / checkout of unrelated files.

---

## 3. Deployable inventory

| Path                         | Role                    | Clerk today                                   |
| ---------------------------- | ----------------------- | --------------------------------------------- |
| `apps/api`                   | FastAPI `:8001`         | JWKS verify + selective Backend API           |
| `apps/worker`                | Background jobs         | Same `CLERK_*` as API (no UI)                 |
| `apps/admin`                 | Admin portal            | `@clerk/nextjs` `^7.5.14`                     |
| `apps/merchant-portal`       | Merchant portal         | `@clerk/nextjs` `^7.5.14`                     |
| `apps/customer`              | Customer portal         | `@clerk/nextjs` `^7.5.14`                     |
| `apps/driver-portal`         | Driver web              | Clerk at login → PorterChain JWT cookies      |
| `website/`                   | Marketing + retail      | `@clerk/nextjs` `^7.5.14` (customer app keys) |
| `apps/mobile-customer`       | Expo 57 shell           | **No** Clerk dependency                       |
| `apps/mobile-driver`         | Expo 57 shell           | **No** Clerk dependency                       |
| `services/fleetbase-adapter` | Fleetbase HTTP boundary | Machine API key; SSO exchange only            |
| `services/driver-platform`   | Driver JWT helpers      | `JWT_SECRET` — not Clerk                      |
| `apps/fleetbase`             | Vendor tree             | Not PorterChain IdP                           |

Root `AGENTS.md` does **not** exist (only `website/AGENTS.md`).

---

## 4. Clerk integration map

### 4.1 SDK / providers

| Surface  | Provider / middleware                                                                              |
| -------- | -------------------------------------------------------------------------------------------------- |
| Admin    | `apps/admin/src/components/providers/AppClerkProvider.tsx`, `middleware.ts`, `AdminAccessGate.tsx` |
| Merchant | `apps/merchant-portal/.../AppClerkProvider.tsx`, `middleware.ts`, `MerchantAccessGate.tsx`         |
| Customer | `apps/customer/src/components/AppClerkProvider.tsx`, `middleware.ts`, `CustomerAccessGate.tsx`     |
| Driver   | `apps/driver-portal/.../AppClerkProvider.tsx`; **middleware uses cookie**, not Clerk session       |
| Website  | `website/src/components/providers/ClerkProviderShell.tsx`, conditional middleware                  |

### 4.2 API auth modules

| File                                            | Responsibility                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------ |
| `auth/clerk_registry.py`                        | 4-app config, JWKS URL list, mode enterprise/legacy                      |
| `auth/clerk.py`                                 | JWT verify (JWKS cache), FastAPI deps                                    |
| `auth/claims.py`                                | `ClerkClaims` + `metadata_role`                                          |
| `auth/portal_guard.py`                          | App mismatch + identity exclusivity                                      |
| `auth/user_sync_service.py`                     | Upsert `porterchain_users` / `identity_links`                            |
| `auth/clerk_client.py`                          | Clerk Backend API (invites / directory)                                  |
| `auth/admin.py` / `merchant.py` / `customer.py` | Portal contexts                                                          |
| `auth/driver.py`                                | PorterChain driver JWT decode                                            |
| `auth/dev.py`                                   | Local bypass gate                                                        |
| `auth/invitation_service.py`                    | Invites; `OPEN_SIGNUP_USER_TYPES = {customer}`                           |
| `auth/sso_service.py` / `fleetbase_roles.py`    | Admin Fleetbase SSO (out of rewrite scope)                               |
| `routers/auth.py`                               | `/v1/auth/me`, `/session-context`, SSO (**`/*/access` removed 2026-07**) |

**Per-request path:** JWKS verify → `UserSyncService.sync()` → portal guard → context.  
**Not** per-request: Clerk Backend API (used for invites/directory/email hydrate only).

**Webhooks:** none (no Svix / `/webhooks/clerk`).

### 4.3 Auth endpoints

| Method | Path                                        |
| ------ | ------------------------------------------- |
| GET    | `/v1/auth/me`                               |
| GET    | `/v1/auth/session-context`                  |
| GET    | `/v1/auth/*/onboarding` (merchant/customer) |
| POST   | `/v1/auth/sso/fleetbase`                    |

> **Removed (2026-07):** `GET /v1/auth/{admin,merchant,customer}/access` — use session-context + SpiceDB.

---

## 5. Environment variable names (no values)

### Enterprise (current prod design)

`CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_{SECRET_KEY,PUBLISHABLE_KEY,JWKS_URL}` — 12 keys.

### Frontend mapped

`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` (per-portal container mapping),  
`NEXT_PUBLIC_CLERK_SIGN_IN_URL`, `NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL`,  
`NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL`, `NEXT_PUBLIC_CLERK_AFTER_SIGN_OUT_URL`.

### Bypass

`CLERK_DEV_BYPASS`, `NEXT_PUBLIC_CLERK_DEV_BYPASS`.

### Legacy

`CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `CLERK_JWKS_URL`.

### Sync-only / unused in mobile code

`EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` (written by `pnpm clerk:sync`).

### Doppler / GitHub (names)

`DOPPLER_TOKEN`, `DOPPLER_PROJECT` (`pcd`), `DOPPLER_CONFIG` (`prd`).  
Doppler runtime also holds non-Clerk secrets per `docs/SECRETS_MAP.md`.  
`FLEETBASE_*` — **blocked (DD-05b)**.

Sources: `env/clerk.env.example`, `env/api.env.example`, `env/production.env.example`,  
`infrastructure/deploy/docker-compose.prod.yml`, `.github/workflows/deploy.yml`,  
`scripts/sync-clerk-env.mjs`, `docs/SECRETS_MAP.md`.

---

## 6. Database columns with Clerk identity

| Table               | Column                                 | Unique         | Business identity today?                     |
| ------------------- | -------------------------------------- | -------------- | -------------------------------------------- |
| `porterchain_users` | `clerk_user_id`                        | yes            | Registry (1:1 Clerk)                         |
| `identity_links`    | `clerk_user_id`                        | yes            | Link + Fleetbase fields                      |
| `admin_users`       | `clerk_user_id`                        | yes            | **Yes** — staff auth                         |
| `merchant_users`    | `clerk_user_id`                        | yes            | **Yes** — membership                         |
| `customers`         | `clerk_user_id`                        | yes            | **Yes** — retail                             |
| `drivers`           | `clerk_user_id`                        | yes (nullable) | Linked; API uses driver JWT                  |
| `merchants`         | `clerk_org_id`                         | yes (nullable) | Legacy/dev marker — **not** Clerk Orgs authz |
| `user_invitations`  | `clerk_user_id`, `clerk_invitation_id` | indexed        | Invite tracking                              |

Migrations: `bd830e39ef4e_initial_schema.py`, `j1k2l3m4n5o6_porterchain_users.py`, `k2l3m4n5o6p7_user_invitations.py`.

---

## 7. Authorization assumptions (risk hotspots)

| Assumption                | Evidence                                     | Risk for unify                              |
| ------------------------- | -------------------------------------------- | ------------------------------------------- |
| Portal token ⇒ user class | `portal_guard.require_clerk_app_for_portal`  | Breaks under one issuer                     |
| One Clerk id ⇒ one class  | `assert_clerk_id_exclusive`                  | Blocks multi-role target                    |
| Authenticated ≈ can book  | `routers/quotes.py` uses `get_clerk_user_id` | Needs explicit permission                   |
| Email links pending rows  | `user_sync_service`, invitations             | OK as match signal only — never admin grant |
| Admin invite-only         | AccessGate + `admin_users` row               | Keep                                        |
| Customer open signup      | `OPEN_SIGNUP_USER_TYPES`                     | Keep policy; minimal role only              |
| UI AccessGate = security  | Portal gates                                 | Server must remain SoT (#5)                 |

---

## 8. Roles / permissions today

**AdminRole:** `super_admin`, `admin`, `dispatcher`, `support`, `support_lead`, `sales`, `sales_manager`, `finance`, `compliance`, `developer`, `marketing`, `read_only`, `fleet_manager` — `admin_engine/rbac.py`.

**MerchantRole:** `merchant_owner`, `merchant_admin`, `merchant_ops`, `merchant_finance`, `merchant_readonly` — `merchant_engine/rbac.py`.

**Customer / driver:** no sub-roles; driver gated by status enum.

**Enterprise coarse:** `porterchain_shared/auth/enterprise_roles.py` via `/v1/auth/me` (legacy fields); prefer `/v1/auth/session-context`.

---

## 9. Dependencies

| Package             | Version range               | Where                                                    |
| ------------------- | --------------------------- | -------------------------------------------------------- |
| `@clerk/nextjs`     | `^7.5.14`                   | admin, merchant-portal, customer, driver-portal, website |
| `@clerk/clerk-expo` | —                           | **Not installed**                                        |
| API JWT             | `python-jose[cryptography]` | JWKS RS256 verify                                        |

Frontend freeze: do not bump Next/React/Clerk majors without approval (`dependency-freeze.mdc`).

---

## 10. Existing tests vs gaps

| Present                                           | Gap                               |
| ------------------------------------------------- | --------------------------------- |
| `test_clerk_registry.py` (mode enterprise/legacy) | Multi-JWKS kid selection / verify |
| New `test_unified_identity_characterization.py`   | End-to-end AccessGate HTTP        |
| IDOR / tenant tests                               | Clerk webhook (none to test yet)  |
| Partial UserSync coverage                         | Driver Clerk→JWT HTTP exchange    |
|                                                   | Portal FE tests for Clerk         |
|                                                   | Mobile (N/A until wired)          |

---

## 11. Doc / prompt conflicts (adapt, do not guess)

| Prompt / old doc assumption     | Repo fact                                                         |
| ------------------------------- | ----------------------------------------------------------------- |
| Introduce `porterchain_users`   | **Already exists**                                                |
| Mobile uses `@clerk/clerk-expo` | Docs claim it; **code does not** (`AUTHENTICATION_FLOW.md` stale) |
| Root `AGENTS.md`                | Missing                                                           |
| Clerk Backend API every request | False — JWKS + DB sync                                            |
| Same person across portals      | Explicitly forbidden today                                        |
| `apps/website` deployable       | Alias only; real app is `website/`                                |
| Merchant Clerk Organizations    | Code: **not** used for merchant authz                             |

---

## 12. Proposed change surface (later phases)

### Phase 2 (done locally)

- `auth/unified_catalog.py` — AssignableRole + UnifiedPermission packs
- Extended `porterchain_users` / `identity_links`
- New: `user_emails`, `user_role_assignments`, `user_permission_overrides`, `access_audit_logs`, migration tables
- Alembic `w6x7y8z9a0b1` (additive only)

### Still upcoming

1. ~~IdentityProvider + CurrentPrincipal~~ **Phase 3 done (dual-read)**
2. ~~Webhooks + ensure-user (no elevate)~~ **Phase 4 done**
3. Dual-write assignments continue; stop exclusive portal class gradually.
4. Backfill business FKs to `porterchain_users.id`; keep `clerk_user_id` (Phase 8).
5. Point all Next apps at one publishable key (Phase 5–6).
6. Doppler matrix + startup validation + config-audit (Phase 6 — local only).
7. Migration CLI audit→plan→dry-run→apply (Phase 7 — local only).
8. Profile FK backfill to `porterchain_users.id` (Phase 8 — additive; legacy cols kept).
9. Full test matrix 401/403/IDOR/webhook/idempotency (Phase 9 — `pnpm identity:test`).
10. Manual cutover runbook only (Phase 10 — [clerk-cutover-phase10.md](../runbooks/clerk-cutover-phase10.md)); production remains founder-owned.
11. Mobile Clerk + min-supported-version before retiring old keys.
12. Migrate routers from portal contexts → `require_permission` incrementally.

**Out of scope:** Fleetbase bridge rewrite, billing, dispatch, Stripe, unrelated dirty-tree files.

---

## 13. Characterization test commands

```bash
cd apps/api && .venv/bin/python -m pytest \
  tests/test_unified_identity_characterization.py \
  tests/test_clerk_registry.py -q
```

**Result (2026-07-28):** `18 passed`.
