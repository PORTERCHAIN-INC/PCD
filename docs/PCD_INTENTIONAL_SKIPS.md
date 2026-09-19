# PCD — intentional skips (project-wide)

Items below are **not leftovers / not bugs**. They are policy holds, deferred Phase 2+, Fleetbase-first refusals, freeze allowlists, or parked Fleetbase-max gaps.

**SSOT for all intentional skips** (including driver verification). Thin pointer: [DRIVER_VERIFICATION_INTENTIONAL_SKIPS.md](DRIVER_VERIFICATION_INTENTIONAL_SKIPS.md).

Sensors: Graphify (`ARCHITECTURE.md`, Phase2 / DeferredSite) → CodeGraph CLI explore → Ripwire (`--for` / `--expand` on flags, adapters, SocketCluster).

---

## Driver verification — done vs skip

P0–P3 Ontario driver verification automation is **complete in code** (core landed `7324ee0`). Not leftovers:

Identity (Stripe) · Checkr background · Ontario abstract rules · compliance expiry sweep · Admin auto/manual/rules badges · quality bonus scoring · portal feature-gated CTAs · shared mobile upload helper · `apps/api/.env` flags synced · CT gap scoped (expiry hard-block; abstract rejection is onboarding-only)

Core loop: **upload / attest → provider or rules → `license_verified` / `background_check_status` / abstract / expiry revoke → Admin source badges**. Admin approval of `DriverStatus` stays human.

### Still policy (driver)

| Item                                                                                | Why held                                                                  |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Auto-approve `DriverStatus` / `DriverStatus.APPROVED` from Identity/Checkr webhooks | Network trust — ops still authorize who can work                          |
| In-house OCR / forgery detector for Ontario DL                                      | Buy Stripe Identity / Persona; do not rebuild                             |
| Scrape ServiceOntario / MTO without Authorized Requester                            | Privacy + contract; attestation + rules until volume justifies ARIS       |
| Insurance / registration auto-verify via insurer APIs                               | Rare early-stage; keep upload + expiry revoke                             |
| Hard CT exclude on rejected abstract when feature off                               | Onboarding gates when `DRIVER_ABSTRACT_VERIFICATION_ENABLED`; CT does not |

### Intentionally not done (driver)

| Item                                                        | Notes                                                                                                                          |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Mobile Identity / Checkr / Abstract CTAs**                | Web portal only for now; `docsUpload.ts` shared helper is in place for Docs + Onboarding                                       |
| **Live Stripe Identity / Checkr**                           | Need Dashboard products + webhook events: `identity.verification_session.*` on `/webhooks/stripe`, Checkr → `/webhooks/checkr` |
| **MTO Authorized Requester**                                | Abstract is structured attestation + demerit/class/suspension rules — not a government API pull                                |
| **Admin Integration settings UI** (`DRIVER_*` / `CHECKR_*`) | Flags are env-only; no settings-panel toggles                                                                                  |

### Ops flags (driver)

Restart **API + worker** after flag changes (`get_settings` is cached). Examples in `env/api.env.example` / `apps/api/env.example`:

- `DRIVER_IDENTITY_VERIFICATION_ENABLED`
- `DRIVER_BACKGROUND_CHECK_ENABLED` / `CHECKR_MOCK` / `CHECKR_API_KEY`
- `DRIVER_ABSTRACT_VERIFICATION_ENABLED` / `DRIVER_ABSTRACT_MAX_DEMERITS`
- `DRIVER_COMPLIANCE_EXPIRY_SWEEP_ENABLED`

---

## Still policy (intentionally)

