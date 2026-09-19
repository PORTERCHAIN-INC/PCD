# Development test cases — Clerk (customer + merchant) × PorterChain × Fleetbase

**Audience:** local/CI development (not prod Doppler until the checklist says so).  
**Sensors used to build this (2026-09-17):** Graphify (`ARCHITECTURE.md`, god-nodes, path `clerk_registry.py` ↔ `FleetbaseClient`) → CodeGraph explore (onboarding blast radius) → Ripwire (`--for="Clerk customer merchant portal auth Fleetbase SSO handshake"`).  
**Intentional non-goals:** see [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) (no VROOM client in PC, no Google routing, no SocketCluster in web, no Firebase Auth).

---

## 0. How to run (dev layer)

| Layer            | Command / harness                                                                                                | What it proves                 |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Unit / contract  | `cd apps/api && pytest apps/api/tests/test_clerk_registry.py test_unified_identity_*.py test_auth_cutover.py -q` | Clerk slots, identity, cutover |
| Merchant surface | `pytest apps/api/tests/test_merchant_*.py -q`                                                                    | Portal API + RBAC pages        |
| Customer surface | `pytest apps/api/tests/test_wave2_customers.py -q` (+ booking/payment suites)                                    | Customer APIs                  |
| Adapter          | `cd services/fleetbase-adapter && pytest`                                                                        | Circuit breaker / client       |
| Portal smoke     | `pnpm validate:portal-smoke` · `pnpm validate:portal-ux`                                                         | Pages load gated               |
| SSO wave         | `python3 scripts/verify_wave10_w10_4_sso.py`                                                                     | Fleetbase SSO contract         |
| Architecture     | `pnpm validate:architecture` · `pnpm validate:integrations-matrix`                                               | Boundaries + leaves            |
| E2E chain        | `pnpm validate:e2e` (local compose up)                                                                           | Full SYSTEM_CHAIN              |

**Dev auth:** `CLERK_DEV_BYPASS=true` + portal `NEXT_PUBLIC_CLERK_DEV_BYPASS=true` + `Bearer dev` — every suite must have a twin that **fails closed** when bypass is off.

---

## 1. Critical handshake map (P0 — prove these first)

```
Clerk (customer|merchant slot or unified Platform)
  → JWT / JWKS (clerk_registry.py)
  → portal_guard / get_*_context
  → PorterChain Postgres (Customer | MerchantUser seat)
  → domain engines (booking | merchant_*)
  → fleetbase-adapter (FleetbaseClient)
  → Fleetbase PHP (orders/drivers/tracking/POD)
  → (SSO) POST /v1/auth/sso/fleetbase → FleetbaseSsoClient.exchange_sso_token
```

Graphify shortest undirected path: `clerk_registry.py → Settings ← … → FleetbaseClient.patch`.  
Ripwire ranked SSO symbols: `SsoService`, `exchange_fleetbase_session_for_principal`, `FleetbaseSsoClient.exchange_sso_token`, `sso_fleetbase`.

| ID    | Case                                                           | Expect                                                                                                            |
| ----- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| HS-01 | Customer Clerk JWT → `GET /v1/auth/me`                         | Persona `customer`, stable `porterchain_user_id`                                                                  |
| HS-02 | Merchant Clerk JWT → `GET /v1/merchant/session` (or `/me`)     | Seat + merchant_id; suspended/closed rejected (AZ)                                                                |
| HS-03 | Wrong portal JWT on customer routes                            | 401/403; no identity leak across portals (`assert_clerk_id_exclusive`)                                            |
| HS-04 | Unified vs enterprise Clerk modes (`clerk_configuration_mode`) | Same JWKS triad resolves all kinds **or** slot isolation holds                                                    |
| HS-05 | `pnpm clerk:sync` from `env/clerk.env`                         | API + portals see matching publishable/secret/JWKS names (`CLERK_*` / `CLERK_<PORTAL>_*`) — never `ADMIN_CLERK_*` |
| HS-06 | Customer book → order → Fleetbase sync                         | PC order has `fleetbase_*` ids; adapter retry/circuit does not dual-write                                         |
| HS-07 | Merchant book → Fleetbase                                      | Same as HS-06 + merchant org mapping (`merchant_sync_service`)                                                    |
| HS-08 | Staff/admin `POST /v1/auth/sso/fleetbase`                      | SSO token issued; Fleetbase session exchange succeeds when `fleetbase_sso_enabled`                                |
| HS-09 | SSO disabled / Redis down                                      | Soft fail per `_AUTH_UNAVAILABLE`; no half-open session                                                           |
| HS-10 | Dev bypass **off**                                             | `Bearer dev` rejected on customer + merchant                                                                      |

