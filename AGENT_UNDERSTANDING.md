# PorterChain (PCD) — Agent Understanding

**Author:** PorterChain coding agent
**Date:** 2026-08-09
**Basis:** Live code reading (services, engines, routers, compose, migrations) + canonical docs (`masterrule.md`, `README.md`, `EVENT_BUS.md`, `FLEETBASE_ADAPTER_ARCHITECTURE.md`, `DOMAIN_MODEL.md`, `ORDER_LIFECYCLE.md`, `DATABASE_ARCHITECTURE.md`, `TECH_STACK.md`, `INTEGRATIONS.md`).
**Note:** This is a synthesis doc written to prove comprehension of the codebase — not a canonical spec. When in doubt, trust `masterrule.md` and the code.

---

## 1. What this project is

**PorterChain (PCD) is a Transportation Capacity Network.** It sells capacity (vehicle + driver), and the software is the network engine — not a SKU. The system optimizes utilization, trust, automation, and merchant/driver retention.

Concretely, the repo is a **pnpm/Turbo monorepo** containing:

- **Nine user-facing apps**: public website (`:3000`), merchant portal (`:3001`), admin/control tower (`:3002`), driver web (`:3003`), customer portal (`:3004`), two Expo mobile shells, the FastAPI backend (`:8001`), and a headless async worker.
- **An upstream Fleetbase clone** (`apps/fleetbase/`) used strictly as the logistics execution engine — dispatch, GPS, routes, POD.
- **Five internal Python service packages** (adapter, pricing, driver platform, event bus, composition root).
- **~40 canonical markdown docs** that form the architecture contract (`masterrule.md` is the SSOT).

The commercial moat lives in Porterchain's own Postgres (PostgreSQL 18) and FastAPI layer: **pricing, quoting, booking, Stripe billing, CRM, claims, merchant onboarding, driver earnings, RBAC/audit**. The execution layer (who picks up what, live GPS, route progress, proof of delivery) belongs to **Fleetbase**, reached only through a single adapter.

---

## 2. The locked topology (the #1 rule)

`masterrule.md` §1 pins this topology. Everything in the codebase bends to it:

```
Website (:3000) → Booking/Customer portal → Merchant portal (:3001) → Admin (:3002)
        ↓
Porterchain API (FastAPI :8001)  ← "Logistics Orchestrator"
        ↓
Pricing / Billing / Notification engines (modules)
        ↓
Internal Event Bus → Fleetbase Adapter → Fleetbase Core (dispatch, GPS, routes, tracking, POD)
        ↓
Driver mobile app
```

Two hard rules emerge from this and are enforced by CI validators (`scripts/verify_*.py`):

1. **Fleetbase-first**: For any ops/logistics feature (dispatch, drivers, vehicles, GPS, geofences, POD, live maps), use Fleetbase via the adapter. Never rebuild a dispatch board, GPS ping store, geofence engine, or route optimizer in Porterchain code. (There is even a `pnpm validate:fleetbase-first` script running `verify_no_ops_spatial_math.py`.)
2. **Single integration path**: No frontend and no router calls Fleetbase HTTP directly. All Fleetbase traffic goes through `services/fleetbase-adapter/`.

---

## 3. Monorepo layout (what each folder is)