| Item                                                                                                | Why held                                                                                                              |
| --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Sell Phase 3 metrics / AI as today’s SKU                                                            | Charter + `ARCHITECTURE.md` root Required                                                                             |
| Rebuild dispatch board / driver online / live GPS SoT / geofences / POD store / VROOM in `*_engine` | Fleetbase-first — Use/wrap only                                                                                       |
| Google Distance Matrix / ETA / route geometry for pricing or dispatch                               | Valhalla → OSRM only; Google = Places + tiles                                                                         |
| Web / mobile SocketCluster SDK; Fleetbase `positions/replay`                                        | Adapter polls REST positions; web never consumes SC                                                                   |
| Unify driver web BFF (`:3003`) with mobile Bearer                                                   | Two auth paths on purpose (`ARCHITECTURE.md` rejected overlays)                                                       |
| Merchants / retail on the Fleetbase Ember console                                                   | Ops surface is PorterChain admin. Bond is the Fleetbase API via the adapter.                                          |
| Admin UI launchers for the Fleetbase Ember console (`Open Fleetbase` SSO)                           | Permanent bond is the API via adapter — PorterChain admin is the ops surface; the Ember console is not a product path |
| Firebase Auth / ad-hoc `ADMIN_CLERK_*` env names                                                    | Clerk triad via `env/clerk.env` + `pnpm clerk:sync`                                                                   |
| Second mail/FCM engine; PorterChain VROOM client                                                    | Leaves stay vendor boxes                                                                                              |
| Restore deleted `models.py` / `core/` / `personas/` overlay trees                                   | Undoes Waves 1–50                                                                                                     |
| Vanity-split fat-but-coherent files                                                                 | `schemas_admin.py`, `settings_service.py`, `shopify_service.py`, `routers/merchants.py` — Wave 51 only if asked       |
| Frontend major bumps (`next` / `react` / Node 26) until ~2026-10                                    | `.cursor/rules/dependency-freeze.mdc`                                                                                 |
| New `*_engine` → other `*_engine` imports outside `_LEGACY_CROSS_ENGINE_IMPORTS`                    | D2 freeze (`verify_d2_contracts.py`)                                                                                  |
| Hard-DELETE merchants (admin or portal)                                                             | Close / convert / reopen only — never invent DELETE                                                                   |
| Ask NIM / ModelGateway `auto_apply=true` or write tools                                             | Propose→confirm only; tools = read/triage admin APIs — **never** Valhalla write, Fleetbase write, or Stripe pay       |
| Admin UI dropdown that flips live stack development ↔ production                                    | Project mode is **boot-time** `APP_ENV` only — Jeff Dean; one click must not unlock `Bearer dev` / Stripe mock        |
| Store project mode in `SystemConfig` / Postgres                                                     | Survives deploys and fights Doppler; SoT is env / Doppler config                                                      |
| Hot-reload `APP_ENV` without process restart                                                        | Clerk JWKS, cookie Domain, bypass gates rebind at boot only                                                           |
| Treat merchant/order `is_sandbox` as platform project mode                                          | Sandbox = commercial traffic label; platform mode = deploy posture                                                    |
| In-process `POST /v1/admin/settings/project-mode` that mutates mode                                 | Always `403 project_mode_immutable`; change via `pnpm mode:set` / Doppler + restart                                   |

---

## Intentionally not done (not bugs)

