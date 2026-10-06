# PorterChain architecture (living)

**Type:** CANONICAL · **Verified:** 2026-09-17 · **Map:** `graphify-out/GRAPH_REPORT.md` (17 616 nodes, 50 030 edges)

Graphify first, then this file. Do not restore the deleted markdown novel. Live pins live in `.cursor/rules/porterchain-stack.mdc`. Charter (root): [docs/PORTERCHAIN_CHARTER.md](docs/PORTERCHAIN_CHARTER.md).

**Dispatch stays in PorterChain.** The day solver is OR-Tools in `dispatch_engine`. Valhalla is the road cost. Google is Places and map tiles. There is no Fleetbase adapter and no vendor console.

Each layer below is **Finished / Current / Required**. Core is the charter. Leaves are personas and vendor boxes. Do not skip a trunk.

```
charter (why we exist)
        │
ARCHITECTURE.md + FastAPI :8001 + *_engine
        │
adapters: MapsService · Stripe sdk.py · Clerk · FCM
        │
Valhalla :8002 → OSRM :5000 (GTA ±150 km) │ Stripe │ Clerk │ Firebase FCM │ OR-Tools day plan
        │
admin :3002 · merchant :3001 · customer :3004 · website :3000
driver web BFF :3003 · driver iOS/Android · customer iOS/Android
```

---

## Root — identity

PorterChain is a **Transportation Capacity Network**. Customers pay for capacity (vehicle + driver). Software is the engine, not the SKU. The network is the moat.

|              |                                                                             |
| ------------ | --------------------------------------------------------------------------- |
| **Finished** | Charter gate (10-customer test) in `.cursor/rules/porterchain-charter.mdc`  |
| **Current**  | [docs/PORTERCHAIN_CHARTER.md](docs/PORTERCHAIN_CHARTER.md) is the file SSOT |
| **Required** | Do not sell Phase 3 metrics as today’s SKU                                  |

---

## Trunk — request path

Next.js portals + Expo apps → HTTPS `:8001` (`/v1/*`, `/driver-api/v1/*`) → thin FastAPI routers → `*_engine` → adapters → Postgres **18** / Redis **8.8**. Worker drains EventBus + day-plan / routing queues.

Web apps never call SocketCluster. Google Maps is Places + tiles only — never distance, ETA, matrix, or geometry for pricing/dispatch.

```
portal / website / mobile
        │  :8001
   routers (auth + require_module + one service call)
        │
   engines (commercial / domain) including dispatch_engine
        │
   adapters: MapsService · Stripe sdk.py · Clerk auth/ · FCM
        │
   Valhalla :8002 → OSRM :5000 │ Stripe │ Clerk │ Firebase
```

Driver web uses a Next BFF (`/api/driver` → `/driver-api/v1`). Mobile driver uses Bearer directly. Do not unify those.

| Context               | Owns                                              | Does not own                |
| --------------------- | ------------------------------------------------- | --------------------------- |
| `booking_engine`      | Quotes, bookings, payments, public track snapshot | Live GPS SoT                |
| `merchant_engine`     | Org, portal APIs, ingest, commercial booking      | Driver online SoT, road TSP |
| `admin_engine`        | Control Tower, staff RBAC, settings               | Custom dispatch board       |
| `pricing_engine`      | Quote bridge, SQLAlchemy pricing repo             | Dispatch assignment         |
| `billing_engine`      | Ledger, COD/Connect _policy_                      | Stripe SDK                  |
| `dispatch_engine`     | OR-Tools day plan, GPS board, optimize run store  | Multi-van fleet split       |
| `driver_engine`       | Duty, accept, proof, Redis last-known GPS         | Day solver                  |
| `auth` / `authz`      | Clerk verify, SpiceDB Check                       | Caching Check allows        |
| `notification_engine` | FCM / email orchestration                         | Identity provider           |

ORM: `*_models.py` under `apps/api/src/porterchain_api/`. Contracts: `schemas_*.py`. Import `booking_models` directly.

|              |                                                                                                                                                  |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Finished** | Waves 1–8 isolation (maps public API, route_import facade, `models.py` gone, HTTP census, vendor leaves, ORM write ownership + allowlist shrink) |
| **Current**  | 639 operations / 568 paths — [`docs/api/openapi.json`](docs/api/openapi.json)                                                                    |
| **Required** | Routers stay thin. No new inline `BaseModel`. No PorterChain VROOM client. No new `*_models.py` writers outside the owning engine                |

---

## Branch — spatial black boxes

1. **Valhalla** (`porterchain-valhalla` :8002) — primary: routes, matrix, isochrones, costing.
2. **OSRM** (`porterchain-osrm` :5000) — ETA / distance fallback when Valhalla is down. Same **GTA ±150 km** PBF as Valhalla (`infrastructure/docker/scripts/prepare-valhalla-gta.sh` then `prepare-osrm-gta.sh`). Not 150 GB. Not full Ontario.
3. **OR-Tools** in `dispatch_engine/sequencer.py` — one-van day plan. No VROOM client.
4. **Google** — Places autocomplete and map tiles only.

Canonical client: `services/python/porterchain_services/maps/service.py` (`MapsService`). Pricing façade: `apps/api/src/porterchain_api/services/routing.py` (`resolve_route_distance`).

Engines may call public `route`, `route_with_source`, `route_distance_meters`, `route_multi`, `matrix_durations`, `isochrone`, `eta_between`, `optimized_route`. They must never call `_osrm_*` or `_valhalla_*`.

**The day solver is OR-Tools in `dispatch_engine`.** Valhalla is the road cost. OSRM is only a labeled fallback when Valhalla is down, and it stays off in production. Google is Places and map tiles. Do not add a VROOM client or a Fleetbase HTTP call for dispatch, GPS, or proof.

