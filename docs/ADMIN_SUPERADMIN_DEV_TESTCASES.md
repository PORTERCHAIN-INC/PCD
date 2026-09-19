# Admin + Super Admin — development test cases

**Entry SSOT:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).

**SSOT for local/CI development tests** covering the admin portal (`apps/admin`), admin FastAPI surface (`/v1/admin/*`), and every handshake those personas touch.

| Meta         | Value                                                                                                                                                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Personas     | `super_admin`, `admin` (also matrix-check other `AdminRole`s)                                                                                                                                                                  |
| Sensors used | Graphify → CodeGraph → Ripwire (2026-09-17)                                                                                                                                                                                    |
| Auth SoT     | SpiceDB `require_module` — `MODULE_PERMISSIONS` is **nav/catalog only**                                                                                                                                                        |
| Out of scope | Items in [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) marked **skip / not a bug**                                                                                                                                      |
| Related      | Auth SSOT: [AUTHENTICATION_DRIVER_ADMIN_DEV_TEST_MATRIX.md](AUTHENTICATION_DRIVER_ADMIN_DEV_TEST_MATRIX.md) · `apps/api/src/porterchain_api/admin_engine/rbac.py`, `apps/admin/src/lib/admin-nav.ts`, `diagnostics_catalog.py` |

**How to use**

1. Prefer **pytest** for API/engine; **Playwright/Vitest** for portal smoke; **System → Test Center** for live probes.
2. Every case: **Given / When / Then** + expected HTTP + side effect.
3. Tag: `[SA]` = Super Admin only · `[AD]` = Admin (non-super) · `[BOTH]` · `[NEG]` = must deny · `[SKIP-POLICY]` = intentional skip (assert _absence_).

---

## 0. Inventory (ground truth)

### 0.1 Admin portal routes (pages)

| Route                                                                                                   | Kind             |
| ------------------------------------------------------------------------------------------------------- | ---------------- |
| `/sign-in`                                                                                              | Auth             |
| `/activate-staff`                                                                                       | Staff enrollment |
| `/dashboard`                                                                                            | Ops              |
| `/operations`                                                                                           | Control Tower    |
| `/orders`, `/orders/[id]`                                                                               | Orders           |
| `/merchants`, `/merchants/[id]`                                                                         | Merchant 360     |
| `/drivers`, `/drivers/[id]`                                                                             | Driver 360       |
| `/customers`, `/customers/[id]`                                                                         | Retail customers |
| `/leads`, `/leads/[id]`, `/leads/pipeline`, `/leads/calendar`                                           | CRM              |
| `/booking-drafts`, `/booking-drafts/[id]`                                                               | Recovery         |
| `/blog`, `/blog/new`, `/blog/[id]`                                                                      | Content          |
| `/finance`, `/finance/invoices/[id]`                                                                    | Billing          |
| `/pricing`                                                                                              | Pricing Center   |
| `/support`, `/support/[id]`                                                                             | Tickets          |
| `/claims`, `/claims/[id]`                                                                               | Claims           |
| `/notifications`                                                                                        | Notification ops |
| `/system`, `/system-health`, `/system-tests` (+ `/admin/system-*` aliases)                              | Diagnostics      |
| `/settings`                                                                                             | Settings Center  |
| `/account/security`                                                                                     | Staff security   |
| `/inbox`                                                                                                | Staff inbox      |
| BFF: `/api/porterchain/[...path]`, `/api/auth/session`, `/api/auth/staff-session`, `/api/auth/ws-token` | Proxy / auth     |

Nav SSOT: `ADMIN_NAV_GROUPS` / `ADMIN_TOP_LEVEL_ROUTES` in `admin-nav.ts`.

### 0.2 Settings sections

Groups: `overview` · `general` · `access` · `commercial` · `partners` · `connections` · `platform`

Sections: `dashboard`, `general`, `users`, `roles`, `authentication`, `security`, `vehicles`, `pricing`, `coverage`, `booking`, `finance`, `documents`, `claims`, `merchant`, `driver`, `customer`, `fleetbase`, `google_maps`, `stripe`, `firebase`, `storage`, `channels`, `lead_ingest`, `automation`, `audit`, `backup`

