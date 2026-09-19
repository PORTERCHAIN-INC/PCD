# Authentication — Driver + Admin development test matrix

**Type:** DEVELOPMENT TEST SSOT (identity / session / authz / vendor handshakes)  
**Verified:** 2026-09-17  
**Sensors:** Graphify (Moment A) → CodeGraph (Moment B) → Ripwire (Moment C)

| Meta                   | Value                                                                                                                                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Personas               | Admin/staff (`AdminContext`) · Driver web (`apps/driver-portal`) · Driver mobile (`apps/mobile-driver`)                                                                                                                        |
| Auth SoT — Admin       | **Staff IdP** — Redis session (`pc_staff_sid` cookie / `Bearer staff_sess_*`). Clerk JWT on `/v1/admin/*` → **401 `admin_clerk_retired_use_staff_idp`**                                                                        |
| Auth SoT — Driver      | **Clerk Bearer only** — no PorterChain cookie JWT minting (`driver_engine/auth_service.py` rationale)                                                                                                                          |
| Authz SoT              | SpiceDB `Check` via `require_module` / tuples — matrix is nav/catalog only                                                                                                                                                     |
| Push SoT               | Firebase **FCM only** — never login/session/RBAC                                                                                                                                                                               |
| Fleetbase              | Adapter + optional `POST /v1/auth/sso/fleetbase` — portals never call `:8000` / SocketCluster                                                                                                                                  |
| Related persona suites | [ADMIN_SUPERADMIN_DEV_TESTCASES.md](ADMIN_SUPERADMIN_DEV_TESTCASES.md) · [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md) · [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md) |
| Policy skips           | [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) — assert _absence_ where tagged `[SKIP-POLICY]`                                                                                                                           |

**How to use**

| Field      | Meaning                                                                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **ID**     | Stable id (`AD-*` admin, `DR-*` driver, `X-*` cross-portal, `HS-*` handshake, `NEG-*` must deny, `DX-*` docker/arch, `MISS-*` easy-to-miss) |
| **P**      | P0 ship-blocker · P1 release · P2 depth · P3 soak/chaos                                                                                     |
| **Kind**   | `unit` · `api` · `contract` · `e2e` · `ui` · `ux` · `handshake` · `security` · `chaos`                                                      |
| **Assert** | Compressed Given / When / Then                                                                                                              |

Prefer **pytest** for API/engine; **Playwright** for portal smoke; **System → Test Center** for live probes; **Maestro** for mobile shells.

---

## 0. Ground truth (from sensors + live census)

### 0.1 Identity topology

```
Admin browser (:3002)
  → Staff IdP login / passkey / magic-link
  → BFF POST /api/auth/staff-session (HttpOnly cookie)
  → BFF /api/porterchain/* → :8001 /v1/admin/*  (cookie → staff_sess Bearer)
  → SpiceDB require_module
  → engines → FleetbaseAdapter / Maps / Stripe / FCM

Driver web (:3003)
  → Clerk driver app session
  → BFF /api/driver/[...path] → :8001 /driver-api/v1/*
  → get_driver_context (Clerk verify → prepare_user → portal_guard → persona_bundle)
  → driver_engine façade → Fleetbase (GPS/jobs SoT) + FCM

Driver mobile (Expo)
  → Clerk Bearer direct to :8001 /driver-api/v1/*
  → same get_driver_context path (do NOT unify with web BFF — intentional)
```

Graphify paths: `get_admin_context` ↔ `FleetbaseClient` (3 hops undirected); `get_driver_context` ↔ `FleetbaseClient` (4 hops). God nodes: `AdminContext` (339), `get_admin_context` (157), `Driver` (188).

CodeGraph blast: `AdminContext` ~85 callers; `ClerkClaims` ~54; `get_driver_context` ~8 router deps (thin surface — every `/driver-api` route must still exercise it).

Ripwire hot symbols: `get_admin_context`, `get_driver_context`, `resolve_notification_ws_user`, `register_push`, `StaffIdp` session/passkey/step-up routes, `SsoService.exchange_fleetbase_session_for_principal`, `assert_portal_email_identity`, `_send_push`.

### 0.2 Coverage census

| Surface                                       | Count / note                                                                                                       |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| OpenAPI ops                                   | 639                                                                                                                |
| Auth-tagged / auth-related ops (loose filter) | ~418 (incl. all `/v1/admin` + `/driver-api`)                                                                       |
| `/v1/auth/*` + staff IdP                      | 17+ staff/passkey/session routes                                                                                   |
| `/driver-api/v1/*`                            | 77 ops · 27 prefixes                                                                                               |
| Admin portal ops pages                        | 20+ routes (see admin suite §0.1)                                                                                  |
| Driver portal pages                           | 18 app routes + 3 BFF auth routes                                                                                  |
| Mobile driver screens                         | SignIn · Onboarding · Jobs · JobDetail · Route · Money · Docs · Inbox · Support · More · Invite · ForceUpdate      |
| Auth package files                            | `apps/api/src/porterchain_api/auth/*` (~50 modules)                                                                |
| Existing API auth suites                      | `test_auth_*`, `test_clerk_registry`, `test_spicedb_authz`, `test_enterprise_identity*`, `test_unified_identity_*` |