`https://router.project-osrm.org` is a **labeled last resort** inside `MapsService` (`OSRM_PUBLIC_DEMO_LAST_RESORT`) gated by `osrm_allow_public_demo` (default **false**). It must not be the env/compose default.

|              |                                                                  |
| ------------ | ---------------------------------------------------------------- |
| **Finished** | Valhalla digest-pinned; GTA ±150 km extract; OR-Tools day plan   |
| **Current**  | MapsService Valhalla-first; OSRM host is local `:5000`           |
| **Required** | CI fails unlabeled public OSRM; no VROOM client under `*_engine` |

---

## Branch — identity and push

| Vendor       | Interface                                                  | Not                                            |
| ------------ | ---------------------------------------------------------- | ---------------------------------------------- |
| **Clerk**    | `CLERK_<PORTAL>_*` via `env/clerk.env` + `pnpm clerk:sync` | Firebase Auth; ad-hoc `ADMIN_CLERK_SECRET_KEY` |
| **Firebase** | FCM device tokens + `notification_engine`                  | Login, session, RBAC                           |
| **SpiceDB**  | Check (no caching allows)                                  | Identity provider                              |

Local: `CLERK_DEV_BYPASS=true` on API; portals `NEXT_PUBLIC_CLERK_DEV_BYPASS`. No customer Clerk bypass as a product shortcut.

|              |                                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| **Finished** | Per-portal Clerk triad; FCM on Expo driver/customer; admin Clerk JWT retired                                                    |
| **Current**  | Staff IdP (passkey/magic link + Redis session) for admin; Clerk for merchant/driver/customer portals + mobile; FCM is push only |
| **Required** | Mobile still hits `:8001` with Clerk Bearer (driver) / public track (customer); admin browser prefers BFF cookie → Bearer       |

---

## Branch — money

Stripe Checkout remains the retail prepaid path. COD via Connect + Checkout/Payment Link is additive (`billing_engine/stripe_cod_service.py` → FastAPI port `services/stripe_service.py`). The only `import stripe` is [`porterchain_services/stripe/sdk.py`](services/python/porterchain_services/stripe/sdk.py).

|              |                                                      |
| ------------ | ---------------------------------------------------- |
| **Finished** | SDK isolation (Wave 2); COD freeze lifted 2026-09-12 |
| **Current**  | Policy in billing_engine; SDK in sdk.py              |
| **Required** | `_STRIPE_ALLOWLIST` stays exact                      |

---

## Branch — execution

Dispatch, driver duty, live GPS, proof, and the day plan live in PorterChain. Valhalla is the road cost. Do not add a second console or a Fleetbase HTTP call.

|              |                                             |
| ------------ | ------------------------------------------- |
| **Finished** | Day solver is OR-Tools in `dispatch_engine` |
| **Current**  | One assigned van, at most 25 stops          |
| **Required** | No Fleetbase HTTP from the API              |

---

## Leaf — HTTP census (Wave 3)

One public interface per persona. Guard: `scripts/openapi_census.py`.

| Persona         | Prefix                         | Auth                                                       |
| --------------- | ------------------------------ | ---------------------------------------------------------- |
| Staff           | `/v1/admin`                    | Staff IdP session (`pc_staff_sid` / `Bearer staff_sess_*`) |
| Merchant portal | `/v1/merchant`                 | Clerk org                                                  |
| Partner API     | `/v1/merchant-api`             | API key + idempotency                                      |
| Driver mobile   | `/driver-api/v1`               | Clerk Bearer                                               |
| Retail book     | `/v1/quotes` `/v1/bookings`    | session / checkout                                         |
| Public track    | `/v1/orders/{tracking_number}` | none                                                       |
| Vendors         | `/webhooks/clerk\|stripe`      | signatures                                                 |

Cut (must stay gone): `POST /driver/location`, `GET /v1/merchant/tracking/orders/{id}`, `POST .../invoices/{id}/resend`.

Kept as different callers: dual merchant book; webhook CRUD vs integrations logs.

|              |                                            |
| ------------ | ------------------------------------------ |
| **Finished** | 639/639 classified (2026-09-15)            |
| **Current**  | Snapshot matches live `:8001/openapi.json` |
| **Required** | New untagged business paths fail CI        |

---

## Leaf — personas (web)

| App        | Port  | Hits                                        |
| ---------- | ----- | ------------------------------------------- |
| Website    | :3000 | `:8001` quotes/bookings + Places            |
| Merchant   | :3001 | `/v1/merchant/*`                            |
| Admin      | :3002 | `/v1/admin/*`                               |
| Driver web | :3003 | BFF `/api/driver` → `/driver-api/v1`        |
| Customer   | :3004 | `/v1/quotes` `/v1/bookings` `/v1/customers` |

Admin **list** = scan the book. **Detail** = operate one company. Merchant **Settings** = rare org config. **Billing** = money. **Team** = seats. Admin does not mint API keys or Shopify; the merchant creates, admin revokes/disables.

| Surface               | Owns                                                                                  | Does not own                                               |
| --------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Admin list            | Status, health, search, AR outstanding                                                | Industry / terms / API as default columns                  |
| Admin detail Overview | Standing, next actions (heuristic)                                                    | Fake “AI insights” as a product                            |
| Admin detail Billing  | Cycle AR preview/generate, invoices, contracts                                        | Rate card (Pricing) · recording payments (Finance invoice) |
| Admin detail Settings | Identity, commercial terms, tax, coverage, COD/Stripe flags                           | Invoices, seats, API keys                                  |
| Merchant Settings     | Profile, locations, delivery contacts, alert prefs, branding, tax, documents, privacy | Invoices, keys, Shopify                                    |
| Merchant Billing      | Invoices, statements, credits, billing contacts, rates                                | Alert prefs                                                |
| Merchant Reports      | Own delivery, spend, destinations, claims                                             | Driver / vehicle fleet internals                           |