---

## 2. Clerk identity & auth subsystem

### 2.1 Registry & config

| ID    | Case                                               | File / symbol                                                 |
| ----- | -------------------------------------------------- | ------------------------------------------------------------- |
| CL-01 | Resolve customer / merchant / admin / driver slots | `clerk_registry._portal_slot_apps`                            |
| CL-02 | Platform triad fallback (`CLERK_*` ← admin)        | `resolve_platform_clerk_config`                               |
| CL-03 | Unified mode when all slots share sk+jwks          | `clerk_configuration_mode` / `is_enterprise_clerk_configured` |
| CL-04 | Incomplete triad (publishable-only)                | Client surfaces OK; API JWT verify fails closed               |
| CL-05 | Diagnostics probe Clerk configured                 | `diagnostics_probes` + `is_clerk_secret_configured`           |
| CL-06 | Config audit report                                | `clerk_config_audit.py`                                       |

### 2.2 Claims, guard, sync

| ID    | Case                                                                                               |
| ----- | -------------------------------------------------------------------------------------------------- |
| CL-10 | Parse `ClerkClaims`; reject expired / wrong issuer                                                 |
| CL-11 | `portal_guard.assert_clerk_id_exclusive` — same email cannot bind two portal clerk ids incorrectly |
| CL-12 | `UserSyncService` / `EnsureUserService` upserts `PorterchainUser` + `IdentityLink`                 |
| CL-13 | Clerk webhooks: verify signature, idempotency (`clerk_webhook_*`)                                  |
| CL-14 | Invitation → activate merchant/customer seat                                                       |
| CL-15 | Email identity normalize (`normalize_email`) collision policy                                      |
| CL-16 | Persona bundle / `resolve_persona_principal` for multi-membership merchant                         |

### 2.3 Customer vs merchant auth dependencies

| ID    | Case                                                       | Symbol                                                              |
| ----- | ---------------------------------------------------------- | ------------------------------------------------------------------- |
| CL-20 | `get_customer` / customer context from JWT                 | `auth/customer.py`                                                  |
| CL-21 | `get_merchant_context` rejects suspended/closed            | `auth/merchant.py`                                                  |
| CL-22 | `get_merchant_seats` + org switcher memberships            | seats_for_clerk                                                     |
| CL-23 | Merchant API key auth (not Clerk) isolated from portal JWT | `auth/merchant_api.py`                                              |
| CL-24 | Onboarding evaluate/provision customer                     | `evaluate_customer_onboarding`, `provision_customer_for_onboarding` |
| CL-25 | Merchant onboarding vertical + company file                | `auth/merchant_onboarding.py` + `/v1/auth/merchant/onboarding*`     |

**CodeGraph gap (must close):** `fetchCustomerOnboarding` / `fetchMerchantOnboarding` / `useCustomerOnboarding` / `PortalOnboardingView` — **no tests within 3 caller hops**. Add portal + API contract tests (ONB-* below).

---

## 3. Customer portal — pages, files, APIs

### 3.1 Page matrix (`apps/customer`)