### 0.3 Admin pages (auth gate on every route)

| Route                                                                                                     | Auth expectation                           |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `/sign-in`                                                                                                | Public; establishes Staff IdP              |
| `/activate-staff`                                                                                         | Enrollment token → activate → cookie       |
| `/dashboard` … `/settings` · `/account/security` · all `(ops)/*`                                          | Staff cookie required; SpiceDB module gate |
| BFF `/api/auth/staff-session` · `/api/auth/session` · `/api/auth/ws-token` · `/api/porterchain/[...path]` | Cookie mint / probe / WS / proxy           |

Full page UX cases: [ADMIN_SUPERADMIN_DEV_TESTCASES.md](ADMIN_SUPERADMIN_DEV_TESTCASES.md) §2 — this matrix owns the **auth handshake** on each page, not every business assertion.

### 0.4 Driver portal pages + BFF

| Route                                                                                                            | Kind                        |
| ---------------------------------------------------------------------------------------------------------------- | --------------------------- |
| `/login/[[...sign-in]]`                                                                                          | Clerk                       |
| `/onboarding`                                                                                                    | Gated until approved / docs |
| `/dashboard` · `/jobs` · `/jobs/[orderId]` · `/stops` · `/navigation` · `/shift` · `/communications`             | Ops                         |
| `/earnings` · `/wallet` · `/performance`                                                                         | Finance                     |
| `/profile` · `/documents` · `/vehicle` · `/insurance` · `/training` · `/support` · `/emergency`                  | Account / safety            |
| BFF `/api/auth/driver-session` · `/api/auth/driver-dev-session` · `/api/auth/ws-token` · `/api/driver/[...path]` | Proxy                       |

Nav SSOT: `DRIVER_NAV_GROUPS` in `apps/driver-portal/src/lib/driver-nav.ts`.

### 0.5 Key API auth endpoints

| Method   | Path                                                        | Persona                       |
| -------- | ----------------------------------------------------------- | ----------------------------- |
| GET      | `/v1/auth/me`                                               | Multi                         |
| GET      | `/v1/auth/session-context`                                  | Multi                         |
| GET/POST | `/v1/auth/staff/enrollment/{token}` · `.../activate`        | Staff                         |
| POST     | `/v1/auth/staff/login-request` · `/login` · `/logout`       | Staff                         |
| POST     | `/v1/auth/staff/passkey/*` · step-up · sessions revoke      | Staff                         |
| POST     | `/v1/auth/sso/fleetbase`                                    | Staff/driver SSO bridge       |
| POST     | `/webhooks/clerk`                                           | Vendor                        |
| GET/POST | `/driver-api/v1/auth/dev-login` · `/auth/dev-drivers`       | Local only                    |
| GET      | `/driver-api/v1/me` · `/onboarding` · `/push` · `/location` | Driver                        |
| *        | `/driver-api/v1/{jobs,shift,navigation,communications,…}`   | Driver + `get_driver_context` |

### 0.6 Diagnostics probe IDs (auth-adjacent)

`clerk` · `firebase` · `email_smtp` · `mailpit` · `redis` · `postgresql` · `websockets` · `notification_engine` · `fleetbase` · `fleetbase_adapter` · `fleetbase_console` · `osrm` · `valhalla` · `vroom` · `google_maps` · `readiness_probe` · `layered_architecture`

---

## 1. Admin — Staff IdP core