| Path                                           | Role                                                                                            |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `website/`                                     | Next.js 16 public site — marketing, SEO, booking entry, tracking, blog CMS                      |
| `apps/merchant-portal/`                        | B2B dashboard — bookings, bulk import, recipients, API keys, webhooks, NET billing              |
| `apps/admin/`                                  | Business admin / Control Tower — CRM, finance, orders 360, drivers, claims, diagnostics         |
| `apps/driver-portal/`                          | Driver web dashboard (BFF → `/driver-api/v1/*`)                                                 |
| `apps/customer/`                               | Retail customer dashboard                                                                       |
| `apps/api/`                                    | FastAPI orchestrator `:8001` — all business logic lives in `*_engine/` packages                 |
| `apps/worker/`                                 | Headless async worker — event bus consumer + task queue drain (no HTTP port)                    |
| `apps/mobile-driver/`, `apps/mobile-customer/` | Expo SDK 57 shells (drivers = execution-first)                                                  |
| `apps/fleetbase/`                              | Upstream Fleetbase clone (Laravel/PHP + Ember console) — **do not modify**                      |
| `packages/*`                                   | Shared TS: `ui`, `types`, `auth`, `events`, `queue`, `config`, `maps`, `mobile-theme`, `shared` |
| `services/fleetbase-adapter/`                  | The **sole** Fleetbase boundary (Python package `porterchain_fleetbase_adapter`)                |
| `services/pricing-engine/`                     | `porterchain_pricing` — pricing library (B2C + B2B, contracts, promos, tax, zones)              |
| `services/event-bus/`                          | `porterchain_event_bus` — publish/subscribe, handlers, idempotency, DLQ, versioning             |
| `services/driver-platform/`                    | `porterchain_driver` — reusable driver domain services                                          |
| `services/python/`                             | `porterchain_services` — composition root (gateway, stripe, maps, notifications…)               |
| `shared/python/`                               | `porterchain_shared` — config, events catalog, queue names, redis client                        |
| `infrastructure/`                              | Docker compose, Fleetbase overlay, deploy scripts, nginx, valhalla                              |
| `env/`                                         | Environment templates (Clerk, secrets, etc.)                                                    |
| `scripts/`                                     | ~145 CI/validation scripts — heavy governance discipline                                        |

---

## 4. The backend: Porterchain API (`:8001`)

FastAPI app assembled in `apps/api/src/porterchain_api/main.py`. It wires ~30 routers, CORS, request-ID and rate-limit middleware, a merchant-API gateway middleware, observability (Sentry + Prometheus `/metrics`), health endpoints, and error envelopes.

### Engine modules (application services home)

| Engine                  | Responsibility                                                                  |
| ----------------------- | ------------------------------------------------------------------------------- |
| `booking_engine/`       | Quote → booking draft → booking → payment → confirmation → tracking (retail)    |
| `merchant_engine/`      | B2B lifecycle, billing, bulk/CSV import, standing orders, integrations          |
| `admin_engine/`         | CRM, finance, claims, order 360, control tower, diagnostics, RBAC, settings     |
| `fleetbase_engine/`     | Outbound sync jobs, inbound webhook processing, retry queue, status translation |
| `driver_engine/`        | Driver auth, Fleetbase bridge, offline executor                                 |
| `billing_engine/`       | Settlement ledger, merchant net-terms billing, driver finance                   |
| `notification_engine/`  | Templates, delivery, email/SMS/push queueing, realtime hub                      |
| `pricing_engine/`       | Bridge into `services/pricing-engine`                                           |
| `order_engine/`         | Platform order views (dashboard, detail, enriched, reports)                     |
| `intelligence_engine/`  | Phase 2 gated — dispatch scoring, ETA, copilot, forecast                        |
| `collaboration_engine/` | Full CRM (companies, contacts, leads, deals, quotations, contracts, activities) |
| `support_engine/`       | Support tickets + claims lifecycle                                              |
| `analytics_engine/`     | ETL service                                                                     |
| `compliance_engine/`    | Privacy/compliance dossier                                                      |
| `oauth_engine/`         | Partner OAuth (`authorization_code` + `client_credentials`)                     |
| `gateway_engine/`       | Merchant API gateway (scoped API keys, rate limits)                             |

### The layered pattern (strictly enforced)

- **Routers are thin controllers**: authenticate → validate (Pydantic) → call one service → return response. No SQL, no pricing math, no Fleetbase calls in routers.
- **Services own business rules**: state machines, pricing decisions, orchestration, and event emission via `emit_event()`.
- **Repositories** (e.g. `booking_engine/repositories/quote_repository.py`) are pure persistence.
- **Adapters** map DTOs and translate external APIs only.
- UI never holds business truth — booking drafts/quotes/payments/order state are **DB-persisted** (server-side truth). The website's local quote preview is estimation only; the server re-prices before payment.

---

## 5. The order lifecycle (canonical state machine)

Defined in `ORDER_LIFECYCLE.md` and implemented in `booking_engine/order_transitions.py` + `fleetbase_engine/status_translator.py`.