| Page          | Path                      | Gate               | API / side effects                   | Dev cases                                                 |
| ------------- | ------------------------- | ------------------ | ------------------------------------ | --------------------------------------------------------- |
| Home          | `/`                       | public / soft      | links to book/sign-in                | CP-01 redirect signed-in → dashboard                      |
| Sign-in       | `/sign-in/[[...sign-in]]` | Clerk              | session cookie                       | CP-10 sign-in, CP-11 redirect URL safe (`safeRedirect`)   |
| Sign-up       | `/sign-up/[[...sign-up]]` | Clerk              | create user                          | CP-12 password policy (`packages/auth`)                   |
| Onboarding    | `/onboarding`             | Clerk + incomplete | `GET/… /v1/auth/customer/onboarding` | ONB-C-01..05                                              |
| Dashboard     | `/dashboard`              | AccessGate         | `GET /v1/customers/me/dashboard`     | CP-20 empty / with orders                                 |
| Account       | `/account`                | AccessGate         | privacy export/delete, profile       | CP-30..33                                                 |
| Notifications | `/notifications`          | AccessGate         | notification inbox + FCM register    | CP-40..42                                                 |
| Book          | `/book`                   | optional auth      | quotes, drafts, Stripe               | BK-C-*                                                    |
| Book success  | `/book/success`           | return URL         | payment complete                     | BK-C-20 Stripe return (`validate:customer-stripe-return`) |
| Track list    | `/track`                  | public/auth        | search                               | TR-C-01                                                   |
| Track detail  | `/track/[trackingNumber]` | public token       | live track / maps tiles              | TR-C-10..15                                               |

### 3.2 Customer components / libs (file-level)

| Surface      | Files                                                                                               | Cases                                                                                     |
| ------------ | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Gate / shell | `CustomerAccessGate.tsx`, `CustomerShell.tsx`                                                       | CP-G-01 unauth redirect; CP-G-02 pending path; CP-G-03 onboarding force                   |
| Auth package | `@porterchain/auth` (`AppClerkProvider`, `SessionContextProvider`, `InactivityLogout`, `devBypass`) | AUTH-PKG-01..08                                                                           |
| Booking UI   | `components/booking/*`                                                                              | BK-C-UI-*                                                                                 |
| Tracking UI  | `components/tracking/*`                                                                             | TR-C-UI-*                                                                                 |
| Libs         | `lib/api.ts`, `booking.ts`, `onboarding.ts`, `notifications.ts`, `visitor-session.ts`               | API client attaches Bearer; visitor session merges on login (`on_customer_authenticated`) |

### 3.3 Customer API (`/v1/customers`, booking, payments, auth)

| ID    | Endpoint / behavior                                      | Expect                                 |
| ----- | -------------------------------------------------------- | -------------------------------------- |
| CA-01 | `GET /v1/auth/me`                                        | customer persona                       |
| CA-02 | `GET /v1/auth/session-context`                           | portal priority list includes customer |
| CA-03 | `GET /v1/auth/customer/onboarding`                       | steps / complete                       |
| CA-04 | `GET /v1/customers/me/dashboard`                         | trends shape matches TS types          |
| CA-05 | `GET/POST /v1/customers/me/support`                      | ticket CRUD                            |
| CA-06 | `POST /v1/customers/me/rebook/{order_id}`                | draft from prior order                 |
| CA-07 | `GET …/privacy/export` · `POST …/privacy/delete-request` | GDPR path                              |
| CA-08 | Quotes / booking drafts / Stripe checkout                | prepaid path unbroken                  |
| CA-09 | Public track by tracking number                          | no PII beyond allowed                  |
| CA-10 | Cross-tenant: merchant JWT on `/v1/customers/*`          | 403                                    |

### 3.4 Customer onboarding (priority — untested hop)

| ID       | Case                                                                 |
| -------- | -------------------------------------------------------------------- |
| ONB-C-01 | New Clerk user → onboarding incomplete → AccessGate blocks dashboard |
| ONB-C-02 | Complete required steps → provision `Customer` row                   |
| ONB-C-03 | Refresh mid-flow keeps draft                                         |
| ONB-C-04 | Dev bypass still runs evaluate path or documents skip                |
| ONB-C-05 | Email/phone conflict with existing customer merges per policy        |

---

## 4. Merchant portal — pages, files, APIs

### 4.1 Page matrix (`apps/merchant-portal`)