| ID          | P   | Kind     | Assert                                                                                                        |
| ----------- | --- | -------- | ------------------------------------------------------------------------------------------------------------- |
| AD-AUTH-001 | P0  | e2e      | Unauthenticated `/dashboard` → `/sign-in`                                                                     |
| AD-AUTH-002 | P0  | api      | Missing bearer/cookie → `401 missing_bearer_token`                                                            |
| AD-AUTH-003 | P0  | api      | Clerk-looking Bearer on admin → `401 admin_clerk_retired_use_staff_idp`                                       |
| AD-AUTH-004 | P0  | api      | Valid `staff_sess_*` Bearer → `AdminContext` with role + user                                                 |
| AD-AUTH-005 | P0  | api      | Valid `pc_staff_sid` cookie alone (no Authorization) → same context                                           |
| AD-AUTH-006 | P0  | bff      | `POST /api/auth/staff-session` with one-time bearer sets HttpOnly cookie; JS cannot read token                |
| AD-AUTH-007 | P0  | bff      | `GET /api/auth/staff-session` probe `{ authenticated: true\|false }` matches Redis session                    |
| AD-AUTH-008 | P0  | api      | Expired / revoked Redis session → 401; cookie cleared on logout                                               |
| AD-AUTH-009 | P0  | api      | `POST /v1/auth/staff/logout` invalidates Redis key; subsequent admin call fails                               |
| AD-AUTH-010 | P0  | api      | `POST /v1/auth/staff/login-request` + magic link (Mailpit local) creates session                              |
| AD-AUTH-011 | P0  | api      | Passkey register options → verify → login options → login succeeds                                            |
| AD-AUTH-012 | P1  | api      | List / revoke / revoke-other sessions; current session survives self-revoke-others                            |
| AD-AUTH-013 | P1  | api      | Step-up options required before sensitive settings mutations when policy on                                   |
| AD-AUTH-014 | P0  | api      | Enrollment `GET /v1/auth/staff/enrollment/{token}` + activate provisions `AdminUser` without Clerk            |
| AD-AUTH-015 | P0  | api      | Enroll-reissue rotates token; old token fails                                                                 |
| AD-AUTH-016 | P0  | api      | Dev bypass `Bearer dev` only when `APP_ENV=local` + bypass flags; else `dev_bypass_disabled`                  |
| AD-AUTH-017 | P0  | security | `X-Admin-Role` header cannot escalate beyond SpiceDB grants                                                   |
| AD-AUTH-018 | P0  | api      | Role change `PATCH /v1/admin/settings/staff/{id}/role` updates SpiceDB tuples immediately                     |
| AD-AUTH-019 | P0  | api      | Unlinked `porterchain_user_id` → `admin_forbidden:*:unlinked_user`                                            |
| AD-AUTH-020 | P0  | contract | Env names only `CLERK_<PORTAL>_*` via `pnpm clerk:sync` — no `ADMIN_CLERK_*`                                  |
| AD-AUTH-021 | P1  | api      | Staff rate-limit on login-request returns 429 under burst                                                     |
| AD-AUTH-022 | P1  | api      | Cookie Domain / Secure / SameSite bind at process boot — hot-reload `APP_ENV` ignored `[SKIP-POLICY]` product |
| AD-AUTH-023 | P0  | ui       | `/account/security` lists passkeys + sessions; revoke works                                                   |
| AD-AUTH-024 | P1  | ux       | Sign-in error copy distinguishes retired Clerk JWT vs missing session vs suspended staff                      |
| AD-AUTH-025 | P0  | api      | `GET /v1/auth/me` under staff session returns staff persona modules from SpiceDB                              |

---

## 2. Admin — page / subpage auth gates

For each route: unauthenticated redirect · authenticated load · wrong-role 403 · BFF proxy 401 passthrough.

| ID        | P   | Route / surface                                                                    | Assert                                                                                     |
| --------- | --- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| AD-PG-001 | P0  | `/dashboard`                                                                       | Session required; metrics call uses staff cookie via BFF                                   |
| AD-PG-002 | P0  | `/operations`                                                                      | Control Tower APIs deny without `operations` module                                        |
| AD-PG-003 | P0  | `/orders` · `/orders/[id]`                                                         | Detail deep-link with expired cookie → sign-in then return path                            |
| AD-PG-004 | P0  | `/merchants` · `/merchants/[id]`                                                   | Merchant 360; no Shopify key mint from admin                                               |
| AD-PG-005 | P0  | `/drivers` · `/drivers/[id]`                                                       | Driver 360 approve/suspend requires elevated module; action uses `run_admin_driver_action` |
| AD-PG-006 | P1  | `/customers` · `/customers/[id]`                                                   | Retail PII only with module                                                                |
| AD-PG-007 | P1  | `/leads` · pipeline · calendar · `[id]`                                            | CRM module gate                                                                            |
| AD-PG-008 | P1  | `/booking-drafts` · `[id]`                                                         | Recovery write needs auth + audit actor                                                    |
| AD-PG-009 | P2  | `/blog` · `new` · `[id]`                                                           | Marketing role can edit; finance cannot                                                    |
| AD-PG-010 | P0  | `/finance` · `/finance/invoices/[id]`                                              | Finance module; step-up if configured                                                      |
| AD-PG-011 | P0  | `/pricing`                                                                         | Pricing Center; FSA rates mutate super_admin/admin only                                    |
| AD-PG-012 | P1  | `/support` · `/claims` + ids                                                       | Support vs claims modules distinct                                                         |
| AD-PG-013 | P0  | `/notifications`                                                                   | WS token from `/api/auth/ws-token` binds to staff principal                                |
| AD-PG-014 | P0  | `/system` · `/system-health` · `/system-tests`                                     | diagnostics_read / diagnostics_write roles                                                 |
| AD-PG-015 | P0  | `/settings` (all sections)                                                         | `settings` / `settings_*` super_admin+admin; subsections inherit                           |
| AD-PG-016 | P0  | Settings → Users tabs staff/driver/merchant/customer                               | Directory calls Clerk slot for persona; staff enroll IdP                                   |
| AD-PG-017 | P0  | Settings → authentication / security / firebase / fleetbase / google_maps / stripe | Secrets never rendered; probes only                                                        |
| AD-PG-018 | P1  | `/inbox`                                                                           | Staff inbox fan-out uses notification principal, not Clerk admin JWT                       |
| AD-PG-019 | P0  | `/activate-staff`                                                                  | Public token page; success → cookie → dashboard                                            |
| AD-PG-020 | P1  | Aliases `/admin/system-*`                                                          | Same auth as `/system-*`                                                                   |