---

## Leaf — personas (mobile iOS / Android)

Expo **SDK 57** / RN **0.86**. EAS projects exist. Wave 4 contracts the API surface; it does not clone Navigator.

| App      | Bundle                     | API                                              |
| -------- | -------------------------- | ------------------------------------------------ |
| Driver   | `com.porterchain.PCD`      | `EXPO_PUBLIC_API_URL` → `:8001` `/driver-api/v1` |
| Customer | `com.porterchain.customer` | same host; public `/v1/orders/{n}` + Clerk       |

FCM: `google-services.json` / `GoogleService-Info.plist` on each app. Clerk: `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`.

|              |                                                                              |
| ------------ | ---------------------------------------------------------------------------- |
| **Finished** | Handshake probes `:8001`; driver fetch prefix `/driver-api/v1`               |
| **Current**  | Shells with Clerk + FCM + location (driver)                                  |
| **Required** | CI: no `:8000`, no `fleetbase` HTTP, no SocketCluster in `apps/mobile-*/src` |

---

## God nodes (Graphify + live code)

**Wave 1 paid down (do not redo):** `import_route_optimize.py` (maps.sequence shim); tracking/public snapshots on public Maps APIs; Stripe FastAPI port in `services/stripe_service.py`; router BaseModels gone; `merchants` / `pricing_components` / `operations` have no inline ORM.

**Wave 2 isolation (2026-09-15):** `merchant_engine/route_import_service.py` is orchestration only (~431 LOC). Quote/distance in `import_quote.py`; confirm + Fleetbase stop payload in `import_confirm.py`; worker apply_* in `import_jobs.py`. `models.py` deleted. Stripe SDK is `porterchain_services/stripe/sdk.py` only.

**Wave 3 HTTP census (2026-09-15):** 639 operations / 568 paths. Guard: `scripts/openapi_census.py`.

**Wave 3 complete.** HTTP aliases are not the remaining mash-up.

**Wave 4 root-to-leaf (2026-09-15):** Tree in this file. Local OSRM from the same GTA ±150 km PBF. Public OSRM demo is labeled last-resort only. Thin pointers: charter, API README, PARTNER_GUIDE, POINTER_STUB_INDEX. Guard: `scripts/verify_vendor_leaves.py`.

**Dead strangler:** `models.py` deleted. Import `booking_models`.

**Wave 5 model ownership (2026-09-15):** ORM writes isolated behind owning engines. Merchant close/COD Connect flags live in `merchant_engine`; CRM status/projection in `collaboration_engine`; driver `is_online` in `admin_engine`; convert-to-customer Customer + credit notes in `booking_engine` / `billing_engine`. Driver jobs router no longer imports `merchant_models` or commits. Guard: `scripts/verify_model_ownership.py` (allowlists not grown).

**Wave 6 allowlist shrink (2026-09-15):** Foreign-model reads go through owner lookups (`merchant_engine/lookups.py`, `admin_engine/driver_lookups.py`, `staff_lookups.py`). Stale + commit-only allowlist rows dropped. Merchant legacy 32→11, admin 25→17, CRM 2→1. Remaining CRM writer is portal `contacts_service`.

**Wave 7 allowlist shrink (2026-09-15):** CRM contacts are a merchant façade over `collaboration_engine`. Contract→merchant create goes through `merchant_engine/provision.py`. Ticket/claim writes go through `support_engine` (extra owner of `admin_models`). Fleetbase webhook Claim/Driver writes go through `support_engine` + `admin_engine` driver lookups. Merchant legacy 11→9, admin 17→9, CRM 1→0.

**Wave 8 allowlist shrink (2026-09-15):** Gateway usage logs, portal signup, privacy DSR, and Settings authorize go through `merchant_engine`. Staff WebAuthn, dev admin, invitations, and SSO reads go through `admin_engine`. Merchant legacy 9→3, admin 9→3. Remaining: `merchant_service`, identity `user_sync` / `identity_fk_backfill`, billing driver payouts.

**Wave 9 allowlist shrink (2026-09-15):** Identity Clerk rebind and profile FK stamps go through owner lookups. Driver payouts are created/marked in `admin_engine`; billing keeps the wallet ledger. Merchant legacy 3→1, admin 3→0. Remaining: `admin_engine/merchant_service.py`.

**Wave 10 allowlist shrink (2026-09-15):** Admin merchant lifecycle stays in `AdminMerchantService`; Merchant/MerchantUser writes go through `merchant_engine` provision, lookups, team seats, and lifecycle. Merchant legacy 1→0. Remaining driver ledger: `billing_engine/driver_finance_service.py`.

**Wave 11 allowlist shrink (2026-09-15):** Driver wallet ledger rows are written in `driver_engine/wallet_ledger.py`. Billing still prices payouts and reads the ledger. Driver legacy 1→0. Remaining: identity/user allowlist (5).

**Wave 12 allowlist shrink (2026-09-15):** SSO identity upserts go through `auth/identity_links.py`. Stale identity allowlist rows that were already owners dropped. Identity legacy 5→0. Remaining user-model leftovers: merchant onboarding, auth dependencies, staff IdP.