| Page              | Path                           | Module gate    | Primary APIs                               | Cases     |
| ----------------- | ------------------------------ | -------------- | ------------------------------------------ | --------- |
| Landing           | `/`                            | —              | —                                          | MP-01     |
| Sign-in / Sign-up | `/sign-in` `/sign-up`          | Clerk merchant | —                                          | MP-10..12 |
| Onboarding        | `/onboarding`                  | Clerk          | `/v1/auth/merchant/onboarding*`            | ONB-M-*   |
| Dashboard         | `/dashboard`                   | portal         | `GET /v1/merchant/dashboard`               | MP-20     |
| Book              | `/book`                        | booking        | preview/confirm/draft/templates            | BK-M-*    |
| Bulk              | `/bulk`                        | booking        | `/bulk/upload` + confirm                   | BLK-*     |
| Orders            | `/orders`                      | orders         | list/dashboard/bulk labels                 | ORD-*     |
| Order 360         | `/orders/[order_id]`           | orders         | `/orders/{id}/360`, cancel, duplicate, POD | ORD-360-* |
| Track             | `/track`                       | tracking       | tracking dashboard + map                   | TR-M-*    |
| Routes            | `/routes` · `/routes/[job_id]` | routes         | route-imports + standing                   | RT-*      |
| Billing           | `/billing` · invoice detail    | billing        | invoices/pay/COD/export                    | BIL-*     |
| Reports           | `/reports`                     | reports        | summary/export/saved/scheduled             | RPT-*     |
| Team              | `/team`                        | team           | seats/roles/2FA/activity                   | TEAM-*    |
| Settings          | `/settings`                    | settings       | branding/warehouses/tax/docs/notif         | SET-*     |
| Notifications     | `/notifications`               | —              | inbox + prefs                              | NOTIF-M-* |
| Shopify           | `/shopify`                     | integrations   | install/connect/pickup                     | SHOP-*    |
| API               | `/api`                         | integrations   | keys/webhooks/sandbox/ERP/OAuth            | INT-*     |
| Referrals         | `/referrals`                   | —              | referral leads                             | REF-*     |
| Help              | `/help`                        | —              | support KB + tickets                       | HELP-*    |

### 4.2 Merchant components (file-level smoke)

For each client under `apps/merchant-portal/src/components/{billing,booking,bulk,dashboard,help,integrations,orders,portal,providers,referrals,reports,routes,settings,team,tracking,nav,onboarding,maps}`:

| ID      | Case                                                                                                |
| ------- | --------------------------------------------------------------------------------------------------- |
| MP-F-01 | Renders with AccessGate + ModuleGate for role without module → locked UX                            |
| MP-F-02 | Sandbox banner when `is_sandbox` (commercial label ≠ `APP_ENV`)                                     |
| MP-F-03 | Org switcher (`MerchantCompanySwitcher` / memberships) switches merchant_id on subsequent API calls |
| MP-F-04 | `MapsMissingBanner` when Google Places key missing — booking still quotes via Valhalla/OSRM         |
| MP-F-05 | NotificationBell unread count matches API                                                           |

### 4.3 Merchant API groups (`routers/merchant/*` → `/v1/merchant/...`)

**Auth / profile / team**

| ID    | Case                                                                          |
| ----- | ----------------------------------------------------------------------------- |
| MA-01 | session / me / memberships                                                    |
| MA-02 | profile PATCH; addresses; recipients; contacts CRUD                           |
| MA-03 | team overview/roles/activity/2FA                                              |
| MA-04 | Viewer role cannot mutate booking/billing (RBAC — `test_merchant_rbac_pages`) |

**Booking / bulk**

| ID      | Case                                                                               |
| ------- | ---------------------------------------------------------------------------------- |
| BK-M-01 | preview → confirm creates order                                                    |
| BK-M-02 | draft save/resume/confirm                                                          |
| BK-M-03 | multi-parcel                                                                       |
| BK-M-04 | templates CRUD                                                                     |
| BK-M-05 | bulk upload validate → confirm; CSV error paths (`test_merchant_route_csv_errors`) |
| BK-M-06 | Pricing uses Valhalla/OSRM — **never** Google Distance Matrix                      |

**Orders / tracking / POD**

| ID     | Case                                                                         |
| ------ | ---------------------------------------------------------------------------- |
| ORD-01 | list pagination + filters                                                    |
| ORD-02 | 360 payload includes Fleetbase execution fields when synced                  |
| ORD-03 | cancel / duplicate                                                           |
| ORD-04 | labels/print/pickup PDF                                                      |
| ORD-05 | POD zip / slug download                                                      |
| ORD-06 | tracking email send (Mailpit in dev)                                         |
| ORD-07 | live tracking map tiles (Google) + positions via adapter (not SocketCluster) |