---

## 3. Driver — Clerk identity core

| ID          | P   | Kind     | Assert                                                                                   |
| ----------- | --- | -------- | ---------------------------------------------------------------------------------------- |
| DR-AUTH-001 | P0  | e2e      | Unauthenticated `/dashboard` → `/login`                                                  |
| DR-AUTH-002 | P0  | api      | No bearer → `401 driver_auth_required`                                                   |
| DR-AUTH-003 | P0  | api      | Invalid Clerk JWT → `401 invalid_driver_token`                                           |
| DR-AUTH-004 | P0  | api      | Valid Clerk driver triad → `DriverContext` for linked `Driver`                           |
| DR-AUTH-005 | P0  | api      | Clerk user without Driver persona → `403 driver_not_found`                               |
| DR-AUTH-006 | P0  | api      | `DriverStatus.SUSPENDED` → `403 driver_suspended`                                        |
| DR-AUTH-007 | P0  | api      | Email mismatch Clerk vs Driver → `403` (`EMAIL_CLERK_MISMATCH` / unverified / required)  |
| DR-AUTH-008 | P0  | api      | `assert_clerk_id_exclusive(..., portal="driver")` blocks merchant/admin clerk ids        |
| DR-AUTH-009 | P0  | api      | `prepare_user_from_claims` + SpiceDB sync runs once per request path                     |
| DR-AUTH-010 | P0  | api      | Self-scope: driver cannot act as another `driver.id` when principal linked               |
| DR-AUTH-011 | P0  | contract | No PorterChain-minted cookie JWT for portal BFF — Clerk only                             |
| DR-AUTH-012 | P0  | api      | Legacy `_driver_id_from_token` (old JWT) not used by portal BFF path                     |
| DR-AUTH-013 | P0  | api      | Dev: `Bearer dev` / `X-Driver-Id` only when bypass allowed + `APP_ENV=local`             |
| DR-AUTH-014 | P0  | api      | `POST /driver-api/v1/auth/dev-login` disabled outside local                              |
| DR-AUTH-015 | P0  | bff      | `/api/driver/[...path]` forwards Clerk Authorization; never Fleetbase URL                |
| DR-AUTH-016 | P1  | bff      | `/api/auth/driver-session` / `driver-dev-session` local-only semantics                   |
| DR-AUTH-017 | P0  | api      | Wrong portal Clerk publishable/secret (admin/merchant) cannot authorize driver routes    |
| DR-AUTH-018 | P1  | api      | Onboarding gate: non-approved driver limited endpoints only                              |
| DR-AUTH-019 | P0  | mobile   | Expo uses `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` + `EXPO_PUBLIC_API_URL` → `:8001` directly |
| DR-AUTH-020 | P0  | arch     | Web BFF vs mobile Bearer remain **two paths** `[SKIP-POLICY]` — do not unify             |
| DR-AUTH-021 | P1  | ux       | Login shows clear “not provisioned / suspended / email mismatch” states                  |
| DR-AUTH-022 | P1  | api      | `GET /driver-api/v1/me` shape matches portal TypeScript types                            |

---

## 4. Driver — page / screen auth + data gates

| ID        | P   | Surface                                               | Assert                                                                           |
| --------- | --- | ----------------------------------------------------- | -------------------------------------------------------------------------------- |
| DR-PG-001 | P0  | `/dashboard`                                          | Loads only with Clerk; KPIs from `/driver-api/v1/dashboard`                      |
| DR-PG-002 | P0  | `/jobs` · `/jobs/[orderId]`                           | Assigned-order only (`require_assigned_order`); other driver’s job → 403/404     |
| DR-PG-003 | P0  | `/stops`                                              | Same assignment boundary                                                         |
| DR-PG-004 | P0  | `/navigation`                                         | Maps tiles/Places OK; ETA/route via Valhalla/OSRM — never Google Distance        |
| DR-PG-005 | P0  | `/shift`                                              | Online/break flips go through driver_engine → Fleetbase SoT                      |
| DR-PG-006 | P0  | `/communications`                                     | Inbox + push register require driver context                                     |
| DR-PG-007 | P1  | `/earnings` · `/wallet` · `/performance`              | Self wallet only; no other driver ledger                                         |
| DR-PG-008 | P1  | `/profile` · `/documents` · `/vehicle` · `/insurance` | Upload auth’d; verification flags env-gated                                      |
| DR-PG-009 | P1  | `/training`                                           | Compliance modules gated                                                         |
| DR-PG-010 | P1  | `/support` · `/emergency`                             | Ticket/SOS create stamped with driver principal                                  |
| DR-PG-011 | P0  | `/onboarding`                                         | Incomplete onboarding cannot open jobs                                           |
| DR-PG-012 | P0  | Mobile `SignInScreen`                                 | SessionGate blocks tabs until Clerk session                                      |
| DR-PG-013 | P1  | Mobile `deviceUnlock`                                 | Biometric unlock does not replace Clerk; only unlocks local vault                |
| DR-PG-014 | P1  | Mobile offline queue                                  | Replays only with valid session; 401 clears queue safely                         |
| DR-PG-015 | P0  | Mobile handshake                                      | `handshake.ts` probes `:8001` not `:8000`                                        |
| DR-PG-016 | P0  | CI mobile                                             | No `fleetbase` HTTP, no SocketCluster, no `:8000` under `apps/mobile-driver/src` |