**Wave 13 allowlist shrink (2026-09-15):** Staff `porterchain_users` rows are created in `auth/staff_identity.py`. AdminUser bind + SpiceDB sync stay in `staff_idp_service`. Stale onboarding/dependencies allowlist rows dropped. User-model leftover 3→0.

**Wave 14 thin router (2026-09-15):** Merchant switcher memberships are assembled in `merchant_engine/team_service.py` (`list_switcher_memberships`). `routers/merchant/profile_team.py` is one service call — dropped from `_LEGACY_ROUTER_LOGIC` (14→13). Do not vanity-split `routers/merchants.py`. Remaining logic debt: auth, oauth, finance, orders, driver jobs/auth_dev, operations, merchants HTTP surface.

**Wave 15 thin router (2026-09-15):** Local driver email picker reads go through `driver_engine/auth_service.py` + `admin_engine/driver_lookups.py`. `routers/driver/auth_dev.py` dropped from `_LEGACY_ROUTER_LOGIC` (13→12). Remaining `db.query` in routers: `oauth.py`, `admin/finance.py`. Do not vanity-split `routers/merchants.py`.

**Wave 16 thin router (2026-09-15):** OAuth token merchant reads go through `merchant_engine/lookups.get_merchant`. `routers/oauth.py` dropped from `_LEGACY_ROUTER_LOGIC` (12→11). Remaining inline `db.query` in routers: `admin/finance.py` (`finance_cod_queue`). Do not vanity-split `routers/merchants.py`.

**Wave 17 thin router (2026-09-15):** Admin COD collection queue reads go through `StripeCodService.list_collection_queue`. `routers/admin/finance.py` dropped from `_LEGACY_ROUTER_LOGIC` (11→10). No leftover `db.query` in routers. Remaining logic debt is fat-but-coherent surfaces (`merchants.py`, `operations.py`, `auth.py`, driver jobs). Do not vanity-split `routers/merchants.py`.

**Wave 18 thin router (2026-09-15):** Customer onboarding provision+commit lives in `auth/customer_onboarding.py` (`provision_customer_for_onboarding`). `routers/auth.py` dropped from `_LEGACY_ROUTER_LOGIC` (10→9). Remaining commit debt: admin booking drafts, claims, orders. Do not vanity-split `routers/merchants.py`.

**Wave 19 thin router (2026-09-15):** Admin booking-draft audit+commit lives in `admin_engine/audit.py` (`commit_admin_audit`). `routers/admin/booking_drafts.py` dropped from `_LEGACY_ROUTER_LOGIC`. Stale allowlist rows with no remaining `db.query`/`db.commit`/model-import (`driver/jobs.py`, `drivers_admin.py`, `merchant/route_imports.py`, `operations.py`, `merchants.py`, `pricing_components.py`) also dropped (9→2). Remaining commit debt: admin claims, orders. Do not vanity-split `routers/merchants.py` (still LOC-capped).

**Wave 20 thin router (2026-09-15):** Admin invoice generate/resend commit lives in `InvoiceService` (`commit=True`). Assist decide/playbook persist in `OrderAssistService`. `routers/admin/orders.py` dropped from `_LEGACY_ROUTER_LOGIC` (2→1). Remaining commit debt: `admin/claims.py`. Do not vanity-split `routers/merchants.py`.

**Wave 21 thin router (2026-09-15):** Admin claims audit+commit lives in `commit_admin_audit` / `commit_admin_write`. `routers/admin/claims.py` dropped from `_LEGACY_ROUTER_LOGIC` (1→0). Inline router `db.query`/`db.commit`/banned model-import is 0. Do not vanity-split `routers/merchants.py` (still LOC-capped).

**Wave 22 thin router (2026-09-15):** Driver assigned-order access lives in `DriverApiService.require_assigned_order`. Package scan payload parse lives in `ScanGateService.scan_qr_from_body`. COD checkout merchant resolve lives in `StripeCodService.issue_cod_checkout_for_order`. `routers/driver/jobs.py` dropped from `_LEGACY_ROUTER_LOC` (355→334, under 350). Stale LOC caps shrunk (11→10). Do not vanity-split `routers/merchants.py` (still LOC-capped at 853).

**Wave 23 thin router (2026-09-15):** Merchant booking idempotency replay lives in `MerchantBookingService.run_idempotent`. Bulk job payload and template payload live in `MerchantBulkService.upload_payload` / `template_payload`. `routers/merchant/dashboard_booking.py` dropped from `_LEGACY_ROUTER_LOC` (394→336, under 350). Do not vanity-split `routers/merchants.py`. Did not grow `booking_flow_service.py`.

**Wave 24 thin router (2026-09-15):** Ops Fleetbase sync retry/requeue and queue depths live in `AdminOperationsService`. Copilot `driver_id` and optimize `assignments` validation live in owning services. `routers/operations.py` is `_invoke` + one service call — dropped from `_LEGACY_ROUTER_LOC` (407→330, under 350). Do not vanity-split `routers/merchants.py`. Did not rebuild the dispatch board.

**Wave 25 thin router (2026-09-15):** Settings write-key resolution lives in `settings_bindings.resolve_writable_config_key`. Platform user-type / Clerk directory rules live in `clerk_directory_service` and `platform_user_authorize`. `routers/admin/settings.py` is `_invoke` + one service call — dropped from `_LEGACY_ROUTER_LOC` (410→344, under 350). Do not vanity-split `settings_service.py` or `routers/merchants.py`.

**Wave 26 thin router (2026-09-15):** Merchant `/session` and `/me` payloads live in `MerchantProfileService`. Team seat mutations sync CRM contacts in `MerchantTeamService`. `routers/merchant/profile_team.py` is `_invoke` + one service call — dropped from `_LEGACY_ROUTER_LOC` (413→317, under 350). Do not vanity-split `routers/merchants.py`.