User directory tabs: `staff` · `driver` · `merchant` · `customer`

### 0.3 Diagnostics probe / test catalog IDs

`clerk`, `stripe`, `firebase`, `google_maps`, `osrm`, `valhalla`, `vroom`, `fleetbase`, `fleetbase_adapter`, `fleetbase_console`, `email_smtp`, `mailpit`, `event_bus`, `websockets`, `redis`, `postgresql`, `readiness_probe`, `metrics_endpoint`, `worker_queue`, `notification_engine`, `pricing_engine`, `billing_engine`, `orders_engine`, `crm_engine`, `finance_engine`, `claims_engine`, `support_engine`, `layered_architecture`, `stripe_webhook`, `scheduled_jobs`

### 0.4 Roles (`AdminRole`)

`super_admin`, `admin`, `dispatcher`, `support`, `support_lead`, `sales`, `sales_manager`, `finance`, `compliance`, `developer`, `marketing`, `read_only`, `fleet_manager`

`settings` / `settings_*` / most destructive diagnostics writes: **super_admin + admin only**.  
`diagnostics_write`: **super_admin + admin**.  
`developers` / `diagnostics` read: also `developer`.

---

## 1. Identity, session, RBAC handshakes

| ID       | Persona     | Layer | Case                                                                                   |
| -------- | ----------- | ----- | -------------------------------------------------------------------------------------- |
| AUTH-001 | BOTH        | UI    | Unauthenticated visit to `/dashboard` redirects to `/sign-in`                          |
| AUTH-002 | BOTH        | UI    | Clerk admin app JWKS validates; wrong portal key rejected                              |
| AUTH-003 | BOTH        | API   | `GET /v1/auth/me` (or session) returns role + `modules` from `modules_for_permissions` |
| AUTH-004 | SA          | API   | `SYSTEM_ALL` → all admin+merchant module keys present                                  |
| AUTH-005 | AD          | API   | `admin` role modules match SpiceDB grants; no silent matrix fallback                   |
| AUTH-006 | NEG         | API   | Unlinked `porterchain_user_id` → `admin_forbidden:*:unlinked_user`                     |
| AUTH-007 | BOTH        | BFF   | `/api/porterchain/*` forwards Bearer; strips host header; never exposes secrets        |
| AUTH-008 | BOTH        | BFF   | `/api/auth/ws-token` issues short-lived WS token for notification realtime             |
| AUTH-009 | BOTH        | BFF   | Staff cookie probe (`probeStaffCookie`) aligns with IdP session                        |
| AUTH-010 | SA          | UI    | Activate-staff enrollment + reissue enrollment works                                   |
| AUTH-011 | AD          | UI    | Non-admin cannot open Settings → Users enroll                                          |
| AUTH-012 | BOTH        | API   | Dev bypass (`CLERK_DEV_BYPASS` / Bearer `dev`) only when `APP_ENV=local`               |
| AUTH-013 | SKIP-POLICY | API   | `POST /settings/project-mode` always `403 project_mode_immutable`                      |
| AUTH-014 | BOTH        | DB    | `AdminUser.clerk_user_id` binds; prune mismatched bindings (`prune_users_to_clerk`)    |
| AUTH-015 | NEG         | API   | Merchant/driver Clerk apps cannot authorize admin routes                               |
| AUTH-016 | BOTH        | UI    | Account → Security: step-up / passkey / magic-link paths per env                       |
| AUTH-017 | SA          | API   | Role change via `PATCH /settings/staff/{id}/role` updates SpiceDB tuples               |
| AUTH-018 | BOTH        | API   | `require_module("finance")` fails for `dispatcher` even if UI link guessed             |
| AUTH-019 | BOTH        | Arch  | No `ADMIN_CLERK_*` env names — only `CLERK_ADMIN_*` triad via `pnpm clerk:sync`        |
| AUTH-020 | BOTH        | API   | Hybrid RBAC tests: Super-admin = `SYSTEM_ALL` + `platform.admin` — not every portal    |

**Role × page matrix smoke (RBAC-PAGE-***)**

For each `ADMIN_TOP_LEVEL_ROUTES` item and each role: assert nav visibility ↔ module key ↔ SpiceDB Check. Critical denials:

| Page                              | Deny roles (examples)             |
| --------------------------------- | --------------------------------- |
| `/settings`                       | all except `super_admin`, `admin` |
| `/system` write / chaos / reports | non-`diagnostics_write`           |
| `/finance` mutate                 | non-finance grant                 |
| `/leads` write                    | non-crm                           |
| `/blog` write                     | non-content                       |

---

## 2. Page / subpage UI–UX cases

### 2.1 Dashboard — `/dashboard`

| ID          | Case                                                                     |
| ----------- | ------------------------------------------------------------------------ |
| UI-DASH-001 | Loads KPIs; `trends: { labels, orders, revenue_cents }` shape matches TS |
| UI-DASH-002 | Empty DB: zero-state, not crash                                          |
| UI-DASH-003 | Search hits merchants/orders/drivers                                     |
| UI-DASH-004 | Alert strip reflects notification unread                                 |

### 2.2 Control Tower — `/operations`

| ID         | Case                                                                                    |
| ---------- | --------------------------------------------------------------------------------------- |
| UI-OPS-001 | Board columns load; drag/move calls `POST …/board/move`                                 |
| UI-OPS-002 | Assignable drivers + suggestions (Valhalla/OSRM via engine — no Google distance)        |
| UI-OPS-003 | Live map tiles = Google Maps JS; positions via adapter poll (no SocketCluster in web)   |
| UI-OPS-004 | Route geometry / playback endpoints return polyline                                     |
| UI-OPS-005 | Exceptions: ack / resolve / retry                                                       |
| UI-OPS-006 | Optimize panel: engines list includes Fleetbase/VROOM path only (no PC VROOM client)    |
| UI-OPS-007 | Optimize run → commit happy path + failure toast                                        |
| UI-OPS-008 | Copilot: llm / accept / modify / dismiss; propose→confirm only (`auto_apply` forbidden) |
| UI-OPS-009 | SLA / utilization / activity / sync health panels                                       |
| UI-OPS-010 | Push health strip reflects FCM/device health                                            |
| UI-OPS-011 | Manifests + scheduled batches list/detail                                               |
| UI-OPS-012 | Queue depths + sync requeue                                                             |

### 2.3 Orders — `/orders`, `/orders/[id]`

| ID         | Case                                                               |
| ---------- | ------------------------------------------------------------------ |
| UI-ORD-001 | List filters, facets, pagination                                   |
| UI-ORD-002 | Create single + bulk                                               |
| UI-ORD-003 | Order 360: tracking, timeline, parcels patch                       |
| UI-ORD-004 | Documents: label/manifest/invoice PDF, POD zip, compliance dossier |
| UI-ORD-005 | Assist propose→decide                                              |
| UI-ORD-006 | Playbooks execute                                                  |
| UI-ORD-007 | Temperature / audit-export                                         |
| UI-ORD-008 | Resend receipt; invoice regenerate                                 |
| UI-ORD-009 | Bulk labels                                                        |

### 2.4 Merchants — `/merchants`, `/merchants/[id]`

| ID         | Case                                                             |
| ---------- | ---------------------------------------------------------------- |
| UI-MER-001 | Facets/stats; unprovisioned signups                              |
| UI-MER-002 | Approve / suspend / unsuspend / reopen / close                   |
| UI-MER-003 | **Never** hard DELETE merchant ([SKIP-POLICY] assert 405/404)    |
| UI-MER-004 | Convert-to-customer                                              |
| UI-MER-005 | Privacy preview + execute                                        |
| UI-MER-006 | Pricing GET/PUT + GTA matrix fields                              |
| UI-MER-007 | Locations / addresses / recipients CRUD                          |
| UI-MER-008 | Billing contacts CRUD                                            |
| UI-MER-009 | Team seats / owner-seat / activate-users / complete-onboarding   |
| UI-MER-010 | API keys rate-limit; webhook delivery retry                      |
| UI-MER-011 | Standing orders deactivate                                       |
| UI-MER-012 | AR preview/generate; statement; credit notes                     |
| UI-MER-013 | Contracts / contacts / activities / tasks / analytics / timeline |
| UI-MER-014 | Shopify connection status on merchant (if linked)                |
| UI-MER-015 | Subsidiaries tree                                                |