---

## 5. Cross-portal isolation & unified identity

| ID    | P   | Kind     | Assert                                                                                  |
| ----- | --- | -------- | --------------------------------------------------------------------------------------- |
| X-001 | P0  | security | Driver Clerk token → `/v1/admin/*` denied                                               |
| X-002 | P0  | security | Staff session → `/driver-api/v1/*` denied (unless explicit admin-as-driver tooling off) |
| X-003 | P0  | security | Merchant Clerk → admin + driver denied                                                  |
| X-004 | P0  | security | Customer Clerk → driver/admin denied                                                    |
| X-005 | P0  | api      | Same email cannot bind two exclusive portals when `portal_guard` enforces exclusivity   |
| X-006 | P0  | api      | `UserSyncService.sync` upserts `IdentityLink` once per clerk_user_id                    |
| X-007 | P0  | api      | `persona_bundle` returns correct admin/driver/merchant/customer slices                  |
| X-008 | P1  | api      | Clerk webhook user.updated rebinds email; mismatch blocks portal until fixed            |
| X-009 | P1  | api      | Clerk webhook idempotency — duplicate delivery no double provision                      |
| X-010 | P0  | api      | `POST /webhooks/clerk` signature verify; bad sig → 401/403                              |
| X-011 | P1  | db       | `prune_users_to_clerk` removes orphan bindings without deleting Fleetbase driver        |
| X-012 | P0  | contract | Firebase Auth never used for any portal `[SKIP-POLICY]`                                 |

---

## 6. Fleetbase handshake (auth-adjacent)

| ID        | P   | Kind      | Assert                                                                                                     |
| --------- | --- | --------- | ---------------------------------------------------------------------------------------------------------- |
| HS-FB-001 | P0  | arch      | All Fleetbase HTTP only via `services/fleetbase-adapter`                                                   |
| HS-FB-002 | P0  | api       | `POST /v1/auth/sso/fleetbase` exchanges session via `SsoService` + `FleetbaseSsoClient.exchange_sso_token` |
| HS-FB-003 | P0  | api       | SSO upserts identity link (`upsert_sso_link`) with provider/issuer                                         |
| HS-FB-004 | P1  | api       | SSO disabled / bridge down → clear error; console probe may skip healthy                                   |
| HS-FB-005 | P0  | api       | Driver approve/link provisions Fleetbase driver id through adapter — not browser                           |
| HS-FB-006 | P0  | api       | Admin operations sync retry uses staff context; never embeds Clerk driver JWT                              |
| HS-FB-007 | P0  | security  | Web apps never import SocketCluster SDK                                                                    |
| HS-FB-008 | P0  | security  | Admin may deep-link console URL (`system-links`) but never proxy Fleetbase cookies to browser API calls    |
| HS-FB-009 | P1  | handshake | `fleetbase_roles.py` mapping staff role → Fleetbase permissions deterministic                              |
| HS-FB-010 | P0  | arch      | No PorterChain-native VROOM client; VROOM stays in Fleetbase orchestrator `[SKIP-POLICY]`                  |
| HS-FB-011 | P1  | api       | Booking sync / ops mirror refresh authenticated as service identity, not end-user JWT                      |
| HS-FB-012 | P2  | chaos     | Adapter timeout/circuit does not leak upstream tokens in error bodies                                      |

---

## 7. Firebase / push / notification auth

| ID         | P   | Kind     | Assert                                                                             |
| ---------- | --- | -------- | ---------------------------------------------------------------------------------- |
| HS-FCM-001 | P0  | api      | Driver `POST` push register requires `get_driver_context`                          |
| HS-FCM-002 | P0  | api      | Admin browser `registerBrowserPush` requires staff session                         |
| HS-FCM-003 | P0  | api      | `get_notification_user` / `resolve_notification_ws_user` reject foreign tokens     |
| HS-FCM-004 | P0  | bff      | `/api/auth/ws-token` (admin + driver) short-lived; cannot call mutating admin APIs |
| HS-FCM-005 | P0  | contract | FCM credentials on API **and** worker; send path uses `notification_engine`        |
| HS-FCM-006 | P1  | api      | Zero device tokens → email fallback for staff risk events                          |
| HS-FCM-007 | P0  | security | Firebase project keys never authorize `/v1/admin` or `/driver-api`                 |
| HS-FCM-008 | P1  | ui       | Admin Operations PushHealthStrip reflects probe without exposing secrets           |
| HS-FCM-009 | P1  | skip     | No Fleetbase `NotifyOrderEvent` / SC for PC portal push `[SKIP-POLICY]`            |
| HS-FCM-010 | P2  | api      | Unregister / token rotate on logout                                                |