```
QUOTE → BOOKING_PENDING → PAYMENT_PENDING → BOOKED → DISPATCH_READY
  → DRIVER_ASSIGNED → DRIVER_ACCEPTED → DRIVER_EN_ROUTE → AT_PICKUP
  → PICKED_UP → IN_TRANSIT → AT_DESTINATION → DELIVERED → POD_COMPLETED
  → INVOICED → CLOSED
```

- **Porterchain owns the canonical state.** Fleetbase operational status maps _in_ via the dispatch bridge (webhooks → `status_translator.py`). State transitions are append-only in the `domain_events` log.
- Exception paths: `FAILED`, `RETURN_TO_SENDER`, `DAMAGED`, `LOST`, `CLAIM_OPEN`, `REFUNDED`, `CANCELLED`.
- Merchant orders **skip** the retail payment states when on NET terms (e.g. `NET_30`): submit → `BOOKED` directly. Per-order Stripe is optional.
- Who can trigger transitions is table-locked: drivers accept and advance execution; dispatchers assign; the board marks exceptions only (Admin does **not** fake Accept→Delivered — that lives in Fleetbase/driver).

---

## 6. Event-driven backbone (Redis Streams + worker)

The system is event-driven (`EVENT_BUS.md`). Key mechanics:

- `emit_event()` (in `booking_engine/_core.py`) → writes a `DomainEvent` row (immutable audit) + publishes an envelope to Redis Stream `porterchain:events`.
- Envelope shape: `{event_id, event_type, occurred_at, aggregate_type, aggregate_id, correlation_id, actor, payload, version}`.
- `apps/worker/run.py` loop: `consume_once()` (consumer group `porterchain-workers`) → drain task queues → periodic drains for Fleetbase retry queue, draft reconciliation, standing orders, notification retries.
- Failure handling: exponential backoff retry (`RetryPolicy`, 5 attempts, 2s→16s) then **DLQ** (`porterchain:events:dlq`). Idempotency markers prevent double-processing.
- Event types are catalogued in **two mirrored sources**: `shared/python/porterchain_shared/events/catalog.py` and `packages/events/src/catalog.ts` (CI checks parity).
- **Rule:** modules never import each other's services at call sites — they publish events; handlers react (e.g. `order.dispatch_ready` → Fleetbase sync; `order.pod_completed` → auto-invoice + email).

---

## 7. Fleetbase integration (adapter-only, version-pinned)

- `services/fleetbase-adapter/porterchain_fleetbase_adapter/` contains: `FleetbaseClient` (HTTP + auth + retry), domain services (orders, drivers, vehicles, dispatch, tracking, routes, manifests, POD), `FleetbaseSsoClient` (admin console SSO), `WebhookService` (HMAC verify), `EventTranslator` (Fleetbase event → Porterchain state), and the `FleetbaseAdapter` facade.
- **Never store** pricing, Stripe IDs, or contract terms in Fleetbase payloads — only correlation (`meta.porterchain_order_id`, `internal_id`).
- Runtime is pinned by Docker digest, not tags: `fleetbase/fleetbase-api@sha256:24c0fbe5e465…` (core-api 1.6.55, fleetops-api 0.6.59). The host `apps/fleetbase` git clone tag is v0.7.40 — docs warn its `composer.lock` is not the running API version.
- Inbound: Fleetbase webhooks hit `POST /webhooks/fleetbase` → `fleetbase_engine/webhook_processor.py`.
- Outbound: `fleetbase_engine/booking_sync_service.py` syncs orders/drivers/vehicles after payment; failures go to the retry queue.

---

## 8. Pricing & routing (Porterchain owns money)

- **Fleetbase never calculates prices** — that is a hard rule. All pricing lives in `services/pricing-engine` (`porterchain_pricing`).
- Pricing inputs (B2C): pickup/dropoff distance, vehicle class (sedan → 20ft box truck), weight/dimensions, declared value, rush vs scheduled, extra stops, fuel surcharge, HST, min charge, promos. B2B adds contracts, lanes, zones, flat rates, volume discounts, weekend multipliers, custom JSON.
- GTA rate matrix in `porterchain_pricing/gta_rate`: vehicle base covers 20 km, extra-km rates, $20 extra pickups / $15 extra drops, downtown $25 / Markham & North York $15 surcharges.
- **Routing providers** (money-path only, server-side): **Valhalla** (`:8002`) is primary, **OSRM** is the fallback. `services/routing.py → resolve_route_distance()`. Google Maps is explicitly _not_ a routing engine — only Places autocomplete, map tiles, optional geocode fallback. No haversine hand-rolls in admin/ops routers (`verify_no_ops_spatial_math.py` guards this).
- Price breakdown is itemized (`base`, `distance`, `vehicle`, `weight`, `fuel`, `stops`, `traffic`, `margin`) — the website's quote engine mirrors this breakdown in UI.