### 2.5 Drivers — `/drivers`, `/drivers/[id]`

| ID         | Case                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------ |
| UI-DRV-001 | Facets/stats list                                                                          |
| UI-DRV-002 | Invite / approve / suspend / deactivate / reject / rehire                                  |
| UI-DRV-003 | Verification badges (Identity / Checkr / abstract / expiry) — human approve still required |
| UI-DRV-004 | Vehicles add/deactivate                                                                    |
| UI-DRV-005 | Documents upload list                                                                      |
| UI-DRV-006 | Payouts create + mark-paid                                                                 |
| UI-DRV-007 | Incidents / analytics / timeline / activities / tasks                                      |
| UI-DRV-008 | Orders history for driver                                                                  |
| UI-DRV-009 | [SKIP-POLICY] No auto-approve `DriverStatus` from webhooks                                 |

### 2.6 Customers — `/customers`, `/customers/[id]`

| ID         | Case                                     |
| ---------- | ---------------------------------------- |
| UI-CUS-001 | Stats + detail                           |
| UI-CUS-002 | Orders / invoices / payments / care tabs |
| UI-CUS-003 | Create booking draft + send payment link |

### 2.7 Growth — leads / pipeline / calendar / drafts / blog

| ID           | Case                                                             |
| ------------ | ---------------------------------------------------------------- |
| UI-LEAD-001  | Merchant leads inbox vs `?source=website_driver_partner`         |
| UI-LEAD-002  | Pipeline stages; metrics                                         |
| UI-LEAD-003  | Calendar events from guides                                      |
| UI-LEAD-004  | Lead detail: merge, identities, conversations, convert, delete   |
| UI-LEAD-005  | Assist decide                                                    |
| UI-LEAD-006  | Referral create + referral-credits list                          |
| UI-LEAD-007  | Visitor intelligence on lead                                     |
| UI-DRAFT-001 | Abandoned list/analytics; extend/cancel/restore/expire/duplicate |
| UI-DRAFT-002 | Send payment link; bulk actions                                  |
| UI-BLOG-001  | List/create/edit/delete EN+FR; media upload                      |

### 2.8 Finance & Pricing

| ID         | Case                                                       |
| ---------- | ---------------------------------------------------------- |
| UI-FIN-001 | Dashboard / collections / ledger / duplicates              |
| UI-FIN-002 | Invoice detail: record payment, remind, PDF                |
| UI-FIN-003 | Credit notes                                               |
| UI-FIN-004 | Merchant AR preview/generate                               |
| UI-FIN-005 | COD board (Connect) — does not break Checkout prepaid path |
| UI-FIN-006 | Export / reports / summary / payouts                       |
| UI-PRC-001 | Pricing Center: catalog, merchant deals, simulate quote    |
| UI-PRC-002 | Simulate uses Valhalla/OSRM distance — never Google Matrix |

### 2.9 Support & Claims

| ID         | Case                                                                      |
| ---------- | ------------------------------------------------------------------------- |
| UI-SUP-001 | Ticket CRUD, assign, auto-assign, notes, SLA pause/resume, bulk           |
| UI-SUP-002 | Knowledge base / macros / automation / SLA settings                       |
| UI-CLM-001 | Claim lifecycle: status, evidence, investigation, compensation, insurance |
| UI-CLM-002 | Max compensation cap from settings; investigation SLA due-at              |

### 2.10 Notifications — `/notifications`

| ID         | Case                                 |
| ---------- | ------------------------------------ |
| UI-NTF-001 | Dashboard / queue / history / failed |
| UI-NTF-002 | Templates list                       |
| UI-NTF-003 | Devices + push-health                |
| UI-NTF-004 | Retry failed; broadcast; send-test   |
| UI-NTF-005 | Delivery logs; entity-alerts         |
| UI-NTF-006 | Realtime bell via WS token           |

### 2.11 System / diagnostics