---

## 8. Email / Mailpit / invitations

| ID          | P   | Kind      | Assert                                                                       |
| ----------- | --- | --------- | ---------------------------------------------------------------------------- |
| HS-MAIL-001 | P0  | handshake | Local staff magic-link lands in Mailpit; link activates once                 |
| HS-MAIL-002 | P0  | api       | Staff enrollment email via `staff_mail`                                      |
| HS-MAIL-003 | P1  | api       | Driver/merchant invitations use correct Clerk app slot from `clerk_registry` |
| HS-MAIL-004 | P0  | dx        | SMTP probe + mailpit probe in diagnostics                                    |
| HS-MAIL-005 | P1  | security  | Invitation tokens single-use; brute-force rate-limited                       |

---

## 9. Clerk registry & multi-app triad

| ID         | P   | Kind      | Assert                                                                        |
| ---------- | --- | --------- | ----------------------------------------------------------------------------- |
| HS-CLK-001 | P0  | unit      | `clerk_app_configs()` returns admin/merchant/driver/customer slots            |
| HS-CLK-002 | P0  | unit      | `clerk_client_for_kind("driver")` uses driver secret — not admin              |
| HS-CLK-003 | P0  | handshake | JWKS URL reachable; clerk diagnostic green                                    |
| HS-CLK-004 | P0  | api       | Directory service list/invite per `user_type`                                 |
| HS-CLK-005 | P1  | api       | `clerk_configuration_mode` / `is_clerk_secret_configured` fail-closed in prod |
| HS-CLK-006 | P1  | audit     | `clerk_config_audit` detects mixed test/live keys                             |
| HS-CLK-007 | P0  | dx        | `pnpm clerk:sync` from `env/clerk.env` is SSOT                                |

---

## 10. SpiceDB / RBAC / modules

| ID        | P   | Kind | Assert                                                                                 |
| --------- | --- | ---- | -------------------------------------------------------------------------------------- |
| HS-AZ-001 | P0  | api  | `require_module("finance")` fails for dispatcher even if URL guessed                   |
| HS-AZ-002 | P0  | api  | Super-admin `SYSTEM_ALL` + `platform.admin` — not every merchant portal module blindly |
| HS-AZ-003 | P0  | api  | Role revoke blocks `require_module` immediately (no allow-cache)                       |
| HS-AZ-004 | P0  | unit | `MODULE_PERMISSIONS` is catalog only — SpiceDB is SoT                                  |
| HS-AZ-005 | P1  | api  | Driver self-scope via `assert_self_scope`                                              |
| HS-AZ-006 | P1  | api  | Authz sync on prepare_user writes expected tuples                                      |

---

## 11. Spatial / maps auth boundaries (not identity, but abuse surface)

| ID         | P   | Kind | Assert                                                          |
| ---------- | --- | ---- | --------------------------------------------------------------- |
| HS-MAP-001 | P0  | api  | Driver navigation session requires driver auth                  |
| HS-MAP-002 | P0  | arch | Distance/ETA/matrix never Google; Valhalla→OSRM only            |
| HS-MAP-003 | P0  | arch | Public OSRM demo last-resort gated off by default               |
| HS-MAP-004 | P1  | api  | Admin live map / suggestions require ops module + staff session |
| HS-MAP-005 | P0  | arch | No haversine in ops assignment scoring path                     |
| HS-MAP-006 | P0  | skip | No PC VROOM client `[SKIP-POLICY]`                              |

---

## 12. Stripe / Shopify / ERP / OAuth / partner keys (auth edges)

| ID           | P   | Kind     | Assert                                                                             |
| ------------ | --- | -------- | ---------------------------------------------------------------------------------- |
| HS-PAY-001   | P0  | webhook  | Stripe webhook signature; no session cookie required                               |
| HS-PAY-002   | P1  | api      | Driver payouts admin-initiated; driver cannot mint Connect account for others      |
| HS-SHOP-001  | P0  | arch     | Admin does **not** mint Shopify keys — merchant creates; admin revoke/disable only |
| HS-SHOP-002  | P0  | security | Shopify OAuth tokens never accepted as admin/driver session                        |
| HS-ERP-001   | P1  | api      | Partner `/v1/merchant-api` API key + idempotency — isolated from staff/driver      |
| HS-OAUTH-001 | P1  | api      | `/v1/oauth/authorize` merchant-scoped; cannot obtain staff_sess                    |
| HS-INT-001   | P2  | contract | Future ERP webhooks follow signature + principal = system, not end-user            |