**Wave 27 thin router (2026-09-15):** Merchant OAuth client list payload lives in `MerchantIntegrationsService.list_oauth_clients`. Integrations HTTP error mapping lives in `_invoke` + `integration_error_message`. `routers/merchant/integrations.py` dropped from `_LEGACY_ROUTER_LOC` (418→277, under 350). Do not vanity-split `shopify_service.py` or `routers/merchants.py`.

**Wave 28 thin router (2026-09-15):** `/me` and session-context payloads live on `CurrentPrincipal`. Staff login/passkey/enrollment cookie assembly lives in `staff_session`. Customer onboarding compose lives in `customer_onboarding_payload` (commit stays out of `auth/customer.py`). `routers/auth.py` dropped from `_LEGACY_ROUTER_LOC` (462→228, under 350). Do not vanity-split `routers/merchants.py`.

**Wave 29 thin router (2026-09-15):** Merchant cancel/duplicate of an owned order lives in `MerchantOrdersService.cancel_owned` / `duplicate_owned`. Tracking/print/POD HTTP mapping lives in `_invoke`. `routers/merchant/orders_tracking.py` dropped from `_LEGACY_ROUTER_LOC` (492→334, under 350). Do not vanity-split `routers/merchants.py`. Did not grow `tracking_service.py`.

**Wave 30 thin router (2026-09-15):** Admin driver push/SMS/email + CRM activity lives in `auth.driver_admin_action.run_admin_driver_action`. Existing-driver Clerk invite payload lives in `InvitationService.invite_existing_driver`. `routers/drivers_admin.py` dropped from `_LEGACY_ROUTER_LOC` (523→345, under 350). Do not vanity-split `routers/merchants.py`. Did not grow `driver_service.py` or `driver360_service.py`.

**Wave 31 thin router (2026-09-15):** Admin invoice generate/resend, assist decide/playbook body parse, and PDF required-or-404 live in `AdminOrdersService`. `routers/admin/orders.py` dropped from `_LEGACY_ROUTER_LOC` (581→329, under 350). Do not vanity-split `routers/merchants.py`. Did not grow `finance_service.py` or `order_assist_service.py`.

**Wave 32 thin router (2026-09-15):** Admin merchant pricing merge lives in `merchant_org.merge_pricing_config`; the pricing tab view lives in `rate_card_view.admin_pricing_view`. Create+onboarding, complete-onboarding, subsidiaries, and CRM contract-link compose live in `merchant_org`. `routers/merchants.py` stayed one HTTP surface (853→590); `_LEGACY_ROUTER_LOC` shrunk. Did not grow `merchant_service.py` or `merchant360_service.py`.

**Wave 33 thin router (2026-09-15):** Admin privacy lookup+erasure lives in `MerchantPrivacyService.status_for_id` / `execute_for_id`. Org seat+profile/billing/contacts and CRM timeline/activities/contracts/tasks compose live in `merchant_org`. `routers/merchants.py` stayed one HTTP surface (590→556); `_LEGACY_ROUTER_LOC` shrunk. Did not grow `merchant_service.py` or `merchant360_service.py`.

**Wave 34 thin router (2026-09-16):** Admin write-then-360 compose lives in `merchant_org.after_admin_write`. Terms/coverage/tax/preferred-vehicle mash-up lives in `merchant_org.apply_merchant_terms` (commit stays on `AdminMerchantService`). `routers/merchants.py` stayed one HTTP surface (556→555); `_LEGACY_ROUTER_LOC` shrunk. `merchant_service.py` 827→693; `_LEGACY_ENGINE_SERVICE_LOC` shrunk. Did not grow `merchant360_service.py`.

**Wave 35 thin router (2026-09-16):** D-25 portal keyed driver-doc compose lives in `admin_engine/driver_documents.py`. `driver_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (580→498, under 500). Did not vanity-split `routers/merchants.py`. Did not grow `driver360_service.py`.

**Wave 36 thin router (2026-09-16):** Merchant billing overview (AR + remittance pack + headroom) lives in `billing_pack.overview_payload`. `billing_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (511→454, under 500). Did not vanity-split `routers/merchants.py` or `shopify_service.py`. Did not grow `finance_service.py`.

**Wave 37 thin router (2026-09-16):** Capacity-first vehicle recommendation (M-23) lives in `coverage.recommend_vehicle`. `booking_flow_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (534→490, under 500). Did not vanity-split `routers/merchants.py`. Did not grow `tracking_service.py`.

**Wave 38 thin router (2026-09-16):** Admin booking-draft list/detail row compose (payment + merchant + abandonment) lives in `booking_draft_admin_rows`. `booking_draft_admin_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (545→487, under 500). Did not vanity-split `routers/merchants.py`. Did not grow `booking_draft_service.py`.

**Wave 39 thin router (2026-09-16):** Merchant order board (dashboard counts, 360 sanitize, bulk, timeline) lives in `orders_board`. `orders_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (551→394, under 500). Did not vanity-split `routers/merchants.py`. Did not grow `tracking_service.py`.

**Wave 40 thin router (2026-09-16):** Driver 360 metrics/row/AI/incidents/analytics/timeline live in `driver360_board`. Billing snapshot stays on the service. `driver360_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (570→231, under 500). Did not vanity-split `routers/merchants.py`. Did not grow `finance_service.py`.