**Billing**

| ID     | Case                                                     |
| ------ | -------------------------------------------------------- |
| BIL-01 | invoices list/detail/pay / pay-outstanding               |
| BIL-02 | credit notes, history, tax summary, contract             |
| BIL-03 | rate-card                                                |
| BIL-04 | CSV exports                                              |
| BIL-05 | COD Connect enable path (additive; Checkout still works) |

**Integrations / Shopify / ERP**

| ID      | Case                                                                       |
| ------- | -------------------------------------------------------------------------- |
| INT-01  | API keys create/revoke + rate limit                                        |
| INT-02  | Webhooks CRUD, rotate secret, test, retry delivery                         |
| INT-03  | Sandbox toggle / purge / simulate                                          |
| INT-04  | NetSuite setup/connect/sync                                                |
| INT-05  | Zapier templates                                                           |
| INT-06  | OAuth clients                                                              |
| INT-07  | CSV templates download                                                     |
| INT-08  | Depth / usage / rate-limits docs                                           |
| SHOP-01 | Install URL → callback HMAC                                                |
| SHOP-02 | Carrier service rates handshake (`test_shopify_carrier_pricing_handshake`) |
| SHOP-03 | Order webhook → book (`shopify_service._book_from_shopify_payload`)        |
| SHOP-04 | Pickup warehouse binding                                                   |
| SHOP-05 | Disconnect shop                                                            |

**Reports / standing / privacy / support**

| ID    | Cover with                                              |
| ----- | ------------------------------------------------------- |
| RPT-* | each `/reports/*` + export csv/xlsx                     |
| RT-*  | route-imports full state machine + standing-orders CRUD |
| PRV-* | privacy export / delete-request                         |
| SUP-* | tickets + claims + KB                                   |

### 4.4 Merchant onboarding

| ID       | Case                                                                                |
| -------- | ----------------------------------------------------------------------------------- |
| ONB-M-01 | Gate blocks portal until onboarding complete                                        |
| ONB-M-02 | Vertical patch                                                                      |
| ONB-M-03 | Company file completeness banner                                                    |
| ONB-M-04 | Unprovisioned signup visible to admin (`/v1/admin/merchants/unprovisioned-signups`) |
| ONB-M-05 | Activation policy (`test_merchant_activation_policy`)                               |

---

## 5. Fleetbase adapter & ops handshakes

| ID    | Module                            | Case                                                                                    |
| ----- | --------------------------------- | --------------------------------------------------------------------------------------- |
| FB-01 | `FleetbaseClient`                 | timeout → retry policy → circuit open → fail fast (`test_client_timeout_breaker`)       |
| FB-02 | orders                            | create/update mirrors PC commercial order                                               |
| FB-03 | drivers / vehicles                | read models for admin/merchant track — no PC re-implementation                          |
| FB-04 | tracking                          | REST positions poll; web never imports SocketCluster                                    |
| FB-05 | POD                               | fetch for merchant download                                                             |
| FB-06 | dispatch / routes / orchestrator  | VROOM stays behind Fleetbase; diagnostics probe engines only                            |
| FB-07 | zones / manifests                 | wrap-only                                                                               |
| FB-08 | webhooks inbound                  | signature + idempotency                                                                 |
| FB-09 | `merchant_sync_service`           | merchant org ↔ Fleetbase contact/company                                                |
| FB-10 | SSO                               | `FleetbaseSsoClient.exchange_sso_token` with roles/permissions                          |
| FB-11 | Admin Fleetbase console launchers | Intentionally removed — permanent bond is API `:8000`; ops surface is PorterChain admin |

**Negative:** FB-N-01 inventing PC VROOM HTTP client · FB-N-02 storing GPS SoT in PC · FB-N-03 merchant using the Fleetbase Ember console as product UI.

---

## 6. Spatial stack (Valhalla / OSRM / VROOM / Google)