---

## 9. Driver platform (extends, doesn't replace Fleetbase)

`services/driver-platform/porterchain_driver/` + `apps/api/.../driver_engine/` + `/driver-api/v1/*` (~75 handlers in `routers/driver.py`):

- Porterchain owns the driver _experience_: earnings, wallet, compliance, POD capture, training, support, emergency.
- Fleetbase owns execution: dispatch, GPS, routes.
- Services: dashboard, jobs, stops, navigation, shift, availability (online/offline, accept/reject), POD (photo/signature/OTP), location, earnings/finance, communications, offline queue+sync, push, emergency.
- Driver data in Postgres: `drivers`, `driver_wallet_transactions`, `driver_location_pings`, `driver_offline_actions`, `driver_stop_meta`, `driver_shifts`.
- Auth is Porterchain JWT (Clerk-backed); dev bypass via `X-Driver-Id` / email paths when `CLERK_DEV_BYPASS=true` and `APP_ENV=local`. Local API also accepts Bearer `dev`.

---

## 10. Identity & auth

- **Clerk is the _only_ IdP** for Porterchain users (`AUTHENTICATION_ARCHITECTURE.md`). No Supabase, no Twilio OTP, no custom OTP (those were explicitly removed).
- Mode: `CLERK_MODE=platform_driver` — a Platform triad (customer, merchant, website) + a Driver triad (driver portal/mobile). Admin uses the **PorterChain staff IdP** (no Clerk) with WebAuthn + SSO; `unified` and `enterprise` modes are retired.
- The API verifies Clerk JWTs (`auth/clerk.py`), syncs users into Postgres (`porterchain_users`, `identity_links`, portal link tables), and does RBAC per portal (`admin_engine/rbac.py`, `merchant_engine/rbac.py`, SpiceDB-style `authz/` with `schema.zed`).
- Local bypass: Bearer `dev` when `CLERK_DEV_BYPASS=true`.
- Webhook: Clerk events → `auth/clerk_webhook_service.py` (idempotent via `clerk_webhook_events` table).

---

## 11. Data layer

| Store                | Engine               | Owner               | Access                               |
| -------------------- | -------------------- | ------------------- | ------------------------------------ |
| Porterchain DB       | PostgreSQL 18        | Porterchain API     | SQLAlchemy 2 + Alembic only          |
| Fleetbase DB         | MySQL 8              | Fleetbase (Laravel) | HTTP adapter only — never direct SQL |
| Redis 8 / Valkey 8.1 | cache/queues/streams | shared infra        | redis client + worker                |

- ~68 Postgres tables across `*_models.py` modules (booking, merchant, admin, crm, driver, fleetbase sync, identity, invitations, website content, etc.). Alembic migrations only — `create_all` is blocked, SQLite is blocked.
- 35+ Alembic revisions in `apps/api/alembic/versions/`.
- **Porterchain mirrors** `orders`, `drivers`, `vehicles` in Postgres; execution state syncs via the adapter.
- Read-replica path planned (`DATABASE_URL_REPLICA`) for analytics; primary is used at Phase A scale.

---

## 12. Billing & payments

- **Stripe config/webhooks are frozen** — checkout creation and webhook parsing live in `services/stripe_service.py`; payment lifecycle in `booking_engine/payment_service.py` and `booking_engine/stripe_webhook_service.py` with idempotency (`stripe_webhook_events` table).
- Retail: checkout session → `payment.succeeded` → order created/confirmed.
- Merchant: NET terms invoicing via `billing_engine/merchant_service.py` + `merchant_engine/billing_service.py`; driver payouts in `billing_engine/driver_finance_service.py`.
- Auto-invoice after POD completion (`InvoiceService.finalize_after_pod` on `order.pod_completed`).