**Wave 41 thin router (2026-09-16):** Order-assist propose catalog (assign, exception, late/money, playbooks) lives in `order_assist_proposals`. Execute/notify/invoice stay on the service. `order_assist_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (598→364, under 500). Did not vanity-split `routers/merchants.py`.

**Wave 42 thin router (2026-09-16):** Merchant tracking views (snapshot sanitize, history, geofences, ETA cache) live in `tracking_views`. Fleetbase fetch + Maps ETA stay on the service. `tracking_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (599→342, under 500). Did not vanity-split `routers/merchants.py`. Did not add a PorterChain VROOM client.

**Wave 43 thin router (2026-09-16):** Merchant 360 row/metrics/onboarding/analytics live in `merchant360_board`. Branding, coverage, tax/legal, and AR cents are passed in so the sibling does not import `merchant_engine` or `billing_engine`. `merchant360_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (753→265, under 500). Did not vanity-split `routers/merchants.py`. Did not grow `finance_service.py`.

**Wave 44 thin router (2026-09-16):** Admin merchant close/convert/approve/suspend/onboarding/ops-invoice compose lives in `merchant_lifecycle`. Commits stay on `AdminMerchantService`. `merchant_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (693→482, under 500). Did not vanity-split `routers/merchants.py`, `settings_service.py`, or `shopify_service.py`.