| ID         | Case                                                                |
| ---------- | ------------------------------------------------------------------- |
| UI-SYS-001 | System Center health categories match `HEALTH_CATEGORIES`           |
| UI-SYS-002 | Run each `TEST_IDS` probe; assert status enum                       |
| UI-SYS-003 | Architecture / modules / workflows views                            |
| UI-SYS-004 | Fleetbase sync + merchant webhook delivery                          |
| UI-SYS-005 | AI usage view                                                       |
| UI-SYS-006 | Chaos scenario (SA/admin only); denied for developer                |
| UI-SYS-007 | Observability + report generate                                     |
| UI-SYS-008 | Layered architecture test fails if UI calls Fleetbase HTTP directly |

### 2.12 Settings Center — `/settings` (super-admin heavy)

| ID         | Case                                                                    |
| ---------- | ----------------------------------------------------------------------- |
| UI-SET-001 | All groups/sections render; aliases redirect (`email`→`channels`, etc.) |
| UI-SET-002 | Dashboard readiness + integration meta                                  |
| UI-SET-003 | Users DirectoryShell: staff/driver/merchant/customer tabs               |
| UI-SET-004 | Enroll staff / reissue / change role modals                             |
| UI-SET-005 | Create/manage driver modals; add merchant seat                          |
| UI-SET-006 | Roles panel read-only matrix matches `permissions_catalog()`            |
| UI-SET-007 | Auth/security panels: env-owned rate limits; no live secrets            |
| UI-SET-008 | Vehicles overview (quote catalog ≠ Fleetbase physical fleet)            |
| UI-SET-009 | Pricing panel + FSA rates card; GTA matrix                              |
| UI-SET-010 | Coverage cities gate retail quotes                                      |
| UI-SET-011 | ConfigFormPanel PUT wired keys; policy keys labeled                     |
| UI-SET-012 | IntegrationPanel actions (Fleetbase / Stripe / Firebase / Maps status)  |
| UI-SET-013 | LeadIngestPanel secrets write → Doppler path                            |
| UI-SET-014 | Channels: email/SMS/push health + staff push budget locked              |
| UI-SET-015 | Audit list + RestoreAuditModal                                          |
| UI-SET-016 | Backup export/import + ImportConfigModal                                |
| UI-SET-017 | EnvOwnedPanel never pretends Doppler fields are editable in DB          |
| UI-SET-018 | [SKIP-POLICY] No UI toggle development↔production project mode          |

---

## 3. API / FastAPI endpoint suites

Prefix assumptions: most under `/v1/admin/…` (confirm router mount in `main.py`).

### 3.1 Cross-cutting API

| ID        | Case                                                         |
| --------- | ------------------------------------------------------------ |
| API-X-001 | OpenAPI lists admin routes; 401 without auth                 |
| API-X-002 | Error envelope stable (`error_envelope` tests)               |
| API-X-003 | IDOR: merchant A data inaccessible with staff lacking module |
| API-X-004 | Rate limit headers on security-sensitive POSTs               |
| API-X-005 | Alembic head applied; no pending migrations in CI            |

### 3.2 Router coverage checklist (smoke each verb)

Use inventory §0 + live route list (~330 admin-facing routes). Minimum per resource:

1. Happy path 2xx
2. Validation 422
3. Forbidden 403 for wrong role
4. Not found 404
5. Side effect audited when mutating

**Must-cover router files**

`admin/{dashboard,orders,finance,leads,claims,support,settings,blog,booking_drafts,audit,data_moat,investor_metrics,monopoly_metrics,platform_metrics,visitor_intelligence}.py`  
`operations.py`, `drivers_admin.py`, `customers_admin.py`, `merchants.py`, `diagnostics.py`, `notifications_admin.py`, `pricing_admin.py`, `security.py`, `collaboration.py`, `shopify.py`

### 3.3 High-risk mutations

| ID          | Case                                                  |
| ----------- | ----------------------------------------------------- |
| API-MUT-001 | Merchant close/reopen idempotent                      |
| API-MUT-002 | Privacy execute irreversible — confirm gate           |
| API-MUT-003 | Finance record-payment double-post rejected           |
| API-MUT-004 | Optimize commit only after successful run             |
| API-MUT-005 | Copilot accept writes audit row                       |
| API-MUT-006 | Settings config PUT writes audit with reason          |
| API-MUT-007 | Lead delete cascades correctly                        |
| API-MUT-008 | Staff role patch cannot escalate self beyond SA rules |