---

## 13. Models / database

| ID     | P   | Kind      | Assert                                                                 |
| ------ | --- | --------- | ---------------------------------------------------------------------- |
| DB-001 | P0  | unit      | `AdminUser` provisioned by Staff IdP without requiring `clerk_user_id` |
| DB-002 | P0  | unit      | `Driver.clerk_user_id` + email identity constraints                    |
| DB-003 | P0  | unit      | `IdentityLink` unique per provider subject                             |
| DB-004 | P0  | unit      | Staff sessions live in Redis — not Postgres opaque JWT table as SoT    |
| DB-005 | P1  | migration | Alembic adds (e.g. admin phone) do not break session bind              |
| DB-006 | P1  | unit      | Suspended driver status blocks context before Fleetbase calls          |
| DB-007 | P1  | unit      | Soft-deleted / pruned clerk bindings fail closed                       |

---

## 14. Docker / worker / architecture / CI

| ID     | P   | Kind  | Assert                                                                                               |
| ------ | --- | ----- | ---------------------------------------------------------------------------------------------------- |
| DX-001 | P0  | dx    | Compose pins exact image tags — never `:latest`                                                      |
| DX-002 | P0  | dx    | API `:8001`, admin `:3002`, driver-portal `:3003`, Fleetbase `:8000`, Valhalla `:8002`, OSRM `:5000` |
| DX-003 | P0  | dx    | Redis 8.8 holds staff sessions; restart flushes sessions (document expected UX)                      |
| DX-004 | P0  | dx    | Worker has FCM + Clerk webhook consumers env; cannot use browser cookies                             |
| DX-005 | P0  | ci    | `scripts/openapi_census.py` — new untagged auth paths fail                                           |
| DX-006 | P0  | ci    | `scripts/verify_vendor_leaves.py` — no SC / Fleetbase in web/mobile                                  |
| DX-007 | P0  | ci    | Mobile CI forbids `:8000` / fleetbase HTTP                                                           |
| DX-008 | P1  | dx    | Mailpit not Mailhog                                                                                  |
| DX-009 | P1  | dx    | Fleetbase cache Valkey 8 override                                                                    |
| DX-010 | P0  | arch  | Routers stay thin — auth logic in `auth/*` + engines                                                 |
| DX-011 | P1  | chaos | Kill Redis → admin sessions fail closed (no Clerk fallback)                                          |
| DX-012 | P1  | chaos | Kill Clerk JWKS → driver auth fails; admin Staff IdP still works                                     |
| DX-013 | P2  | chaos | Split-brain clock skew JWT `nbf`/`exp` handling                                                      |

---

## 15. UI / UX quality (auth surfaces)

| ID     | P   | Assert                                                                          |
| ------ | --- | ------------------------------------------------------------------------------- |
| UX-001 | P1  | Admin sign-in: passkey vs magic-link choice clear; no “Clerk” jargon for staff  |
| UX-002 | P1  | Driver login: Clerk components; brand-consistent; mobile + web parity messaging |
| UX-003 | P1  | Session expiry mid-form → non-destructive re-auth (preserve draft where safe)   |
| UX-004 | P1  | 403 module pages show “request access” not blank shell                          |
| UX-005 | P2  | Step-up modal focus trap + cancel restores prior view                           |
| UX-006 | P2  | Logout clears FCM registration + WS + query cache                               |

---

## 16. Things easy to miss (you asked — added)

| ID       | P   | Assert                                                                                             |
| -------- | --- | -------------------------------------------------------------------------------------------------- |
| MISS-001 | P0  | Admin Clerk JWT retirement is permanent — regression test for `admin_clerk_retired_use_staff_idp`  |
| MISS-002 | P0  | Cookie name `pc_staff_sid` vs Bearer prefix `staff_sess_` both paths covered                       |
| MISS-003 | P1  | WebAuthn origin / RP ID match admin host only                                                      |
| MISS-004 | P1  | Staff phone SMS is secondary — push→email failsafe `[SKIP-POLICY]` primary SMS                     |
| MISS-005 | P1  | Notification WS user resolution amp high (Ripwire) — fuzz tokens                                   |
| MISS-006 | P1  | `DriverAuthService` impact reaches booking loop — auth link clerk does not break retail checkout   |
| MISS-007 | P0  | Google Places key restricted; never used as bearer                                                 |
| MISS-008 | P1  | Diagnostics AI / copilot tools never auto-write Fleetbase/Valhalla/Stripe                          |
| MISS-009 | P1  | Checkr / Stripe Identity webhooks are verification — not session mint `[SKIP-POLICY]` live vendors |
| MISS-010 | P1  | Referral / wallet credits never trust client `driver_id` without context                           |
| MISS-011 | P2  | Multi-tab admin: logout in tab A kills tab B within probe interval                                 |
| MISS-012 | P2  | Safari ITP / third-party cookie: staff cookie first-party on admin origin                          |
| MISS-013 | P1  | `CLERK_DEV_BYPASS` dual-gated with project mode — blocked in staging/prod                          |
| MISS-014 | P1  | Impersonation (if any) audited + time-boxed — default deny                                         |
| MISS-015 | P2  | Clock-skew between API and Redis session TTL                                                       |
| MISS-016 | P1  | OpenAPI security schemes document staff vs clerk vs api_key correctly                              |
| MISS-017 | P1  | Event bus consumer identity ≠ end-user; poisoned JWT in payload ignored                            |
| MISS-018 | P2  | GraphQL/SC leftover routes absent from OpenAPI census                                              |
| MISS-019 | P1  | Admin BFF strips hop-by-hop headers; no SSRF via `/api/porterchain`                                |
| MISS-020 | P1  | Driver location POST authenticated + rate-limited; cannot spoof another driver                     |
| MISS-021 | P2  | Passkey sync across devices; lost passkey recovery via magic-link                                  |
| MISS-022 | P1  | Enrollment email deep-link HTTPS only in non-local                                                 |
| MISS-023 | P1  | SpiceDB unavailable → fail closed (no matrix fallback allow)                                       |
| MISS-024 | P2  | Corpus of `test_unified_identity_phase*` still green after IdP cutover                             |
| MISS-025 | P1  | Shopify rate quote / ERP ingest uses merchant API key — never staff cookie                         |