| ID    | Case                                          | Policy                                                 |
| ----- | --------------------------------------------- | ------------------------------------------------------ |
| SP-01 | Quote distance/duration via Valhalla          | primary                                                |
| SP-02 | Valhalla down → OSRM fallback                 | maps service                                           |
| SP-03 | Vehicle class costing (box vs auto)           | `test_valhalla_costing`                                |
| SP-04 | Matrix / isochrone where used                 | Valhalla                                               |
| SP-05 | Google Places autocomplete in book UI         | allowed                                                |
| SP-06 | Google map tiles in track UI                  | allowed                                                |
| SP-07 | Google Distance Matrix / Directions for price | **FORBIDDEN**                                          |
| SP-08 | VROOM optimization                            | only via Fleetbase orchestrator probe                  |
| SP-09 | No haversine in `admin_engine` ops paths      | `validate:architecture` / `verify_no_ops_spatial_math` |

---

## 7. Notifications, email, Firebase push

| ID    | Case                                                                                |
| ----- | ----------------------------------------------------------------------------------- |
| NT-01 | Notification engine creates `NotificationRecord` for customer + merchant principals |
| NT-02 | Email delivery → Mailpit in dev (`_probe_mailpit`)                                  |
| NT-03 | Role matrix (`test_notification_role_matrix`)                                       |
| NT-04 | Loud push ops (`test_notification_ops_loud_push`)                                   |
| NT-05 | Customer/merchant register web push / FCM token (Firebase **Messaging**, not Auth)  |
| NT-06 | Preference PATCH respects channel toggles                                           |
| NT-07 | Tracking email from merchant order                                                  |
| NT-08 | Onboarding / invoice reminder emails                                                |
| NT-09 | No second mail/FCM engine (intentional skip)                                        |

---

## 8. Payments & Stripe

| ID    | Case                                                        |
| ----- | ----------------------------------------------------------- |
| ST-01 | Customer Checkout prepaid happy path                        |
| ST-02 | Webhook idempotency table                                   |
| ST-03 | Merchant invoice pay                                        |
| ST-04 | COD via Connect / Payment Link additive — Checkout unbroken |
| ST-05 | Stripe mock vs live gated by env; never flipped by admin UI |

---

## 9. Database, models, authz

| ID    | Case                                                                                   |
| ----- | -------------------------------------------------------------------------------------- |
| DB-01 | Alembic upgrade head on clean Postgres 18                                              |
| DB-02 | Customer / Merchant / MerchantUser / Order / IdentityLink FKs                          |
| DB-03 | SpiceDB / tuple writer sync on seat changes (`test_spicedb_authz`, `test_hybrid_rbac`) |
| DB-04 | Soft-close merchant — no hard DELETE                                                   |
| DB-05 | Sandbox order flag ≠ platform `APP_ENV`                                                |
| DB-06 | Pool / stateless API (`verify_db_pool`, `verify_api_stateless`)                        |

God-nodes to regression-watch (Graphify): `Settings`, `Order`, `MerchantContext`, `AdminContext`, `Merchant`.

---

## 10. Docker / compose / microservices

| ID    | Service                                                   | Case                                                      |
| ----- | --------------------------------------------------------- | --------------------------------------------------------- |
| DK-01 | postgres                                                  | healthy; PC DSN `postgresql+psycopg`                      |
| DK-02 | redis / valkey (Fleetbase override)                       | cache + SSO session deps                                  |
| DK-03 | mailpit                                                   | catch-all SMTP                                            |
| DK-04 | valhalla                                                  | digest-pinned image; route probe                          |
| DK-05 | osrm                                                      | ETA fallback                                              |
| DK-06 | vroom                                                     | only as Fleetbase dependency — not called from PC engines |
| DK-07 | fleetbase + override                                      | adapter base URL reachable                                |
| DK-08 | api + worker                                              | same settings; Clerk JWKS at boot only                    |
| DK-09 | spicedb                                                   | migrate + authorize                                       |
| DK-10 | No `:latest` tags in compose                              | pin audit                                                 |
| DK-11 | `services/pricing-engine`, `event-bus`, `driver-platform` | unit tests green; gateway registry lazy loads             |

---

## 11. Website & public book (Clerk-adjacent)

Retail often starts on `website` then continues in `apps/customer`.

| ID     | Case                                                                |
| ------ | ------------------------------------------------------------------- |
| WEB-01 | `/book` anonymous draft + visitor session                           |
| WEB-02 | Continue → customer Clerk attach (`on_customer_authenticated`)      |
| WEB-03 | Navbar Clerk (`SiteNavbarAuthClerk`) portal priority                |
| WEB-04 | Track public pages                                                  |
| WEB-05 | `validate:product-vision` / SEO smoke still pass after auth changes |