---

## 4. Models / database

| ID     | Case                                                                       |
| ------ | -------------------------------------------------------------------------- |
| DB-001 | `AdminUser`, `Driver`, `Vehicle`, `SystemConfig`, `AdminAuditLog` ORM load |
| DB-002 | Integrity FKs (migration `t2u3…`) — orphan inserts fail                    |
| DB-003 | Order sandbox flag ≠ platform `APP_ENV`                                    |
| DB-004 | Soft lifecycle fields on merchant (no hard delete)                         |
| DB-005 | Notification / device / delivery-log tables consistent with admin queries  |
| DB-006 | Lead ingest + referral credits tables                                      |
| DB-007 | Invoice document / credit notes / wallet package migrations                |
| DB-008 | CRM collapse schema still serves pipeline/calendar                         |
| DB-009 | Postgres 18 image pin; no `:latest`                                        |
| DB-010 | Redis 8.8 / Valkey 8 for Fleetbase cache override                          |

---

## 5. Microservices & integration handshakes

### 5.1 Fleetbase (+ adapter, console, VROOM)

| ID         | Case                                                                       |
| ---------- | -------------------------------------------------------------------------- |
| INT-FB-001 | All Fleetbase HTTP only via `services/fleetbase-adapter`                   |
| INT-FB-002 | Adapter timeout + circuit breaker                                          |
| INT-FB-003 | `_probe_fleetbase`, `_probe_fleetbase_adapter`, `_probe_fleetbase_console` |
| INT-FB-004 | Console probe skips healthy when SSO/bridge disabled                       |
| INT-FB-005 | Booking sync service mirrors order lifecycle                               |
| INT-FB-006 | Sync health / process / requeue from operations                            |
| INT-FB-007 | Optimize engines → VROOM **inside** Fleetbase orchestrator                 |
| INT-FB-008 | [SKIP-POLICY] No PorterChain-native VROOM client                           |
| INT-FB-009 | Web never imports SocketCluster SDK                                        |
| INT-FB-010 | Positions via adapter REST poll — not `positions/replay`                   |

### 5.2 Valhalla / OSRM / Google Maps

| ID         | Case                                                                     |
| ---------- | ------------------------------------------------------------------------ |
| INT-RT-001 | Valhalla primary route/matrix/isochrone probe healthy                    |
| INT-RT-002 | OSRM fallback when Valhalla down                                         |
| INT-RT-003 | Quote/pricing distance never calls Google Distance Matrix                |
| INT-RT-004 | Google Places autocomplete works in address fields                       |
| INT-RT-005 | Map tiles render; costing selector box vs auto                           |
| INT-RT-006 | Digest-pinned Valhalla image only                                        |
| INT-RT-007 | Driver suggestions spatial via Valhalla/OSRM — no haversine in ops layer |

### 5.3 Clerk

| ID          | Case                                          |
| ----------- | --------------------------------------------- |
| INT-CLK-001 | `_portal_slot_apps` returns admin slot        |
| INT-CLK-002 | JWKS fetch; clerk health in readiness         |
| INT-CLK-003 | Directory sync staff/driver/merchant/customer |
| INT-CLK-004 | Invitation / enroll emails                    |
| INT-CLK-005 | [SKIP-POLICY] No Firebase Auth for staff      |

### 5.4 Stripe / payments / COD

| ID         | Case                                                   |
| ---------- | ------------------------------------------------------ |
| INT-ST-001 | Stripe probe; secrets never in Settings UI             |
| INT-ST-002 | Checkout prepaid retail path unchanged                 |
| INT-ST-003 | COD Connect + Payment Link additive                    |
| INT-ST-004 | Webhook signature verify; identity verification events |
| INT-ST-005 | Billing engine invoice lifecycle                       |

### 5.5 Firebase / push / email / notifications

| ID          | Case                                               |
| ----------- | -------------------------------------------------- |
| INT-FCM-001 | `_get_firebase_app` / probe; production ready gate |
| INT-FCM-002 | Admin `firebase-messaging-sw.js` registers         |
| INT-FCM-003 | Web push subscribe (`web-push.ts`)                 |
| INT-FCM-004 | `push_health` admin service                        |
| INT-FCM-005 | SMTP + Mailpit probe (dev)                         |
| INT-FCM-006 | Notification orchestrator send/retry/broadcast     |
| INT-FCM-007 | E2E `phase_7_notifications`                        |
| INT-FCM-008 | [SKIP-POLICY] No second mail/FCM engine            |