---

## 17. Suggested automation map

| Layer           | Where                                                                              | Cases                                         |
| --------------- | ---------------------------------------------------------------------------------- | --------------------------------------------- |
| unit            | `apps/api/tests/test_auth_*.py`, `test_clerk_registry.py`, `test_spicedb_authz.py` | AD-AUTH-_, DR-AUTH-_, HS-CLK-_, HS-AZ-_, DB-* |
| unit            | `test_unified_identity_*.py`, `test_enterprise_identity.py`                        | X-*, MISS-024                                 |
| api/integration | pytest + httpx against `:8001`                                                     | HS-FB-_, HS-FCM-_, HS-MAIL-*, page API gates  |
| portal e2e      | Playwright admin + driver-portal                                                   | AD-PG-_, DR-PG-001–011, UX-_                  |
| mobile          | Maestro `apps/mobile-driver/maestro`                                               | DR-PG-012–016, DR-AUTH-019                    |
| probes          | Admin System Test Center                                                           | §0.6 IDs                                      |
| ci gates        | openapi_census · verify_vendor_leaves · mobile path bans                           | DX-005–007                                    |
| chaos           | local compose kill Redis/Clerk/Fleetbase                                           | DX-011–013, HS-FB-012                         |

---

## 18. Exit criteria (dev layer)

1. **P0** rows green on localhost + CI.
2. Admin: Staff IdP only — Clerk JWT regression suite red-flag protected.
3. Driver: Clerk Bearer + email identity + portal exclusivity green on web BFF **and** mobile direct.
4. No portal/mobile path to Fleetbase HTTP / SocketCluster / Firebase Auth.
5. FCM register/WS token bound to correct principal; worker can send.
6. SSO Fleetbase exchange works when bridge enabled; fails closed when not.
7. Intentional skips asserted as **absence** (unify BFF, PC VROOM, Firebase Auth, admin Shopify mint, etc.).
8. Persona suites remain complementary — this file owns auth; admin/merchant/customer docs own business pages.

---

## 19. File / package checklist (touch list for reviewers)

**API auth:** `auth/admin.py` · `auth/driver.py` · `auth/staff_session.py` · `auth/staff_webauthn.py` · `auth/staff_step_up.py` · `auth/clerk_registry.py` · `auth/portal_guard.py` · `auth/email_identity.py` · `auth/persona_bundle.py` · `auth/sso_service.py` · `auth/clerk_webhook_*.py` · `routers/auth.py` · `routers/driver/*` · `admin_engine/staff_idp_service.py` · `driver_engine/auth_service.py` · `notification_engine/principal.py`

**Admin UI:** `AdminAuthProvider` · `AdminAccessGate` · `staff-session.ts` · `staff-step-up.ts` · `staff-webauthn.ts` · `middleware.ts` · `api/auth/*` · `api/porterchain/[...path]` · `web-push.ts` · `firebase-*.ts`

**Driver UI:** `login/[[...sign-in]]` · `api/driver/[...path]` · `api/auth/driver-*` · `offline-client.ts` · `firebase-*.ts`

**Mobile:** `SessionGate` · `session.ts` · `handshake.ts` · `push.ts` · `auth/*`

**Adapter:** `porterchain_fleetbase_adapter/auth` · `FleetbaseSsoClient` · `FleetbaseClient`

**Shared:** `porterchain_shared/auth/session.py` (legacy envelope — confirm unused by admin/driver portal paths)

---

_Generated from live Graphify graph, CodeGraph symbol extract, Ripwire adapter lens, OpenAPI census, and `ARCHITECTURE.md` identity branch (2026-09-17)._