| Item                                                                | Notes                                                                                                                           |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Phase 2 flags default off**                                       | `PORTERCHAIN_PHASE2_{CRM,AI_DISPATCH,ANALYTICS,INTELLIGENCE}` — masterrule §21.4 until Phase 1 loop is boring                   |
| **Route Center (`route_center`)**                                   | **Retired** — always `False` in `Phase2Flags.as_dict`; Fleetbase/VROOM owns sequencing                                          |
| **`intelligence_engine` / `analytics_engine` product surface**      | Scaffold + `PHASE2_BOUNDARY` only; strategies gated by flags (ADR-010 / §4.1)                                                   |
| **Fleetbase-max GTA150 plan (Phases 0–6 + leftovers)**              | **Complete** — do not reopen for “continue”. Parked only: rows below                                                            |
| **OrderConfig HOS / break windows → VROOM**                         | Probe-then-wrap held until Fleetbase OrderConfig fields are proven live                                                         |
| **Return-to-depot end-of-day**                                      | Not required for early network; Fleetbase depot when ops asks                                                                   |
| **Traffic SoT (live congestion)**                                   | Valhalla `date_time` optional only; no Google traffic as dispatch SoT                                                           |
| **Fleetbase seed / console 401 in CI**                              | Local probe / ops credentials — not a PC feature gap                                                                            |
| **Fleetbase Maintenance / Telematics hardware**                     | Marked **Future** in `FLEETBASE_MODULES.md`                                                                                     |
| **Fleetbase Storefront / Ledger console modules**                   | Ignore / Replace with PorterChain portals + billing                                                                             |
| **Mobile customer app depth**                                       | Expo shell: Sign-in + Track only — not a Navigator clone                                                                        |
| **Mobile driver = full field product**                              | Shell with Clerk + FCM + location + jobs/docs; Wave 4 contracts API, does not replace Fleetbase Navigator                       |
| **OSRM public demo as default**                                     | `osrm_allow_public_demo` default **false**; labeled last resort only                                                            |
| **Full Ontario / 150 GB map extract**                               | GTA ±150 km Valhalla/OSRM PBF only                                                                                              |
| **Zoho SalesIQ on website**                                         | Guard: `DeferredSiteIntegrations` must **not** load Zoho (`verify_wave10_w10_5_whatsapp.py`) — WhatsApp + CapacityGuide instead |
| **Admin mint merchant API keys / Shopify**                          | Merchant creates; admin revokes/disables only                                                                                   |
| **Fake “AI insights” on admin merchant Overview**                   | Heuristic next actions only — not a product SKU (NIM narrative only when Phase2 + flag on)                                      |
| **Merchant-portal NVIDIA NIM**                                      | Admin Ask NIM / ModelGateway first; portal stays out until Phase 1 loop is boring                                               |
| **Vitest for admin merchant Locations / Team CRUD panels**          | Deferred under 10-customer gate — Waves 1–3 mounted live UI without panel unit tests                                            |
| **Merchant portal `/bulk` in main Operations nav**                  | Module exists for OWNER/ADMIN/OPS; stays EXTRA_ROUTE / under-nav until ops asks — do not invent a parallel admin bulk spine     |
| **Delivery zones dual SoT cleanup**                                 | `coverage.delivery_zones` structured vs Settings free-text `delivery_zones` — parked single-SoT polish, not a Wave 3 mount      |
| **Customer Clerk bypass as product shortcut**                       | Local `CLERK_DEV_BYPASS` for API/portals only                                                                                   |
| **Missing `docs/WEBSITE_GTM_EXECUTION_PLAN.md`**                    | Not a license to invent Phase 3 website copy                                                                                    |
| **Admin Settings editable Project mode control**                    | Read-only posture card on Settings overview; control place = `pnpm mode:set` / Doppler (`project_mode.py`)                      |
| **`APP_ENV=development` / `dev` as distinct stored values**         | Normalized at boot to `local` (development mode); testing stays `test`; production aliases → fail-closed                        |
| **Auth bypass / Stripe mock outside development project mode**      | Dual-gated: mode + `CLERK_DEV_BYPASS` / `STRIPE_MOCK`; testing + production stay blocked                                        |
| **iOS Critical Alerts entitlement** (ops SOS / cold-chain)          | Needs Apple entitlement + provisioning; FCM uses `time-sensitive` only until ops requests Critical Alerts                       |
| **True on-call / topic subscribe for staff push**                   | Device-aware fan-out (active FCM tokens → push; else email) is enough for early network; no shift/on-call rota product yet      |
| **Staff push on every parcel milestone**                            | Alert budget — risk events only (SLA / exception / reject / emergency / delay / temp / incident). Routine → `in_app`            |
| **Expo Push / dual raw APNs plane**                                 | FCM-only (`DeviceService` rejects Expo / fake `web-*` tokens)                                                                   |
| **Fleetbase `NotifyOrderEvent` / SocketCluster for PC portal push** | FleetOps console may keep Fleetbase notify; PorterChain admin/driver portals use `notification_engine` → FCM only               |
| **Admin staff SMS as primary channel**                              | Push → email is the failsafe; SMS only when `AdminUser.phone` (or linked `PorterchainUser.phone`) is set — not required for MVP |

---

## Project mode — done vs skip

Boot-time project mode is **complete in code** (`porterchain_shared.config.project_mode`, Settings normalize, settings dashboard `project_mode`, Admin read-only card, `pnpm mode:set`). Not leftovers:

| Mode        | `APP_ENV` (canonical)             | Intent                                        |
| ----------- | --------------------------------- | --------------------------------------------- |
| development | `local`                           | Laptop; bypass/mocks only with explicit flags |
| testing     | `test`                            | CI; no `Bearer dev`                           |
| production  | `production` / `staging` / `prod` | Fail-closed; live Clerk                       |

**Ops:** change mode → restart API + portals. Do not treat Admin `403 project_mode_immutable` as a missing feature.

---

## Shopify Quote≡Book + merchant billing — intentional skips (2026-09)

Wave goal: **one PricingEngine** for CarrierService + book; **merchant_ar** as outstanding SSOT; Stripe Checkout Pay now / Pay all; invoice detail SOT; spend-by-channel / pricing-model reports. Rows below are **held on purpose** — not incomplete Carrier or AR bugs.

### Done in this wave (do not reopen as “skips”)

HMAC-hardened CarrierService → `calculate_merchant` · `shopify_rate_quotes` + quote_id on book · Quote≡Book tests · invoice GET detail (channel / pricing_model / quote) · POST pay + pay-outstanding · webhook settle · portal Pay now / Pay all · sticky invoice detail UI · remind email Pay link · PDF/CSV ≡ GET cents · reports spend by channel / FSA|distance bands · OAuth/email hijack blocks · Shopify carrier/webhook rate limits · AR cycle `InvoiceLine` with channel · settle receipt + `invoice.paid_stripe` audit · commerce Prometheus metrics (`shopify_quote`, `invoice_pay`, `ar_mismatch`) · billing tax/credits/contract glossary KPIs · Doppler/env notes for Shopify+Stripe · DoD assert Quote≡Book≡channel≡invoice · canvas todos synced (54 completed / 9 cancelled intentional)

### Intentionally not done

| Item                                                                | Why held                                                                                                                                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Shopify App Store / Partners public listing**                     | Not discoverable by default; install is OAuth link or custom Admin API token. `integrations/shopify/app.toml` stays a stub (`client_id` empty) until Partners publish is an explicit ops decision |
| **Filled `app.toml` + listing assets (P2)**                         | Same as above — empty `client_id` is not a CarrierService gap                                                                                                                                     |
| **ACH / saved payment methods for AR pay (P2)**                     | Card Checkout is enough for early network; Connect COD path stays separate from AR                                                                                                                |
| **New pricing / billing microservice**                              | One FastAPI + PricingEngine; Shopify is thin HMAC ingress only                                                                                                                                    |
| **Client-supplied invoice cents / pay amounts**                     | Amount always server-locked from invoice / `merchant_ar` — never trust portal body                                                                                                                |
| **CRM / sales pipeline mixed into delivery outstanding**            | Sales CRM stays out of `merchant_ar`                                                                                                                                                              |
| **Google Distance Matrix for Shopify rates**                        | Carrier path uses Valhalla → OSRM (+ FSA from postal); Google = Places only                                                                                                                       |
| **SocketCluster / Fleetbase HTTP from merchant portal for Shopify** | Install + rates stay behind PorterChain API                                                                                                                                                       |
| **Scheduled report email delivery**                                 | `scheduled_email_available: false` — profile may store schedule rows; mailer is not product yet                                                                                                   |
| **Shared custom period picker on Reports**                          | Calendar-month UTC is period SoT for now; deep date-range UX is polish, not Quote≡Book                                                                                                            |
| **Aging + paid-on-time as a dedicated report slice**                | Aging already on invoice detail / AR; report KPI waits until pay volume is boring                                                                                                                 |
| **Live E2E Shopify→invoice→Pay→channel in CI**                      | Unit/integration cover Quote≡Book + pay webhook; full shop sandbox E2E needs Partners test shop + secrets — ops, not a missing engine                                                             |
| **Portal contract badge / sample Shopify quote polish**             | Rate card + billing already surface contract; badge is UX candy after install loop is boring                                                                                                      |
| **Admin “preview as checkout” Shopify simulator**                   | Admin pricing tools exist; full CarrierService replay UI is not required for 10 merchants                                                                                                         |

### Still open product work (not skips — track separately)