### 5.6 Shopify & other ERP / connections

| ID          | Case                                    |
| ----------- | --------------------------------------- |
| INT-SHP-001 | Install URL + OAuth callback            |
| INT-SHP-002 | Webhooks ingest                         |
| INT-SHP-003 | Carrier-service rates quote             |
| INT-SHP-004 | Pickup config PUT; uninstall DELETE     |
| INT-ERP-001 | Merchant webhook delivery + retry       |
| INT-ERP-002 | Merchant API keys rate-limit            |
| INT-ERP-003 | Lead ingest Meta/LinkedIn CAPI settings |
| INT-ERP-004 | Public lead webhooks auth               |
| INT-ERP-005 | Storage backend status (documents/POD)  |

### 5.7 Event bus / workers / websockets

| ID          | Case                                                           |
| ----------- | -------------------------------------------------------------- |
| INT-BUS-001 | Event bus publish smoke + catalog parity                       |
| INT-BUS-002 | Worker queue depths; scheduled jobs / Fleetbase retry          |
| INT-BUS-003 | Admin notification WS                                          |
| INT-BUS-004 | Readiness includes routing + clerk + firebase + fleetbase sync |

---

## 6. Docker / architecture / CI gates

| ID      | Case                                                                      |
| ------- | ------------------------------------------------------------------------- |
| ARC-001 | Compose pins exact tags/digests — never `:latest`                         |
| ARC-002 | Mailpit not Mailhog                                                       |
| ARC-003 | Fleetbase cache Valkey override                                           |
| ARC-004 | `verify_architecture_boundaries.py` Fleetbase URL allowlist               |
| ARC-005 | D2 no illegal cross-engine imports                                        |
| ARC-006 | D3 matrix / dispatch POD contracts                                        |
| ARC-007 | Frontend freeze: no drive-by next/react bumps                             |
| ARC-008 | God-node awareness: Settings/Order/AdminContext changes need blast review |
| ARC-009 | Portal does not call Fleetbase/Valhalla/OSRM directly (API only)          |
| ARC-010 | `APP_ENV` boot-time only; restart required                                |
| ARC-011 | Chaos + layered_architecture diagnostics green on local stack             |
| ARC-012 | CI workflows admin-related jobs green (`ci.yml`, nightly e2e)             |

---

## 7. Super Admin vs Admin — differential suite

| ID       | Super Admin                                        | Admin                                                 |
| -------- | -------------------------------------------------- | ----------------------------------------------------- |
| DIFF-001 | Full Settings write                                | Full Settings write (same module set)                 |
| DIFF-002 | Staff enroll any role including elevating peers    | Same if SpiceDB grants `settings` — assert org policy |
| DIFF-003 | Chaos diagnostics                                  | Chaos allowed (`diagnostics_write`)                   |
| DIFF-004 | `SYSTEM_ALL` modules include merchant catalog keys | Admin typically platform modules only                 |
| DIFF-005 | Can authorize platform users across portals        | Scoped by tuples                                      |
| DIFF-006 | Investor / monopoly / platform metrics endpoints   | Often same read if `reports` — verify Check           |
| DIFF-007 | Lead ingest secret rotation                        | Same if settings                                      |
| DIFF-008 | Audit restore                                      | Same if settings                                      |
| DIFF-009 | Cannot flip project mode in UI                     | Same — both denied                                    |
| DIFF-010 | SpiceDB grant documentation: SA ≠ every portal     | Admin ≠ SA                                            |

> Note: product code treats **settings/diagnostics_write** as `{SUPER_ADMIN, ADMIN}`. Many “super-only” expectations are **policy/process**, not separate module keys — encode those as runbooks, not false 403s.

---

## 8. UX quality (non-functional)