---

## 12. Admin / staff (boundary of this doc)

Customer/merchant Clerk must not unlock admin. Still include:

| ID    | Case                                                   |
| ----- | ------------------------------------------------------ |
| AD-01 | Staff IdP / passkey path separate from portal Clerk    |
| AD-02 | Admin merchant lifecycle approve/suspend/close/convert |
| AD-03 | Clerk directory service for merchant users             |
| AD-04 | Fleetbase SSO from admin only                          |
| AD-05 | Project mode immutable (`403 project_mode_immutable`)  |

---

## 13. Architecture & contract validators (always-on)

Treat these as automated test cases:

- `pnpm validate:architecture`
- `pnpm validate:integrations-matrix`
- `pnpm validate:golden-rules`
- `pnpm validate:router-audit`
- `pnpm validate:oauth`
- `pnpm validate:observability`
- `pnpm validate:integration-adapter`
- `scripts/verify_wave10_w10_4_sso.py`
- `pnpm validate:portal-smoke` / `validate:portal-ux` / `validate:tracking-maps` / `validate:booking-a11y`

---

## 14. Systems you did not name (still in scope)

| System                          | Why test                                              |
| ------------------------------- | ----------------------------------------------------- |
| SpiceDB / OpenFGA tuples        | Merchant RBAC + hybrid authz                          |
| Redis                           | Principal cache, rate limits, SSO                     |
| Event bus                       | Order/notification fan-out                            |
| Worker                          | Async Fleetbase sync, reminders, sweeps               |
| OAuth (`/v1/...` oauth router)  | Merchant integration clients                          |
| Lead ingest / webhooks          | Merchant referrals + public leads                     |
| Zoho calendar adapter           | `integrations/zoho_calendar.py`                       |
| Doppler / secrets sync          | Prod mirror of `clerk:sync`                           |
| Mobile customer / driver shells | Handshake parity later; do not block portal P0        |
| Collaboration router            | Shared ops if merchant exposed                        |
| Security router                 | Step-up / session hygiene boundaries                  |
| Diagnostics readiness           | Clerk/Mailpit/Valhalla/Fleetbase probes               |
| Pricing engine service          | Contract with merchant rate-card                      |
| Checkr / Stripe Identity        | Driver-only; assert merchant/customer paths untouched |

---

## 15. Suggested implementation order (Jeff Dean)

1. **P0 handshakes** HS-01..10 + CL-01..05 + FB-01/10
2. **Close CodeGraph gap** ONB-C-* + ONB-M-* (portal + API)
3. **Customer critical path** book → pay → track → Fleetbase
4. **Merchant critical path** book → order 360 → track → billing pay
5. **Shopify carrier + webhook** SHOP-01..03
6. **Notifications + Mailpit + FCM register** NT-*
7. **Spatial policy** SP-01..09
8. **Integrations matrix** NetSuite/Zapier/OAuth/sandbox
9. **Docker pin + readiness** DK-*
10. **Full `validate:e2e` SYSTEM_CHAIN**

---

## 16. Traceability (sensor → artifact)

| Sensor    | Finding                                                                           | Test IDs                       |
| --------- | --------------------------------------------------------------------------------- | ------------------------------ |
| Graphify  | Clerk ↔ Fleetbase via Settings; god-nodes Settings/Order/MerchantContext          | HS-*, DB-06, god-node watch    |
| Graphify  | `merchant_sync_service`, shopify, notification, maps leaves                       | FB-09, SHOP-_, NT-_, SP-*      |
| CodeGraph | Onboarding hooks untested within 3 hops                                           | ONB-C-_, ONB-M-_               |
| Ripwire   | SSO ranked high churn (`sso_service`, `FleetbaseSsoClient`, `MerchantAccessGate`) | HS-08/09, FB-10, MP gate cases |
| Ripwire   | `PLATFORM_PORTALS = customer, merchant` in `sync-clerk-env.mjs`                   | HS-05, CL-01                   |

---

_Update this file when portal routes or Clerk mode (unified vs enterprise) changes; re-run Graphify folder update after large auth moves._