**Wave 45 thin router (2026-09-16):** Admin finance dashboard, collections, reports, GL export, and payment-page compose live in `finance_board`. Invoice/payment writes, credit notes, and reminders stay on `AdminFinanceService`. `finance_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (718→481, under 500). Did not vanity-split `routers/merchants.py`, `settings_service.py`, or `shopify_service.py`.

**Wave 46 thin router (2026-09-16):** Booking-draft field apply, quote copy, payment lifecycle, and dict view live in `draft_compose`. Transition/expire/restore/cancel stay on `BookingDraftService`. `booking_draft_service.py` dropped from `_LEGACY_ENGINE_SERVICE_LOC` (732→446, under 500). Did not grow `booking_draft_admin_service.py`. Did not vanity-split `routers/merchants.py`.

**Wave 47 cross-engine shrink (2026-09-16):** Retail vehicle catalog lives in `domain/retail_vehicles.py` so quotes and CRM convert do not import `admin_engine`. Stale `profile_service` / `quote_service` upward rows dropped. CRM mixins type against `CrmActor` in `crm_helpers`; remaining CRM→admin edge is `crm_activity` audit. Driver/merchant lookups that still import `admin_engine` stay frozen (`auth_service`, `orders_service`, `privacy`). Did not zero the cross-engine freeze. Did not vanity-split `settings_service.py`, `shopify_service.py`, `schemas_admin.py`, or `routers/merchants.py`.

**Wave 48 cross-engine shrink (2026-09-16):** Merchant activation reads `settings_merchant` via `merchant_engine/config_read` (no `AdminSettingsService`). Close/erasure guards live in `merchant_engine/offboard` so privacy does not import `admin_engine`. Merchant compliance PDFs load drivers via `platform/driver_reads` (writes stay on `admin_engine/driver_lookups`). Remaining upward-admin freeze is `driver_engine/auth_service` Clerk bind. Remaining CRM→admin freeze is `crm_activity` audit. Did not zero the freeze. Did not vanity-split `settings_service.py`, `shopify_service.py`, `schemas_admin.py`, or `routers/merchants.py`.

**Wave 49 cross-engine shrink (2026-09-16):** Driver Clerk bind reads live in `platform/driver_reads`; the write stays on `admin_engine/driver_lookups` and is reached through `auth/driver_identity.bind_clerk_user_id`. CRM staff audit lives in `platform/admin_audit` (write stays on `admin_engine.audit`). `_LEGACY_UPWARD_ADMIN_IMPORTS` is 0. Remaining composition freeze is admin/merchant/fleetbase/support wiring — not mash-up. Did not zero the freeze. Did not vanity-split `settings_service.py`, `shopify_service.py`, `schemas_admin.py`, or `routers/merchants.py`.

**Wave 50 cross-engine shrink (2026-09-16):** Support mixins type against `SupportActor` (same Protocol shape as CRM). Audit goes through `platform/admin_audit`. Claim/ticket event names use `DomainEventType` (not `admin_engine.events`). Invoice status on the ticket row uses `platform/invoice_status` (write/status logic stays in `billing_engine`). `support_engine→admin_engine` is 0. Remaining into-admin freeze is Fleetbase/billing/compliance/notification/order composition. Did not zero the freeze. Did not vanity-split `settings_service.py`, `shopify_service.py`, `schemas_admin.py`, or `routers/merchants.py`.

**Wave 51 notification ownership (2026-09-18):** Admin notification center ops live in `notification_engine/admin_service.py` (`NotificationAdminService`). Router `notifications_admin.py` + diagnostics call the engine SoT. Ops retry is `NotificationEngine.requeue`. Removed `admin_engine/notification_admin_service.py` (and its booking/notification cross-engine allowlist rows). Remaining into-admin freeze is Fleetbase/billing/compliance/order composition plus thin diagnostics→notification probes. Did not vanity-split `settings_service.py`, `shopify_service.py`, `schemas_admin.py`, or `routers/merchants.py`.

**Wave 51b notification delivery (2026-09-18):** `emit_event` defers bus publish until SQLAlchemy `after_commit` (hydrate-safe; rollbacks never fan out). `notification.sent` is audit-only (`publish=False`) so it no longer floods Redis Streams. EventBus `STREAM_READ_COUNT` 1→25. Stale queued email/SMS/push are re-enqueued by `sweep_notification_retries`. Routine booking/payment/order-created staff in_app fanout removed (ops noise). Confirmation payloads include customer/merchant identity on `ORDER_CREATED`/`ORDER_BOOKED`.

**Wave 51c worker drain (2026-09-18):** mode=all no longer BRPOPs empty queues (Redis timeout=0 blocks forever; empty-queue BRPOP starved the event consumer ~8s+/loop). Queues use non-blocking `LPOP`; event bus bursts up to 50 msgs/loop. Local lag began falling (~700 msgs/10s) after restart.

**Wave 51d push hygiene (2026-09-18):** `NotificationEngine.dispatch` skips push when the recipient has no active FCM device (admin high/critical still queues for email fallback). Sweeper defers doomed no-device queued push as `push_token_required`. Stream lag reached 0; email sent backlog clearing via Mailpit.

**Wave 51e notification cleanup (2026-09-18):** Deleted dead `booking_engine/notification_handler.py` + `notification_service.py` and retired `porterchain_services.notifications` from the gateway registry. Routine lifecycle staff in_app fanout removed (assign/accept/pickup/deliver/POD/invoice/terminal tracking); staff inbox kept for cancel, reject, claims/support, exceptions, SLA, security, and driver alerts.

**Wave 52 website–admin bond (2026-09-18):** Blog rows are owned by `content_engine.BlogService`. `/v1/admin/blog` and `/v1/public/blog` are the only HTTP wires. The public router does not import `admin_engine`. The website reads `/v1/public/blog` only (no markdown merge). Retail booking leads go through `LeadIngestService.ingest`. Handshake: `scripts/verify_blog_cms.py`. Did not vanity-split `schemas_admin.py`, `settings_service.py`, or `routers/merchants.py`.

**CI holes:** Stripe SDK is `sdk.py` only. Spatial math banned in ops. Census frozen. Vendor leaves (OSRM URL, VROOM, mobile Fleetbase) frozen in Wave 4. Model ownership frozen in Waves 5–13. Thin-router logic allowlist is 0 (Waves 14–21). Thin-router LOC allowlist shrinks in Waves 22–34. Engine-service LOC allowlist shrinks in Waves 35–46. Quote/CRM upward-admin mash-up shrinks in Wave 47. Merchant activation/privacy/orders upward-admin mash-up shrinks in Wave 48. Driver Clerk bind and CRM audit upward-admin mash-up shrinks in Wave 49 (`_LEGACY_UPWARD_ADMIN_IMPORTS` is 0). Support audit/actor/events upward-admin mash-up shrinks in Wave 50 (`support_engine→admin_engine` is 0). Notification admin center ownership moves to `notification_engine` in Wave 51. Inline router `db.query` is 0.

Fat-but-coherent (do not vanity-split): `schemas_admin.py`, `settings_service.py`, `shopify_service.py`, `routers/merchants.py` HTTP surface.

Graphify hubs (connectivity, not always the bug): `Settings`, `MerchantContext`, `Order`, `AdminContext`, `require_module`, `Merchant`, `get_merchant_context`.

---

## Folder law

- Vendor I/O in adapters (`MapsService`, Stripe `sdk.py`, `auth/clerk_*`, FCM).
- Commercial logic in `*_engine/*_service.py`.
- Routers: auth + `require_module` + one service call. No new inline `BaseModel`.
- Spatial math in admin ops is banned (`scripts/verify_no_ops_spatial_math.py`).
- New ORM writes belong in the owning `*_engine` (`scripts/verify_model_ownership.py`).
- No vendor dispatch HTTP / Stripe SDK / UI `:8000` / public OSRM defaults guarded by `scripts/verify_architecture_boundaries.py` + `scripts/verify_vendor_leaves.py`.

---

## Rejected overlays

Do not create `core/`, `backend/`, or `personas/`. Those names already live under `apps/`, `services/`, and `*_engine`. A parallel tree is a second request path and undoes Waves 1–50. Do not spray `// @ARCHITECTURE.md (325-340)` (or `# @ARCHITECTURE.md (325-340)`) on files — those lines are the sensor pipeline, not a functional boundary. Folder law above is the boundary.

| Prompt path                                    | Live path                                                                            | Do not                                    |
| ---------------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------- |
| `core/domain/models.py`                        | `*_models.py` under `apps/api/src/porterchain_api/`                                  | Restore deleted `models.py`               |
| `core/domain/types.ts`                         | Portal `lib/api.ts` + shared packages                                                | One TS dump across personas               |
| `core/blackbox/fleetbase.py`                   | **Removed** — day plan is `dispatch_engine` (OR-Tools + Valhalla)                    | Restore Fleetbase adapter                 |
| `core/blackbox/clerk.py`                       | `apps/api/src/porterchain_api/auth/clerk.py`                                         | Ad-hoc Clerk env names                    |
| `core/blackbox/firebase.py`                    | `notification_engine` (FCM only)                                                     | Firebase Auth                             |
| `core/blackbox/routing.py`                     | `MapsService` + `dispatch_engine/sequencer.py`                                       | PorterChain VROOM client                  |
| `core/blackbox/google_maps.py` Distance Matrix | **Illegal**                                                                          | Google distance / ETA / matrix / geometry |
| `core/blackbox/communications.py`              | `notification_engine`                                                                | Second mail/FCM engine                    |
| `backend/api/v1/auth.py` + `router.py`         | `routers/auth.py` + census prefixes                                                  | One fat `router.py`                       |
| `backend/config/environments.py`               | `config.py` `Settings`                                                               | Second Settings class                     |
| `backend/config/pipeline_ci.yml`               | `.github/workflows` + `pnpm validate:ci` (`scripts/run-ci-gates.sh` / `verify_*.py`) | Sandbox-replace CI                        |
| `personas/admin`                               | `apps/admin` `:3002` → `/v1/admin`                                                   |                                           |
| `personas/merchant`                            | `apps/merchant-portal` `:3001` → `/v1/merchant`                                      |                                           |
| `personas/customer`                            | `apps/customer` `:3004` + website `:3000`                                            |                                           |
| `personas/driver`                              | `apps/driver-portal` BFF `:3003` + `apps/mobile-driver`                              | Unify web BFF with mobile Bearer          |

Fat-but-coherent (do not vanity-split): `schemas_admin.py`, `settings_service.py`, `shopify_service.py`, `routers/merchants.py`. Next isolation, if asked, is Wave 51 — Settings hub + remaining composition freeze — not a folder rewrite.

---

## Agent sensors (mandatory pipeline)

SSOT: [`.cursor/rules/graph-tools.mdc`](.cursor/rules/graph-tools.mdc) · [AGENTS.md](AGENTS.md). One sensor per session. Use the living markdown below for organize / align / cleanup / implement. Do not restore the deleted novel. Do not follow `apps/api/.venv/**` or other vendor licenses.

```
mashed-up code
        │ Step 1
   GRAPHIFY CLI  (Graphify-Labs/graphify)     → this file + FastAPI↔PHP map
        │ Steps 2–3
   CODEGRAPH MCP (@colbymchenry/codegraph)    → Pydantic / ORM / Valhalla / OSRM
        │ Steps 4–6
   RIPWIRE CLI   (redhat-et/ripwire)          → thin routers, Stripe/Clerk adapters
```

Do not install `codegraph-ai/CodeGraph`. Do not wire Graphify or Ripwire into `.cursor/mcp.json`. After a folder-graph change: one `graphify update .`.

### Align — why we exist, what we ship

| File                                                                             | Follow for                                           |
| -------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [docs/PORTERCHAIN_CHARTER.md](docs/PORTERCHAIN_CHARTER.md)                       | Identity, 10-customer gate, Phase 1 copy             |
| [`.cursor/rules/porterchain-charter.mdc`](.cursor/rules/porterchain-charter.mdc) | Same gate on every agent turn                        |
| [`.cursor/rules/porterchain-stack.mdc`](.cursor/rules/porterchain-stack.mdc)     | Node / Python / Next / Expo / Postgres / Redis pins  |
| [`.cursor/rules/dependency-freeze.mdc`](.cursor/rules/dependency-freeze.mdc)     | Frontend freeze, image pins, no SocketCluster in web |

`docs/WEBSITE_GTM_EXECUTION_PLAN.md` is not on disk. Missing GTM markdown is not a license to invent Phase 3 copy.

### Organize — where code lives

| File                                                                                                 | Follow for                                                                                       |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| [ARCHITECTURE.md](ARCHITECTURE.md)                                                                   | This trunk: request path, folder law, rejected overlays, census                                  |
| [AGENTS.md](AGENTS.md)                                                                               | Sensor order (Graphify → CodeGraph → Ripwire)                                                    |
| [`.cursor/rules/graph-tools.mdc`](.cursor/rules/graph-tools.mdc)                                     | Sensor pins; one sensor per session                                                              |
| [`.cursor/rules/graphify.mdc`](.cursor/rules/graphify.mdc)                                           | Graphify query/path/explain only (overridden by graph-tools for daily work)                      |
| [`.cursor/skills/porterchain-graph-tools/SKILL.md`](.cursor/skills/porterchain-graph-tools/SKILL.md) | When to open which sensor                                                                        |
| `graphify-out/GRAPH_REPORT.md`                                                                       | Generated map (17 616 nodes). Dated copies under `graphify-out/2026-09-*` are snapshots, not law |

### Implement — how to build a slice or the whole

| File                                                                                   | Follow for                                           |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [`.cursor/rules/fleetbase-first-policy.mdc`](.cursor/rules/fleetbase-first-policy.mdc) | PorterChain owns dispatch; Valhalla before Google    |
| [INTEGRATIONS.md](INTEGRATIONS.md)                                                     | Vendor registry (`integrations.yaml`)                |
| [apps/api/README.md](apps/api/README.md)                                               | OpenAPI snapshot + `pnpm docs:openapi`               |
| [docs/api/PARTNER_GUIDE.md](docs/api/PARTNER_GUIDE.md)                                 | `/v1/merchant-api` API-key surface                   |
| [infrastructure/docker/osrm/data/README.md](infrastructure/docker/osrm/data/README.md) | Local OSRM GTA ±150 km extract (not committed graph) |

Diagrams (not markdown law): `docs/architecture/mermaid/*.mmd` — start at [system_architecture.mmd](docs/architecture/mermaid/system_architecture.mmd). Do not restore PlantUML duplicates.

### Cleanup — what not to grow or restore

| File                                                                         | Follow for                                    |
| ---------------------------------------------------------------------------- | --------------------------------------------- |
| [docs/POINTER_STUB_INDEX.md](docs/POINTER_STUB_INDEX.md)                     | Root POINTER stubs ≤5; living CANONICAL set   |
| [docs/archive/pointer-stubs/README.md](docs/archive/pointer-stubs/README.md) | Overflow pointers live here, not at repo root |

Guards (Python, not markdown): `scripts/verify_doc_pointer_stubs.py`, `scripts/verify_doc_governance.py`, `scripts/verify_architecture_boundaries.py`, `scripts/verify_vendor_leaves.py`.

Do not recreate deleted vendor trees or the old dispatch bond. Generated native `ios`/`android` folders and `.next` caches are local-only.

---

## Related

The tables above are the follow-list. Root CANONICAL: this file · [docs/PORTERCHAIN_CHARTER.md](docs/PORTERCHAIN_CHARTER.md).