**None.** Canvas: 54 completed / 9 cancelled / **0 pending** — **WAVE CLOSED**. Admin E2E asserts Invoice/Statement/Reports/Dispatch/Delivery; ops-1 has `quote_latency` + `pay_started`/`succeeded` aliases; handshake canvas is Quote≡Book.

Residual **ops only** (human laptop/prod — not agent backlog): set live Doppler `SHOPIFY_*` + Stripe in the prod API project; optional Mailpit UI glance after a real remind/receipt (SMTP :1025 reachable locally).

---

## Loud FCM / ops push — done vs skip (2026-09)

Jeff Dean bar for admin + driver loud push. **Complete in code for early network — not leftovers.**

### Done (do not reopen as gaps)

FCM OS urgency (`AndroidConfig` / `APNSConfig` / `channel_id`) · staff risk `push` budget · unmuteable admin high/critical · device-aware staff fan-out · zero-device → email · admin auto-register + loud SW + foreground `onMessage` · driver `ops_critical` / `assignments` / `tracking` channels · SLI by push priority · ops **Push health** strip · `AdminUser.phone` for optional SMS fallback

Sensors: Graphify (architecture) → Ripwire (routers / SW / register). CodeGraph schema pass was optional hygiene, not a product gap.

### Intentionally not done (same surface)

Rows in **Intentionally not done** above: Critical Alerts · on-call topics · every-parcel staff push · Expo/dual APNs · Fleetbase notify for PC portals · SMS-as-primary. Also covered by **Still policy**: second mail/FCM engine; SocketCluster in web apps.

### Ops

`FIREBASE_*` + `PORTERCHAIN_PUSH_ENABLED` / `PORTERCHAIN_PUSH_SEND` on API **and** worker (`env/worker.env.example`). Grant browser notifications once on admin; strip on Operations Control Tower. Migration: `a9b0c1d2e3f4` (`admin_users.phone`).

---

## Freeze allowlists (intentional debt, not new work)

| Guard                                                                 | Intentional hold                                                                                     |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `_LEGACY_CROSS_ENGINE_IMPORTS`                                        | Existing admin↔billing/booking/fleetbase/… edges; **no new** mash-ups                                |
| `_LEGACY_UPWARD_ADMIN_IMPORTS` / router LOC / engine service LOC caps | Baseline debt frozen in `verify_d2_contracts.py` — shrink over time, do not invent features to “fix” |
| Fat service / router LOC caps                                         | Coherent surfaces stay whole; next isolation = Wave 51 Settings hub if requested                     |
| Mobile vendor leaves CI                                               | No `:8000`, no `fleetbase` HTTP, no SocketCluster under `apps/mobile-*/src`                          |

---

## Ops / naming traps (not “missing features”)

| Name                              | Reality                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------ |
| `DeferredSiteIntegrations`        | **Implemented** — lazy CMP/analytics/WhatsApp; “deferred” = load timing, not backlog |
| `FsaRatesCard` `BLANK`            | Empty form draft for new FSA rate — not an unfinished panel                          |
| `DeliveryDeferred`                | Notification delivery state, not a product deferral                                  |
| CRM `LeadDecisionStatus.DEFERRED` | Business lead status enum                                                            |

---

## Related SSOT

- [ARCHITECTURE.md](../ARCHITECTURE.md) — Finished / Current / Required + rejected overlays
- [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md) — Use / Extend / Replace / Future (parked Phase 6 points here)
- [FLEETBASE_PERMANENT_BOND.md](FLEETBASE_PERMANENT_BOND.md) — PorterChain↔Fleetbase permanent bond (do not fork PHP)
- [docs/PORTERCHAIN_CHARTER.md](PORTERCHAIN_CHARTER.md) — 10-customer gate
- [DRIVER_VERIFICATION_INTENTIONAL_SKIPS.md](DRIVER_VERIFICATION_INTENTIONAL_SKIPS.md) — thin pointer → this file
- `shared/python/porterchain_shared/config/project_mode.py` — ProjectMode / RuntimePosture SoT
- `.cursor/rules/fleetbase-first-policy.mdc` · `dependency-freeze.mdc` · `porterchain-charter.mdc`