| ID     | Case                                             |
| ------ | ------------------------------------------------ |
| UX-001 | Loading skeletons; error toasts with recovery    |
| UX-002 | Mobile nav collapses; tables horizontal scroll   |
| UX-003 | Empty states for every list                      |
| UX-004 | Destructive actions require confirm              |
| UX-005 | Form dirty-guard on merchant/settings            |
| UX-006 | A11y: focus order on modals; button labels       |
| UX-007 | No secrets in client bundles / network responses |
| UX-008 | Timezone display uses company timezone setting   |

---

## 9. Things easy to miss (added)

| Area                    | Cases to add                                                      |
| ----------------------- | ----------------------------------------------------------------- |
| SpiceDB memory fallback | Boot before container ready → reconnect                           |
| Staff step-up           | Sensitive settings mutations                                      |
| Data moat               | Network / merchant / own-ping-ETA endpoints                       |
| Collaboration           | Activities + tasks CRUD on entities                               |
| Inbox                   | `/inbox` loads + deep links                                       |
| Account security        | `/account/security`                                               |
| System route aliases    | `/system-health`, `/admin/system-tests` redirects                 |
| Investor metrics        | `/investor-metrics`, `/monopoly-metrics`, `/platform-metrics`     |
| Checkr / Identity       | Webhook paths; Admin badges only                                  |
| Referral credits        | Lead referral flow                                                |
| Visitor intelligence    | Session + lead endpoints                                          |
| AI usage                | Diagnostics AI panel; propose-only                                |
| Food/SLA                | Food dispatch SLA if enabled                                      |
| Import route optimize   | Merchant import path visibility from admin                        |
| GPS ingest waves        | Health only from admin ops — no rebuild                           |
| Audit export CSV        | Domain events export                                              |
| Portal middleware       | AdminAccessGate module gating                                     |
| Firebase SW             | Service worker scope                                              |
| ripwire/codegraph       | Re-run sensors after large admin refactors before expanding suite |

---

## 10. Suggested automation map

| Layer       | Tool                               | Owns                                   |
| ----------- | ---------------------------------- | -------------------------------------- |
| Unit        | pytest `apps/api/tests`            | rbac, services, probes                 |
| Contract    | pytest + OpenAPI                   | route envelopes                        |
| Adapter     | `services/fleetbase-adapter/tests` | client breaker                         |
| Portal unit | Vitest                             | `admin-nav`, settings metadata aliases |
| Portal e2e  | Playwright                         | persona login × top routes             |
| Live probes | Diagnostics Test Center            | integration catalog                    |
| Arch gates  | `scripts/verify_*.py`              | boundaries, D2/D3                      |

### 10.1 P0 skeletons (wired to IDs)

| Artifact         | Path                                                                        |
| ---------------- | --------------------------------------------------------------------------- |
| Machine registry | [`docs/testing/admin_p0_registry.json`](testing/admin_p0_registry.json)     |
| pytest suite     | `apps/api/tests/admin_p0/` (`@pytest.mark.tc_id` / `@pytest.mark.admin_p0`) |
| Playwright suite | `apps/admin/e2e/*.p0.spec.ts` (grep `@AUTH-001` / `@p0`)                    |

```bash
pnpm test:admin-p0:api          # pytest P0 (implemented + skipped skeletons)
pnpm --filter @porterchain/admin test:e2e:install
pnpm test:admin-p0:e2e          # Playwright P0 (needs ADMIN_BASE_URL + optional ADMIN_STORAGE_STATE)
```

Fill a skeleton: implement the assert → set `"status": "implemented"` in the registry → remove `pytest.skip` / `test.skip`.

---

## 11. Exit criteria (dev layer)

- [ ] All `ADMIN_TOP_LEVEL_ROUTES` load for SA and AD with correct deny for `read_only`
- [ ] Settings every section opens; Roles matrix matches API catalog
- [ ] Diagnostics full `TEST_IDS` run on local compose
- [ ] Merchant lifecycle without DELETE; finance COD does not break Checkout
- [ ] No Google routing; no SocketCluster in admin bundle; no PC VROOM client
- [ ] Project mode immutable; Clerk triad naming
- [ ] Intentional skips explicitly asserted as absent/held

---

_Generated from live Graphify / CodeGraph / Ripwire inventory. Update this file when nav, `MODULE_PERMISSIONS`, or `TEST_CATALOG` change._