---

## 13. Integrations (live inventory)

| Integration             | Status        | Role                                    |
| ----------------------- | ------------- | --------------------------------------- |
| Fleetbase               | ✅ adapter    | dispatch, GPS, POD                      |
| Google Maps             | ✅ UI-only    | autocomplete, map tiles, server geocode |
| Valhalla                | ✅ primary    | routing `:8002`                         |
| OSRM                    | ✅ fallback   | distance/polyline                       |
| Stripe                  | ✅ frozen     | payments                                |
| Clerk                   | ✅ live       | identity                                |
| Firebase FCM            | ⚠️ partial    | push (prod creds needed)                |
| SMTP (Zoho/Mailpit)     | ✅            | transactional email                     |
| Merchant webhooks       | ✅            | HMAC outbound fan-out                   |
| Merchant API keys       | ✅            | `/v1/merchant-api` programmatic         |
| OAuth                   | ✅            | partner flows                           |
| NetSuite/Shopify/Zapier | integrations/ | adapters (Zoho calendar in API)         |

---

## 14. DevOps & infra

- Docker Compose profiles: `core` (Postgres, Redis, Mailpit), `routing` (Valhalla, OSRM), `fleetbase` (MySQL, Valkey, SocketCluster, Laravel queue/scheduler/app, nginx httpd, Ember console).
- Fleetbase stack merged from three compose files (upstream → installer → Porterchain overlay). Container names prefixed `porterchain-fleetbase-*`. All images pinned by **digest, never `:latest`**.
- Deploy: DigitalOcean droplet + Caddy, Doppler secrets, `bootstrap-droplet.sh` / `harden-droplet.sh`, prod compose. Admin production `pnpm validate:p0:prod` smoke tests.
- **Governance is heavy**: ~145 validation scripts wired into `package.json` (`validate:*` targets), Husky precommit, Trivy scans, `verify_*` gates for architecture boundaries, model ownership, lockfile freshness, golden rules, security posture. This is a deliberate "CI as architecture enforcement" culture.

---

## 15. Current state of the repo (as of 2026-08-09)

- Branch: **`feature/crm`** (off `main`). Recent commits: CRM lead hard-delete, home-hero/copy cleanups, WhatsApp + sign-in nav, Trivy fixes, Clerk Platform go-live, event-bus drain, fleetbase host deferral.
- Working tree has a large in-flight change set (544 files, +38k/−40k) — many deleted root `*_AUDIT.md`/`*_REPORT.md` files and moved/rewritten website `lib/quote/*` modules, consistent with the docs simplification program (archive historical audits, collapse quote engine into server-side pricing).
- Website quote engine code was recently de-duplicated toward the server (`services/routing.py`, `porterchain_pricing`).

---

## 16. What an engineer must never do here

1. Call Fleetbase HTTP from a frontend or router — **adapter only**.
2. Rebuild dispatch boards, GPS stores, geofences, or route optimizers — **Fleetbase-first**.
3. Put pricing/Stripe/business rules in UI, routers, models, or the adapter — **engines own them**.
4. Use Google for distance/ETA/matrix/nearest-driver/optimization — **Valhalla/OSRM**.
5. Change Stripe config/webhooks or upgrade next/react/typescript/eslint without approval.
6. Use `:latest` images, `create_all`, SQLite, or direct MySQL access to Fleetbase.
7. Touch `apps/fleetbase/` (upstream clone) — extend only via adapter/extension points.

---

## 17. TL;DR (one paragraph)

PorterChain is a **transportation capacity network** where the commercial layer (quotes, pricing, booking, Stripe, CRM, merchant/driver retention, RBAC) is owned end-to-end by a FastAPI "logistics orchestrator" backed by PostgreSQL 18, while **Fleetbase is used (never forked) purely as the logistics execution engine** through one adapter package behind a Redis Streams event bus consumed by a headless Python worker. Portals are Next.js 16 + React 19 + Clerk; routing for money is Valhalla/OSRM only; the whole monorepo is governed by `masterrule.md` and enforced by ~145 CI validators. The product's defensibility is the data + pricing/contract moat, not the dispatch UI — which is exactly why the architecture rules protect the Fleetbase boundary so aggressively.
