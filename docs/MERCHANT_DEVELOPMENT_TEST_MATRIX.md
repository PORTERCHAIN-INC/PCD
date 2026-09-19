# Merchant + Admin Merchant — Development Test Matrix

**Entry SSOT:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).

**Type:** DEVELOPMENT TEST SSOT · **Verified:** 2026-09-17 · **Sensor:** Graphify (Moment A)

Mapped from live OpenAPI (`docs/api/openapi.json`), `ARCHITECTURE.md`, `apps/merchant-portal`, `apps/admin` merchant 360, `merchant_engine`, `routers/merchants.py`, and intentional skips in `docs/PCD_INTENTIONAL_SKIPS.md`.

God nodes (Graphify): **MerchantContext** (465), **Merchant** (257). Portal app: `apps/merchant-portal` (:3001). Admin merchants: `/merchants` + `/merchants/[id]` tabs.

## How to use

| Field      | Meaning                                                                                                                                        |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **ID**     | Stable case id (`MP-*` portal, `AD-*` admin, `API-*` HTTP, `HS-*` handshake, `NEG-*` architecture negative, `DB-*` model, `DX-*` docker/infra) |
| **P**      | P0 ship-blocker · P1 release · P2 depth · P3 soak/chaos                                                                                        |
| **Kind**   | `unit` · `api` · `contract` · `e2e` · `ui` · `ux` · `handshake` · `chaos` · `security`                                                         |
| **Assert** | Pass condition (Given/When/Then compressed)                                                                                                    |

Follow-up sensors (one per session per `.cursor/rules/graph-tools.mdc`):

1. **CodeGraph** — extract Pydantic/ORM for booking, pricing, Shopify payloads, MapsService contracts.
2. **Ripwire** — `--for="merchant portal thin routers"` / `--callers=MerchantContext` / `--impact=shopify_service`.

---

## 0. Coverage census (live)

| Surface                             | Count |
| ----------------------------------- | ----: |
| Merchant portal pages/subpages      |    22 |
| Admin merchant UI surfaces          |    16 |
| `/v1/merchant/*` paths              |   150 |
| `/v1/merchant-api/*` paths          |     7 |
| Admin merchant-related paths        |    43 |
| Shopify integration paths           |     8 |
| Auth onboarding paths               |     3 |
| Shared notification paths           |     9 |
| Existing `test_merchant*` API files |    34 |
| ORM classes in `merchant_models.py` |    14 |

Existing API suites already present (do not duplicate blindly — extend):

- `test_merchant_ar_service.py`
- `test_merchant_control_wave.py`
- `test_merchant_coverage_ao.py`
- `test_merchant_lifecycle.py`
- `test_merchant_org_ssot.py`
- `test_merchant_service_coverage.py`
- `test_merchant_status_glossary_ap.py`
- `test_merchant_tax_legal_am.py`
- `test_merchant_activation_policy.py`
- `test_merchant_api_documentation.py`
- `test_merchant_api_idempotency.py`
- `test_merchant_billing_pack.py`
- `test_merchant_book_al.py`
- `test_merchant_branding.py`
- `test_merchant_cancel.py`
- `test_merchant_claims.py`
- `test_merchant_first_run_ay.py`
- `test_merchant_inbox.py`
- `test_merchant_integrations.py`
- `test_merchant_invoice_pay.py`
- `test_merchant_onboarding_company_file.py`
- `test_merchant_onboarding_email.py`
- `test_merchant_pricing_api.py`
- `test_merchant_print_preview.py`
- `test_merchant_privacy.py`
- `test_merchant_rbac_pages.py`
- `test_merchant_referrals.py`
- `test_merchant_reports.py`
- `test_merchant_route_csv_errors.py`
- `test_merchant_spend_attribution.py`
- `test_merchant_tracking.py`
- `test_merchant_verticals.py`
- `test_merchant_wave2_floor.py`
- `test_admin_merchant_org.py`

Portal unit tests today (thin): `merchant-nav.test.ts`, `onboarding.test.ts`, `route-module/units.test.ts`.

---

## 1. Architecture & negative cases (must stay true)

| ID           | P   | Kind     | Assert                                                                                                   |
| ------------ | --- | -------- | -------------------------------------------------------------------------------------------------------- |
| NEG-ARCH-001 | P0  | contract | Merchant portal never calls Fleetbase HTTP or SocketCluster SDK                                          |
| NEG-ARCH-002 | P0  | contract | Pricing/book path uses MapsService → Valhalla then OSRM; never Google Distance Matrix/ETA/geometry       |
| NEG-ARCH-003 | P0  | contract | No PorterChain VROOM client under `*_engine`; VROOM only via Fleetbase orchestrator                      |
| NEG-ARCH-004 | P0  | security | Admin hard-DELETE merchant is absent (close/convert/reopen only)                                         |
| NEG-ARCH-005 | P0  | security | Clerk merchant triad is `CLERK_MERCHANT_*` via `env/clerk.env` + `pnpm clerk:sync` — no ad-hoc key names |
| NEG-ARCH-006 | P0  | contract | Firebase is FCM-only for merchant web push — not Auth/RBAC                                               |
| NEG-ARCH-007 | P0  | contract | `is_sandbox` on merchant/order is commercial label, not `APP_ENV` project mode                           |
| NEG-ARCH-008 | P1  | contract | Routers under `routers/merchant/` stay thin (service call only)                                          |
| NEG-ARCH-009 | P1  | contract | Admin browser does not use merchant Clerk JWT; staff IdP session only                                    |
| NEG-ARCH-010 | P0  | contract | OpenAPI census includes `/v1/merchant` + `/v1/admin/merchants` prefixes                                  |

---

## 2. Merchant persona — pages & UX

Nav SSOT: `apps/merchant-portal/src/lib/merchant-nav.ts` (modules + jobs: owner/dispatcher/accounting/viewer).

| ID          | P   | Kind      | Page                          | Assert                                                                                                                                            |
| ----------- | --- | --------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| MP-AUTH-001 | P0  | e2e       | /sign-in                      | Clerk merchant app sign-in succeeds; bad org rejected                                                                                             |
| MP-AUTH-002 | P0  | e2e       | /sign-up                      | Signup lands onboarding when company incomplete                                                                                                   |
| MP-AUTH-003 | P0  | api       | session                       | GET /v1/merchant/session returns modules matching RBAC                                                                                            |
| MP-AUTH-004 | P0  | api       | /v1/merchant/me               | Identity + merchant_id + role present                                                                                                             |
| MP-AUTH-005 | P0  | api       | memberships                   | GET /v1/merchant/memberships lists orgs; switcher isolates data                                                                                   |
| MP-AUTH-006 | P1  | ui        | MerchantAccessGate            | Missing module hides nav item and blocks deep link                                                                                                |
| MP-ONB-001  | P0  | e2e       | /onboarding                   | Company file completeness gates portal unlock                                                                                                     |
| MP-ONB-002  | P0  | api       | auth onboarding               | PATCH profile/vertical persist; GET reflects                                                                                                      |
| MP-ONB-003  | P1  | api       | activation                    | Pending merchant cannot book until activate policy allows                                                                                         |
| MP-DASH-001 | P0  | e2e       | /dashboard                    | KPIs load; empty state for new merchant                                                                                                           |
| MP-DASH-002 | P1  | api       | dashboard                     | GET /v1/merchant/dashboard schema matches portal types                                                                                            |
| MP-BOOK-001 | P0  | e2e       | /book                         | Places autocomplete (Google) → quote preview → confirm creates order                                                                              |
| MP-BOOK-002 | P0  | api       | preview                       | POST /v1/merchant/booking/preview returns cents + distance source valhalla                                                                        | osrm |
| MP-BOOK-003 | P0  | api       | confirm                       | POST confirm is idempotent on replay                                                                                                              |
| MP-BOOK-004 | P0  | handshake | Fleetbase                     | Confirm enqueues Fleetbase sync; retry queue survives adapter blip                                                                                |
| MP-BOOK-005 | P1  | api       | draft                         | Draft create/confirm path works; abandoned drafts listable in admin                                                                               |
| MP-BOOK-006 | P1  | api       | templates                     | CRUD booking templates                                                                                                                            |
| MP-BOOK-007 | P1  | api       | multi                         | POST /booking/multi multi-stop quote+book                                                                                                         |
| MP-BOOK-008 | P1  | ux        | /book                         | Error copy for out-of-coverage postal is actionable                                                                                               |
| MP-BULK-001 | P0  | e2e       | /bulk                         | CSV upload → confirm creates N orders                                                                                                             |
| MP-BULK-002 | P1  | api       | bulk                          | Invalid rows return row-level errors without partial silent success                                                                               |
| MP-RTE-001  | P0  | e2e       | /routes                       | Upload CSV, map columns, optimize, confirm                                                                                                        |
| MP-RTE-002  | P0  | handshake | quote distance                | Stop/quote distance via MapsService Valhalla→OSRM; **never** Google geometry                                                                      |
| MP-RTE-002b | P0  | handshake | VROOM                         | POST .../optimize **enqueues** worker / Fleetbase orchestrator (`engine=vroom`); NN+quote in worker — not in-process TSP; no PC VROOM HTTP client |
| MP-RTE-002c | P0  | contract  | anti-VROOM                    | Grep/CI: `merchant_engine` has no direct VROOM client import                                                                                      |
| MP-RTE-003  | P1  | api       | mapping-profile               | Save/apply mapping profile across jobs                                                                                                            |
| MP-RTE-004  | P1  | api       | stops patch                   | PATCH stop index corrects address + re-geocode                                                                                                    |
| MP-RTE-005  | P2  | chaos     | Valhalla down                 | Quote/distance falls back to OSRM or fails clearly labeled; optimize enqueue still may hit Fleetbase when bridge on                               |
| MP-RTE-006  | P1  | api       | job status                    | GET route job reflects queued → ready/failed; confirm only when unconfirmed                                                                       |
| MP-RTE-007  | P1  | handshake | Fleetbase sync                | Confirm creates/updates Fleetbase stops via sync/retry queue                                                                                      |
| MP-ORD-001  | P0  | e2e       | /orders                       | List/filter/search; open Order 360                                                                                                                |
| MP-ORD-002  | P0  | api       | orders 360                    | GET /orders/{id}/360 returns timeline + pricing + tracking                                                                                        |
| MP-ORD-003  | P0  | api       | cancel                        | Cancel respects cancel_policy; Fleetbase notified                                                                                                 |
| MP-ORD-004  | P1  | api       | parcels                       | PATCH parcels amend before dispatch lock                                                                                                          |
| MP-ORD-005  | P1  | api       | labels/pod                    | PDF labels, POD zip, print-preview, compliance dossier                                                                                            |
| MP-ORD-006  | P1  | api       | duplicate                     | Duplicate order creates new draft/booking                                                                                                         |
| MP-ORD-007  | P1  | api       | tracking-email                | POST tracking-email sends via mail (Mailpit in dev)                                                                                               |
| MP-TRK-001  | P0  | e2e       | /track                        | Track by number; map tiles Google; GPS SoT not invented in portal                                                                                 |
| MP-TRK-002  | P0  | api       | track                         | GET /v1/merchant/track/{tn} + orders/{id}/tracking                                                                                                |
| MP-TRK-003  | P1  | api       | tracking dashboard            | GET /tracking/dashboard aggregate                                                                                                                 |
| MP-HLP-001  | P0  | e2e       | /help                         | Create ticket + claim; list knowledge-base                                                                                                        |
| MP-HLP-002  | P1  | api       | claims                        | POST/GET claims; status transitions                                                                                                               |
| MP-BIL-001  | P0  | e2e       | /billing                      | Overview, invoices, statement, exports                                                                                                            |
| MP-BIL-002  | P0  | api       | invoices pdf                  | GET invoice PDF; remind AP contact                                                                                                                |
| MP-BIL-003  | P0  | api       | COD                           | COD connect/enable gated; Checkout path untouched                                                                                                 |
| MP-BIL-004  | P1  | api       | credit-notes                  | List credit notes; export CSVs                                                                                                                    |
| MP-BIL-005  | P1  | e2e       | invoice detail                | /billing/invoices/[id] renders line items                                                                                                         |
| MP-RPT-001  | P0  | e2e       | /reports                      | Overview + export csv/xlsx for each report_type                                                                                                   |
| MP-RPT-002  | P1  | api       | saved/scheduled               | CRUD saved reports + scheduled                                                                                                                    |
| MP-RPT-003  | P2  | api       | switching-costs               | Switching-cost report numbers stable                                                                                                              |
| MP-NTF-001  | P0  | e2e       | /notifications                | Inbox list/read/archive; preferences                                                                                                              |
| MP-NTF-002  | P0  | handshake | FCM                           | Device register → order event → web push (or Mailpit email fallback)                                                                              |
| MP-NTF-003  | P1  | api       | settings notifications        | PATCH merchant settings/notifications                                                                                                             |
| MP-INT-001  | P0  | e2e       | /api                          | Integrations console: keys, webhooks, docs, sandbox                                                                                               |
| MP-INT-002  | P0  | api       | api-keys                      | Create/revoke key; rate-limit patch                                                                                                               |
| MP-INT-003  | P0  | api       | webhooks                      | CRUD webhook, test, rotate secret, retry delivery                                                                                                 |
| MP-INT-004  | P1  | api       | oauth clients                 | OAuth client CRUD                                                                                                                                 |
| MP-INT-005  | P1  | api       | netsuite                      | Setup/connect/sync happy + auth fail                                                                                                              |
| MP-INT-006  | P1  | api       | zapier/erp                    | Templates + ERP overview depth                                                                                                                    |
| MP-INT-007  | P1  | api       | sandbox                       | Sandbox simulator toggles without polluting live ledger                                                                                           |
| MP-SHP-001  | P0  | e2e       | /shopify                      | Install URL → callback → shop listed                                                                                                              |
| MP-SHP-002  | P0  | handshake | Shopify webhook               | orders/create books; cancel cancels; HMAC invalid → 401                                                                                           |
| MP-SHP-003  | P0  | handshake | Carrier rates                 | POST carrier-service/rates returns quote via pricing_engine                                                                                       |
| MP-SHP-004  | P1  | api       | pickup                        | PUT pickup location; DELETE shop disconnect                                                                                                       |
| MP-TEAM-001 | P0  | e2e       | /team                         | Invite seat, change role, remove user                                                                                                             |
| MP-TEAM-002 | P0  | security  | RBAC                          | Viewer cannot book; accounting cannot manage api_keys                                                                                             |
| MP-TEAM-003 | P1  | api       | two-factor                    | GET/PATCH team two-factor flags                                                                                                                   |
| MP-TEAM-004 | P1  | api       | activity                      | Team activity audit visible                                                                                                                       |
| MP-REF-001  | P0  | e2e       | /referrals                    | Share link; credit applied per policy                                                                                                             |
| MP-SET-001  | P0  | e2e       | /settings                     | Company, tax, branding, warehouses, billing contacts, documents                                                                                   |
| MP-SET-002  | P0  | api       | org SSOT                      | Admin + portal write same company file (merchant_org)                                                                                             |
| MP-SET-003  | P1  | api       | privacy                       | Export + delete-request; admin execute path separate                                                                                              |
| MP-SET-004  | P1  | api       | addresses/recipients/contacts | CRUD + default address                                                                                                                            |
| MP-SET-005  | P1  | api       | standing-orders               | CRUD standing orders                                                                                                                              |
| MP-SET-006  | P1  | api       | rate-card                     | GET pricing/rate-card matches admin configured rates                                                                                              |
| MP-UX-001   | P1  | ux        | all pages                     | Loading/empty/error skeletons; no raw stack traces                                                                                                |
| MP-UX-002   | P1  | ux        | nav jobs                      | merchantPortalJob derives owner/dispatcher/accounting/viewer from modules                                                                         |
| MP-UX-003   | P2  | ux        | a11y                          | Tab order + aria on book and Order 360                                                                                                            |
| MP-UX-004   | P2  | ui        | mobile viewport               | Book + track usable at 390px                                                                                                                      |

---

## 3. Admin — merchants module (pages, tabs, panels)

Files: `apps/admin/src/app/(ops)/merchants/page.tsx`, `[id]/page.tsx`, `components/merchants/*`, `lib/merchants.ts`, router `routers/merchants.py`.

| ID          | P   | Kind     | Surface                       | Assert                                                          |
| ----------- | --- | -------- | ----------------------------- | --------------------------------------------------------------- |
| AD-LIST-001 | P0  | e2e      | /merchants                    | List + facets + stats; search/filter                            |
| AD-LIST-002 | P0  | api      | GET /v1/admin/merchants       | Pagination, status filters, unprovisioned-signups               |
| AD-LIST-003 | P1  | api      | facets/stats                  | Facets and stats agree with list counts                         |
| AD-CRT-001  | P0  | e2e      | create merchant               | POST create provisions org + optional owner seat                |
| AD-360-001  | P0  | e2e      | tab=overview                  | Health, risk, AI strip, deep links to portal/billing/support    |
| AD-360-002  | P0  | e2e      | tab=orders                    | Merchant orders list scoped; no cross-tenant bleed              |
| AD-360-003  | P0  | e2e      | tab=money invoices            | Invoices panel + AR actions                                     |
| AD-360-004  | P0  | e2e      | tab=money contracts           | Contracts CRUD                                                  |
| AD-360-005  | P1  | e2e      | tab=money statement/credits   | Statement + credit notes                                        |
| AD-360-006  | P0  | e2e      | tab=pricing                   | Distance vs FSA model; GTA matrix fields persist                |
| AD-360-007  | P0  | e2e      | tab=people team               | Seats invite/role/delete; AddMerchantSeatModal                  |
| AD-360-008  | P0  | e2e      | tab=people contacts/locations | Contacts + locations panels; Google Places for address          |
| AD-360-009  | P1  | e2e      | tab=people activity           | Timeline / activities / tasks                                   |
| AD-360-010  | P0  | e2e      | tab=api                       | API keys/webhooks mirror merchant integrations                  |
| AD-360-011  | P0  | e2e      | tab=settings                  | Tax, privacy card, COD, standing orders, billing contacts       |
| AD-LF-001   | P0  | api      | approve/suspend/close/reopen  | Lifecycle transitions audit-logged; booking gates update        |
| AD-LF-002   | P0  | api      | complete-onboarding           | Marks onboarding complete; portal unlock                        |
| AD-LF-003   | P0  | api      | convert-to-customer           | Conversion path; no DELETE                                      |
| AD-LF-004   | P1  | api      | activate-users/owner-seat     | Seat activation emails (Mailpit)                                |
| AD-PRV-001  | P0  | security | privacy execute               | Staff step-up required; erasure executes MerchantPrivacyService |
| AD-PRC-001  | P0  | api      | PUT pricing                   | Persists; merchant rate-card GET reflects                       |
| AD-ORG-001  | P0  | api      | org SSOT                      | Admin patch profile/addresses/contacts == portal company file   |
| AD-FIN-001  | P0  | api      | merchant-ar preview/generate  | Finance AR endpoints                                            |
| AD-FIN-002  | P1  | e2e      | FinanceMerchantArPanel        | UI generate flow                                                |
| AD-USR-001  | P1  | e2e      | settings users merchant       | Directory tab add seat                                          |
| AD-DIAG-001 | P1  | api      | merchant-webhook-delivery     | Diagnostics probe                                               |
| AD-MOAT-001 | P2  | api      | data-moat merchants           | Moat metrics for merchant_id                                    |
| AD-RBAC-001 | P0  | security | staff modules                 | Non-merchant module staff gets 403 on /admin/merchants          |
| AD-UX-001   | P1  | ux       | tab deep links                | ?tab=&panel= round-trips                                        |
| AD-UX-002   | P1  | ux       | cross links                   | Portal/billing/claims/support query merchant_id                 |

---

## 4. HTTP contract matrix — every merchant-related OpenAPI path

For **each** path below generate at minimum: happy path, 401/403, validation 422, and tenant isolation where `{merchant_id}`/`order_id` present.

### 4.1 Portal `/v1/merchant/*`

| ID         | Methods      | Path                                                                | P0 focus                |
| ---------- | ------------ | ------------------------------------------------------------------- | ----------------------- |
| API-MP-001 | GET,POST     | `/v1/merchant/addresses`                                            | authz+schema            |
| API-MP-002 | DELETE,PATCH | `/v1/merchant/addresses/{address_id}`                               | authz+schema            |
| API-MP-003 | POST         | `/v1/merchant/addresses/{address_id}/default`                       | authz+schema            |
| API-MP-004 | GET,POST     | `/v1/merchant/api-keys`                                             | happy+idempotency+authz |
| API-MP-005 | DELETE       | `/v1/merchant/api-keys/{key_id}`                                    | happy+idempotency+authz |
| API-MP-006 | GET          | `/v1/merchant/audit-logs`                                           | authz+schema            |
| API-MP-007 | GET          | `/v1/merchant/billing/cod`                                          | happy+idempotency+authz |
| API-MP-008 | POST         | `/v1/merchant/billing/cod/connect`                                  | happy+idempotency+authz |
| API-MP-009 | POST         | `/v1/merchant/billing/cod/enable`                                   | happy+idempotency+authz |
| API-MP-010 | GET          | `/v1/merchant/billing/contract`                                     | happy+idempotency+authz |
| API-MP-011 | GET          | `/v1/merchant/billing/credit-notes`                                 | happy+idempotency+authz |
| API-MP-012 | GET          | `/v1/merchant/billing/export/history.csv`                           | happy+idempotency+authz |
| API-MP-013 | GET          | `/v1/merchant/billing/export/invoices.csv`                          | happy+idempotency+authz |
| API-MP-014 | GET          | `/v1/merchant/billing/export/statement.csv`                         | happy+idempotency+authz |
| API-MP-015 | GET          | `/v1/merchant/billing/history`                                      | happy+idempotency+authz |
| API-MP-016 | GET          | `/v1/merchant/billing/invoices`                                     | happy+idempotency+authz |
| API-MP-017 | GET          | `/v1/merchant/billing/invoices/{invoice_id}/pdf`                    | happy+idempotency+authz |
| API-MP-018 | POST         | `/v1/merchant/billing/invoices/{invoice_id}/remind`                 | happy+idempotency+authz |
| API-MP-019 | GET          | `/v1/merchant/billing/overview`                                     | happy+idempotency+authz |
| API-MP-020 | GET          | `/v1/merchant/billing/payments`                                     | happy+idempotency+authz |
| API-MP-021 | GET          | `/v1/merchant/billing/statement`                                    | happy+idempotency+authz |
| API-MP-022 | GET          | `/v1/merchant/billing/statement/detail`                             | happy+idempotency+authz |
| API-MP-023 | GET          | `/v1/merchant/billing/tax-summary`                                  | happy+idempotency+authz |
| API-MP-024 | POST         | `/v1/merchant/booking/confirm`                                      | happy+idempotency+authz |
| API-MP-025 | GET,POST     | `/v1/merchant/booking/draft`                                        | happy+idempotency+authz |
| API-MP-026 | POST         | `/v1/merchant/booking/draft/{draft_id}/confirm`                     | happy+idempotency+authz |
| API-MP-027 | POST         | `/v1/merchant/booking/multi`                                        | happy+idempotency+authz |
| API-MP-028 | POST         | `/v1/merchant/booking/preview`                                      | happy+idempotency+authz |
| API-MP-029 | GET          | `/v1/merchant/booking/recipients`                                   | happy+idempotency+authz |
| API-MP-030 | GET          | `/v1/merchant/booking/saved-addresses`                              | happy+idempotency+authz |
| API-MP-031 | GET,POST     | `/v1/merchant/booking/templates`                                    | happy+idempotency+authz |
| API-MP-032 | DELETE       | `/v1/merchant/booking/templates/{template_id}`                      | happy+idempotency+authz |
| API-MP-033 | POST         | `/v1/merchant/bookings`                                             | happy+idempotency+authz |
| API-MP-034 | POST         | `/v1/merchant/bulk/upload`                                          | authz+schema            |
| API-MP-035 | POST         | `/v1/merchant/bulk/{job_id}/confirm`                                | authz+schema            |
| API-MP-036 | GET,POST     | `/v1/merchant/claims`                                               | authz+schema            |
| API-MP-037 | GET          | `/v1/merchant/claims/{claim_id}`                                    | authz+schema            |
| API-MP-038 | GET,POST     | `/v1/merchant/contacts`                                             | authz+schema            |
| API-MP-039 | DELETE,PATCH | `/v1/merchant/contacts/{contact_id}`                                | authz+schema            |
| API-MP-040 | GET          | `/v1/merchant/dashboard`                                            | authz+schema            |
| API-MP-041 | PATCH        | `/v1/merchant/integrations/api-keys/{key_id}/rate-limit`            | happy+idempotency+authz |
| API-MP-042 | POST         | `/v1/merchant/integrations/console`                                 | authz+schema            |
| API-MP-043 | GET          | `/v1/merchant/integrations/csv-templates`                           | authz+schema            |
| API-MP-044 | GET          | `/v1/merchant/integrations/csv-templates/{template_id}.csv`         | authz+schema            |
| API-MP-045 | GET          | `/v1/merchant/integrations/depth`                                   | authz+schema            |
| API-MP-046 | GET          | `/v1/merchant/integrations/documentation`                           | authz+schema            |
| API-MP-047 | GET          | `/v1/merchant/integrations/erp`                                     | authz+schema            |
| API-MP-048 | GET          | `/v1/merchant/integrations/events`                                  | authz+schema            |
| API-MP-049 | POST         | `/v1/merchant/integrations/netsuite/connect`                        | authz+schema            |
| API-MP-050 | GET          | `/v1/merchant/integrations/netsuite/setup`                          | authz+schema            |
| API-MP-051 | POST         | `/v1/merchant/integrations/netsuite/sync`                           | authz+schema            |
| API-MP-052 | GET          | `/v1/merchant/integrations/oauth`                                   | authz+schema            |
| API-MP-053 | GET,POST     | `/v1/merchant/integrations/oauth/clients`                           | authz+schema            |
| API-MP-054 | GET          | `/v1/merchant/integrations/overview`                                | authz+schema            |
| API-MP-055 | GET          | `/v1/merchant/integrations/rate-limits`                             | authz+schema            |
| API-MP-056 | GET,PATCH    | `/v1/merchant/integrations/sandbox`                                 | authz+schema            |
| API-MP-057 | GET          | `/v1/merchant/integrations/usage`                                   | authz+schema            |
| API-MP-058 | POST         | `/v1/merchant/integrations/webhooks/deliveries/{delivery_id}/retry` | authz+schema            |
| API-MP-059 | GET          | `/v1/merchant/integrations/webhooks/logs`                           | authz+schema            |
| API-MP-060 | DELETE,PATCH | `/v1/merchant/integrations/webhooks/{webhook_id}`                   | authz+schema            |
| API-MP-061 | GET          | `/v1/merchant/integrations/webhooks/{webhook_id}/history`           | authz+schema            |
| API-MP-062 | POST         | `/v1/merchant/integrations/webhooks/{webhook_id}/rotate-secret`     | authz+schema            |
| API-MP-063 | POST         | `/v1/merchant/integrations/webhooks/{webhook_id}/test`              | authz+schema            |
| API-MP-064 | GET          | `/v1/merchant/integrations/zapier/templates`                        | authz+schema            |
| API-MP-065 | GET          | `/v1/merchant/me`                                                   | authz+schema            |
| API-MP-066 | GET          | `/v1/merchant/memberships`                                          | authz+schema            |
| API-MP-067 | GET          | `/v1/merchant/orders`                                               | happy+idempotency+authz |
| API-MP-068 | POST         | `/v1/merchant/orders/bulk`                                          | happy+idempotency+authz |
| API-MP-069 | GET          | `/v1/merchant/orders/dashboard`                                     | happy+idempotency+authz |
| API-MP-070 | POST         | `/v1/merchant/orders/labels/bulk`                                   | happy+idempotency+authz |
| API-MP-071 | GET          | `/v1/merchant/orders/pickup-list.pdf`                               | happy+idempotency+authz |
| API-MP-072 | GET          | `/v1/merchant/orders/pickup-manifest.pdf`                           | happy+idempotency+authz |
| API-MP-073 | GET          | `/v1/merchant/orders/{order_id}`                                    | happy+idempotency+authz |
| API-MP-074 | GET          | `/v1/merchant/orders/{order_id}/360`                                | happy+idempotency+authz |
| API-MP-075 | POST         | `/v1/merchant/orders/{order_id}/cancel`                             | happy+idempotency+authz |
| API-MP-076 | GET          | `/v1/merchant/orders/{order_id}/compliance-dossier.pdf`             | happy+idempotency+authz |
| API-MP-077 | POST         | `/v1/merchant/orders/{order_id}/duplicate`                          | happy+idempotency+authz |
| API-MP-078 | GET          | `/v1/merchant/orders/{order_id}/labels.pdf`                         | happy+idempotency+authz |
| API-MP-079 | PATCH        | `/v1/merchant/orders/{order_id}/parcels`                            | happy+idempotency+authz |
| API-MP-080 | GET          | `/v1/merchant/orders/{order_id}/pod.zip`                            | happy+idempotency+authz |
| API-MP-081 | GET          | `/v1/merchant/orders/{order_id}/pod/{slug}`                         | happy+idempotency+authz |
| API-MP-082 | GET          | `/v1/merchant/orders/{order_id}/print-preview.pdf`                  | happy+idempotency+authz |
| API-MP-083 | GET          | `/v1/merchant/orders/{order_id}/tracking`                           | happy+idempotency+authz |
| API-MP-084 | POST         | `/v1/merchant/orders/{order_id}/tracking-email`                     | happy+idempotency+authz |
| API-MP-085 | GET          | `/v1/merchant/pricing/rate-card`                                    | happy+idempotency+authz |
| API-MP-086 | GET          | `/v1/merchant/privacy`                                              | security+step-up        |
| API-MP-087 | POST         | `/v1/merchant/privacy/delete-request`                               | security+step-up        |
| API-MP-088 | GET          | `/v1/merchant/privacy/export`                                       | security+step-up        |
| API-MP-089 | GET,PATCH    | `/v1/merchant/profile`                                              | authz+schema            |
| API-MP-090 | GET,POST     | `/v1/merchant/recipients`                                           | authz+schema            |
| API-MP-091 | DELETE,PATCH | `/v1/merchant/recipients/{recipient_id}`                            | authz+schema            |
| API-MP-092 | GET          | `/v1/merchant/reports/claims`                                       | authz+schema            |
| API-MP-093 | GET          | `/v1/merchant/reports/delivery-performance`                         | authz+schema            |
| API-MP-094 | GET          | `/v1/merchant/reports/destinations`                                 | authz+schema            |
| API-MP-095 | GET          | `/v1/merchant/reports/drivers`                                      | authz+schema            |
| API-MP-096 | GET          | `/v1/merchant/reports/executive`                                    | authz+schema            |
| API-MP-097 | GET          | `/v1/merchant/reports/export/{report_type}.csv`                     | authz+schema            |
| API-MP-098 | GET          | `/v1/merchant/reports/export/{report_type}.xlsx`                    | authz+schema            |
| API-MP-099 | GET          | `/v1/merchant/reports/invoices`                                     | authz+schema            |
| API-MP-100 | GET          | `/v1/merchant/reports/order-volume`                                 | authz+schema            |
| API-MP-101 | GET          | `/v1/merchant/reports/overview`                                     | authz+schema            |
| API-MP-102 | GET,POST     | `/v1/merchant/reports/saved`                                        | authz+schema            |
| API-MP-103 | DELETE       | `/v1/merchant/reports/saved/{report_id}`                            | authz+schema            |
| API-MP-104 | GET,POST     | `/v1/merchant/reports/scheduled`                                    | authz+schema            |
| API-MP-105 | GET          | `/v1/merchant/reports/sla-history`                                  | authz+schema            |
| API-MP-106 | GET          | `/v1/merchant/reports/summary`                                      | authz+schema            |
| API-MP-107 | GET          | `/v1/merchant/reports/switching-costs`                              | authz+schema            |
| API-MP-108 | GET          | `/v1/merchant/reports/vehicles`                                     | authz+schema            |
| API-MP-109 | GET          | `/v1/merchant/route-import-profiles`                                | happy+idempotency+authz |
| API-MP-110 | GET,POST     | `/v1/merchant/route-imports`                                        | happy+idempotency+authz |
| API-MP-111 | POST         | `/v1/merchant/route-imports/upload`                                 | happy+idempotency+authz |
| API-MP-112 | GET          | `/v1/merchant/route-imports/{job_id}`                               | happy+idempotency+authz |
| API-MP-113 | POST         | `/v1/merchant/route-imports/{job_id}/confirm`                       | happy+idempotency+authz |
| API-MP-114 | PATCH        | `/v1/merchant/route-imports/{job_id}/mapping`                       | happy+idempotency+authz |
| API-MP-115 | POST         | `/v1/merchant/route-imports/{job_id}/mapping-profile`               | happy+idempotency+authz |
| API-MP-116 | POST         | `/v1/merchant/route-imports/{job_id}/mapping-profile/apply`         | happy+idempotency+authz |
| API-MP-117 | POST         | `/v1/merchant/route-imports/{job_id}/optimize`                      | happy+idempotency+authz |
| API-MP-118 | PATCH        | `/v1/merchant/route-imports/{job_id}/stops/{index}`                 | happy+idempotency+authz |
| API-MP-119 | GET          | `/v1/merchant/session`                                              | authz+schema            |
| API-MP-120 | GET,POST     | `/v1/merchant/settings/billing-contacts`                            | happy+idempotency+authz |
| API-MP-121 | DELETE,PATCH | `/v1/merchant/settings/billing-contacts/{contact_id}`               | happy+idempotency+authz |
| API-MP-122 | PATCH        | `/v1/merchant/settings/branding`                                    | authz+schema            |
| API-MP-123 | GET          | `/v1/merchant/settings/contract`                                    | authz+schema            |
| API-MP-124 | GET,POST     | `/v1/merchant/settings/documents`                                   | authz+schema            |
| API-MP-125 | DELETE       | `/v1/merchant/settings/documents/{doc_id}`                          | authz+schema            |
| API-MP-126 | PATCH        | `/v1/merchant/settings/notifications`                               | authz+schema            |
| API-MP-127 | GET          | `/v1/merchant/settings/overview`                                    | authz+schema            |
| API-MP-128 | GET,PATCH    | `/v1/merchant/settings/tax`                                         | authz+schema            |
| API-MP-129 | GET,POST     | `/v1/merchant/settings/warehouses`                                  | authz+schema            |
| API-MP-130 | DELETE,PATCH | `/v1/merchant/settings/warehouses/{warehouse_id}`                   | authz+schema            |
| API-MP-131 | GET,POST     | `/v1/merchant/shopify`                                              | happy+idempotency+authz |
| API-MP-132 | GET          | `/v1/merchant/shopify/install-url`                                  | happy+idempotency+authz |
| API-MP-133 | DELETE       | `/v1/merchant/shopify/{shop_id}`                                    | happy+idempotency+authz |
| API-MP-134 | PUT          | `/v1/merchant/shopify/{shop_id}/pickup`                             | happy+idempotency+authz |
| API-MP-135 | GET,POST     | `/v1/merchant/standing-orders`                                      | happy+idempotency+authz |
| API-MP-136 | DELETE       | `/v1/merchant/standing-orders/{standing_order_id}`                  | happy+idempotency+authz |
| API-MP-137 | GET          | `/v1/merchant/support/knowledge-base`                               | authz+schema            |
| API-MP-138 | GET,POST     | `/v1/merchant/support/tickets`                                      | authz+schema            |
| API-MP-139 | GET          | `/v1/merchant/support/tickets/{ticket_id}`                          | authz+schema            |
| API-MP-140 | GET          | `/v1/merchant/team`                                                 | authz+schema            |
| API-MP-141 | GET          | `/v1/merchant/team/activity`                                        | authz+schema            |
| API-MP-142 | GET          | `/v1/merchant/team/overview`                                        | authz+schema            |
| API-MP-143 | GET          | `/v1/merchant/team/roles`                                           | authz+schema            |
| API-MP-144 | POST         | `/v1/merchant/team/seats`                                           | authz+schema            |
| API-MP-145 | GET,PATCH    | `/v1/merchant/team/two-factor`                                      | authz+schema            |
| API-MP-146 | DELETE,PATCH | `/v1/merchant/team/{user_id}`                                       | authz+schema            |
| API-MP-147 | PATCH        | `/v1/merchant/team/{user_id}/role`                                  | authz+schema            |
| API-MP-148 | GET          | `/v1/merchant/track/{tracking_number}`                              | authz+schema            |
| API-MP-149 | GET          | `/v1/merchant/tracking/dashboard`                                   | authz+schema            |
| API-MP-150 | GET,POST     | `/v1/merchant/webhooks`                                             | authz+schema            |

### 4.2 Merchant API keys `/v1/merchant-api/*`

| ID          | Methods | Path                                        | P0 focus                            |
| ----------- | ------- | ------------------------------------------- | ----------------------------------- |
| API-KEY-001 | POST    | `/v1/merchant-api/bookings`                 | key auth + idempotency + rate limit |
| API-KEY-002 | GET     | `/v1/merchant-api/orders`                   | key auth + idempotency + rate limit |
| API-KEY-003 | GET     | `/v1/merchant-api/orders/{order_id}`        | key auth + idempotency + rate limit |
| API-KEY-004 | POST    | `/v1/merchant-api/orders/{order_id}/cancel` | key auth + idempotency + rate limit |
| API-KEY-005 | POST    | `/v1/merchant-api/quotes`                   | key auth + idempotency + rate limit |
| API-KEY-006 | GET     | `/v1/merchant-api/rate-card`                | key auth + idempotency + rate limit |
| API-KEY-007 | GET     | `/v1/merchant-api/track/{tracking_number}`  | key auth + idempotency + rate limit |

### 4.3 Admin merchants

| ID         | Methods      | Path                                                               | P0 focus                             |
| ---------- | ------------ | ------------------------------------------------------------------ | ------------------------------------ |
| API-AD-001 | GET          | `/v1/admin/data-moat/merchants/{merchant_id}`                      | staff auth + audit + no cross-tenant |
| API-AD-002 | GET          | `/v1/admin/diagnostics/merchant-webhook-delivery`                  | staff auth + audit + no cross-tenant |
| API-AD-003 | POST         | `/v1/admin/finance/merchant-ar/generate`                           | staff auth + audit + no cross-tenant |
| API-AD-004 | GET          | `/v1/admin/finance/merchant-ar/preview`                            | staff auth + audit + no cross-tenant |
| API-AD-005 | GET,POST     | `/v1/admin/merchants`                                              | staff auth + audit + no cross-tenant |
| API-AD-006 | GET          | `/v1/admin/merchants/facets`                                       | staff auth + audit + no cross-tenant |
| API-AD-007 | GET          | `/v1/admin/merchants/stats`                                        | staff auth + audit + no cross-tenant |
| API-AD-008 | GET          | `/v1/admin/merchants/unprovisioned-signups`                        | staff auth + audit + no cross-tenant |
| API-AD-009 | GET,PATCH    | `/v1/admin/merchants/{merchant_id}`                                | staff auth + audit + no cross-tenant |
| API-AD-010 | POST         | `/v1/admin/merchants/{merchant_id}/activate-users`                 | staff auth + audit + no cross-tenant |
| API-AD-011 | GET          | `/v1/admin/merchants/{merchant_id}/activities`                     | staff auth + audit + no cross-tenant |
| API-AD-012 | POST         | `/v1/admin/merchants/{merchant_id}/addresses`                      | staff auth + audit + no cross-tenant |
| API-AD-013 | DELETE,PATCH | `/v1/admin/merchants/{merchant_id}/addresses/{address_id}`         | staff auth + audit + no cross-tenant |
| API-AD-014 | POST         | `/v1/admin/merchants/{merchant_id}/addresses/{address_id}/default` | staff auth + audit + no cross-tenant |
| API-AD-015 | GET          | `/v1/admin/merchants/{merchant_id}/analytics`                      | staff auth + audit + no cross-tenant |
| API-AD-016 | GET          | `/v1/admin/merchants/{merchant_id}/api`                            | staff auth + audit + no cross-tenant |
| API-AD-017 | POST         | `/v1/admin/merchants/{merchant_id}/approve`                        | staff auth + audit + no cross-tenant |
| API-AD-018 | GET,POST     | `/v1/admin/merchants/{merchant_id}/billing-contacts`               | staff auth + audit + no cross-tenant |
| API-AD-019 | DELETE,PATCH | `/v1/admin/merchants/{merchant_id}/billing-contacts/{contact_id}`  | staff auth + audit + no cross-tenant |
| API-AD-020 | POST         | `/v1/admin/merchants/{merchant_id}/close`                          | staff auth + audit + no cross-tenant |
| API-AD-021 | POST         | `/v1/admin/merchants/{merchant_id}/complete-onboarding`            | staff auth + audit + no cross-tenant |
| API-AD-022 | GET,POST     | `/v1/admin/merchants/{merchant_id}/contacts`                       | staff auth + audit + no cross-tenant |
| API-AD-023 | DELETE,PATCH | `/v1/admin/merchants/{merchant_id}/contacts/{contact_id}`          | staff auth + audit + no cross-tenant |
| API-AD-024 | GET,POST     | `/v1/admin/merchants/{merchant_id}/contracts`                      | staff auth + audit + no cross-tenant |
| API-AD-025 | POST         | `/v1/admin/merchants/{merchant_id}/convert-to-customer`            | staff auth + audit + no cross-tenant |
| API-AD-026 | GET          | `/v1/admin/merchants/{merchant_id}/invoices`                       | staff auth + audit + no cross-tenant |
| API-AD-027 | GET          | `/v1/admin/merchants/{merchant_id}/locations`                      | staff auth + audit + no cross-tenant |
| API-AD-028 | GET          | `/v1/admin/merchants/{merchant_id}/onboarding`                     | staff auth + audit + no cross-tenant |
| API-AD-029 | GET          | `/v1/admin/merchants/{merchant_id}/orders`                         | staff auth + audit + no cross-tenant |
| API-AD-030 | POST         | `/v1/admin/merchants/{merchant_id}/owner-seat`                     | staff auth + audit + no cross-tenant |
| API-AD-031 | GET,PUT      | `/v1/admin/merchants/{merchant_id}/pricing`                        | staff auth + audit + no cross-tenant |
| API-AD-032 | GET          | `/v1/admin/merchants/{merchant_id}/privacy`                        | staff auth + audit + no cross-tenant |
| API-AD-033 | POST         | `/v1/admin/merchants/{merchant_id}/privacy/execute`                | staff auth + audit + no cross-tenant |
| API-AD-034 | POST         | `/v1/admin/merchants/{merchant_id}/recipients`                     | staff auth + audit + no cross-tenant |
| API-AD-035 | DELETE,PATCH | `/v1/admin/merchants/{merchant_id}/recipients/{recipient_id}`      | staff auth + audit + no cross-tenant |
| API-AD-036 | GET          | `/v1/admin/merchants/{merchant_id}/standing-orders`                | staff auth + audit + no cross-tenant |
| API-AD-037 | GET          | `/v1/admin/merchants/{merchant_id}/subsidiaries`                   | staff auth + audit + no cross-tenant |
| API-AD-038 | POST         | `/v1/admin/merchants/{merchant_id}/suspend`                        | staff auth + audit + no cross-tenant |
| API-AD-039 | GET          | `/v1/admin/merchants/{merchant_id}/tasks`                          | staff auth + audit + no cross-tenant |
| API-AD-040 | GET          | `/v1/admin/merchants/{merchant_id}/team`                           | staff auth + audit + no cross-tenant |
| API-AD-041 | POST         | `/v1/admin/merchants/{merchant_id}/team/seats`                     | staff auth + audit + no cross-tenant |
| API-AD-042 | DELETE,PATCH | `/v1/admin/merchants/{merchant_id}/team/{user_id}`                 | staff auth + audit + no cross-tenant |
| API-AD-043 | GET          | `/v1/admin/merchants/{merchant_id}/timeline`                       | staff auth + audit + no cross-tenant |

### 4.4 Shopify public + auth onboarding + notifications

| ID         | Methods   | Path                                                | P0 focus                             |
| ---------- | --------- | --------------------------------------------------- | ------------------------------------ |
| API-SH-001 | GET       | `/v1/integrations/shopify/callback`                 | HMAC/OAuth + quote/book side effects |
| API-SH-002 | POST      | `/v1/integrations/shopify/carrier-service/rates`    | HMAC/OAuth + quote/book side effects |
| API-SH-003 | GET       | `/v1/integrations/shopify/install`                  | HMAC/OAuth + quote/book side effects |
| API-SH-004 | POST      | `/v1/integrations/shopify/webhooks`                 | HMAC/OAuth + quote/book side effects |
| API-SH-005 | GET,POST  | `/v1/merchant/shopify`                              | HMAC/OAuth + quote/book side effects |
| API-SH-006 | GET       | `/v1/merchant/shopify/install-url`                  | HMAC/OAuth + quote/book side effects |
| API-SH-007 | DELETE    | `/v1/merchant/shopify/{shop_id}`                    | HMAC/OAuth + quote/book side effects |
| API-SH-008 | PUT       | `/v1/merchant/shopify/{shop_id}/pickup`             | HMAC/OAuth + quote/book side effects |
| API-OB-001 | GET       | `/v1/auth/merchant/onboarding`                      | Clerk + company file                 |
| API-OB-002 | PATCH     | `/v1/auth/merchant/onboarding/profile`              | Clerk + company file                 |
| API-OB-003 | PATCH     | `/v1/auth/merchant/onboarding/vertical`             | Clerk + company file                 |
| API-NT-001 | POST      | `/v1/notifications/devices/register`                | merchant principal scoping           |
| API-NT-002 | DELETE    | `/v1/notifications/devices/{device_id}`             | merchant principal scoping           |
| API-NT-003 | GET       | `/v1/notifications/inbox`                           | merchant principal scoping           |
| API-NT-004 | GET       | `/v1/notifications/inbox/history`                   | merchant principal scoping           |
| API-NT-005 | POST      | `/v1/notifications/inbox/mark-all-read`             | merchant principal scoping           |
| API-NT-006 | POST      | `/v1/notifications/inbox/{notification_id}/archive` | merchant principal scoping           |
| API-NT-007 | POST      | `/v1/notifications/inbox/{notification_id}/read`    | merchant principal scoping           |
| API-NT-008 | GET,PATCH | `/v1/notifications/preferences`                     | merchant principal scoping           |
| API-NT-009 | GET,PATCH | `/v1/notifications/settings`                        | merchant principal scoping           |

---

## 5. Handshake / integration suites

| ID             | P   | Systems               | Assert                                                                                    |
| -------------- | --- | --------------------- | ----------------------------------------------------------------------------------------- |
| HS-CLERK-001   | P0  | Clerk ↔ API ↔ portal  | JWKS verify; wrong portal secret rejected; dev bypass only when flags on                  |
| HS-CLERK-002   | P0  | Clerk org             | Org membership maps to MerchantUser; removed seat loses access                            |
| HS-FB-001      | P0  | FleetbaseAdapter      | Booking sync creates/updates Fleetbase order; RetryQueue drains                           |
| HS-FB-002      | P0  | merchant_sync_service | Merchant profile fields mirrored per Fleetbase-first policy                               |
| HS-FB-003      | P1  | VROOM via Fleetbase   | Multi-stop optimize for dispatch stays in adapter — portal optimize uses MapsService only |
| HS-VAL-001     | P0  | Valhalla :8002        | Booking preview distance/duration from Valhalla within GTA extract                        |
| HS-OSRM-001    | P0  | OSRM :5000            | With Valhalla stopped, preview still quotes via OSRM or explicit failure                  |
| HS-MAP-001     | P0  | Google Places/tiles   | Autocomplete works; assert no Distance Matrix calls in network log                        |
| HS-STRIPE-001  | P0  | Stripe Checkout       | Invoice/pay retail path unchanged                                                         |
| HS-STRIPE-002  | P0  | Connect COD           | Enable/connect; COD order settlement policy in billing_engine                             |
| HS-FCM-001     | P0  | Firebase FCM          | Token register; notification_engine delivers; unregister                                  |
| HS-MAIL-001    | P0  | Mailpit               | Onboarding, invoice remind, tracking-email, seat invite land in Mailpit                   |
| HS-REDIS-001   | P1  | Redis                 | Webhook delivery / rate-limit counters; worker event bus                                  |
| HS-PG-001      | P0  | Postgres 18           | Migrations apply; FKs from integrity migration hold                                       |
| HS-SHOP-001    | P0  | Shopify               | Install, webhook, carrier rates, cancel book loop                                         |
| HS-ERP-001     | P1  | NetSuite              | Connect/sync failure surfaces; secrets not logged                                         |
| HS-ERP-002     | P2  | Zapier/OAuth          | Template list; OAuth client secret once                                                   |
| HS-WH-001      | P0  | Outbound webhooks     | Signed delivery; retry sweeper; admin diagnostics                                         |
| HS-EVT-001     | P1  | EventBus/worker       | Merchant domain events consumed with idempotent handlers                                  |
| HS-SPICEDB-001 | P1  | SpiceDB               | require_module checks; no cached allow                                                    |

---

## 6. Models / DB / Docker / microservices

| ID         | P   | Kind      | Target                      | Assert                                                                          |
| ---------- | --- | --------- | --------------------------- | ------------------------------------------------------------------------------- |
| DB-ORM-001 | P1  | unit      | `Merchant`                  | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-002 | P1  | unit      | `MerchantUser`              | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-003 | P1  | unit      | `SavedAddress`              | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-004 | P1  | unit      | `MerchantRecipient`         | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-005 | P1  | unit      | `MerchantApiKey`            | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-006 | P1  | unit      | `MerchantWebhook`           | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-007 | P1  | unit      | `MerchantApiUsageLog`       | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-008 | P1  | unit      | `MerchantWebhookDelivery`   | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-009 | P1  | unit      | `BulkImportJob`             | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-010 | P1  | unit      | `MerchantAuditLog`          | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-011 | P1  | unit      | `MerchantBookingTemplate`   | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-012 | P1  | unit      | `StandingOrder`             | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-013 | P1  | unit      | `ShopifyShop`               | Constraints, nullability, cascade, status enums                                 |
| DB-ORM-014 | P1  | unit      | `ShopifyRateQuote`          | Constraints, nullability, cascade, status enums                                 |
| DB-ISO-001 | P0  | api       | tenant                      | Merchant A cannot read Merchant B orders/keys/invoices                          |
| DB-AUD-001 | P1  | api       | MerchantAuditLog            | Sensitive admin/portal mutations append audit                                   |
| DX-DOC-001 | P0  | handshake | compose                     | api:8001, valhalla:8002, osrm:5000, postgres, redis, mailpit, fleetbase healthy |
| DX-DOC-002 | P0  | contract  | image pins                  | No `:latest` for merchant-critical services                                     |
| DX-WRK-001 | P0  | handshake | worker                      | Shopify/webhook/Fleetbase retry jobs process                                    |
| DX-ENV-001 | P0  | contract  | clerk sync                  | `pnpm clerk:sync` populates merchant portal + API                               |
| MS-GW-001  | P1  | contract  | gateway_engine/merchant_api | Registry routes merchant-api consistently                                       |
| MS-MAP-001 | P0  | unit      | MapsService                 | Public methods only; no engine `_valhalla_*` calls                              |

---

## 7. Engine / service unit focus (merchant_engine + admin merchant)

| ID      | P   | Module                                   | Assert                               |
| ------- | --- | ---------------------------------------- | ------------------------------------ |
| SVC-001 | P1  | `profile_service`                        | update_profile projects company file |
| SVC-002 | P1  | `organization_sync`                      | tax/legal/branding projection        |
| SVC-003 | P1  | `activation_service`                     | signup policy + activate             |
| SVC-004 | P1  | `booking_service / booking_flow_service` | quote→book                           |
| SVC-005 | P1  | `route_import_service`                   | optimize via MapsService             |
| SVC-006 | P1  | `shopify_service`                        | book/cancel from payload             |
| SVC-007 | P1  | `integrations_service`                   | keys webhooks oauth                  |
| SVC-008 | P1  | `privacy`                                | export + erasure                     |
| SVC-009 | P1  | `standing_order_service`                 | recurrence create                    |
| SVC-010 | P1  | `invoice_reminder`                       | AP contact resolve + send            |
| SVC-011 | P1  | `team_service`                           | seats roles                          |
| SVC-012 | P1  | `reports_service`                        | report payloads                      |
| SVC-013 | P1  | `parcel_amend_service`                   | amend gates                          |
| SVC-014 | P1  | `webhook_delivery_service`               | retry/signing                        |
| SVC-015 | P1  | `fleetbase_engine.merchant_sync_service` | sync fields                          |
| SVC-016 | P1  | `admin merchant_lifecycle`               | approve/suspend/close                |
| SVC-017 | P1  | `admin merchant_org`                     | admin_merchant_context               |
| SVC-018 | P1  | `admin merchant360_service/board`        | detail/metrics payloads              |
| SVC-019 | P1  | `billing_engine ar + merchant_service`   | AR totals                            |
| SVC-020 | P1  | `pricing_engine repository`              | merchant rate card                   |
| SVC-021 | P1  | `notification_engine principal`          | merchant recipient resolve           |

---

## 8. UI component file matrix (admin + portal)

### Admin `components/merchants/*`

| ID                                | File                                    | Cases                                                                |
| --------------------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| UI-AD-MerchantBillingContactsCard | `MerchantBillingContactsCard.tsx`       | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantContactsPanel       | `MerchantContactsPanel.tsx`             | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantGtaMatrixFields     | `MerchantGtaMatrixFields.tsx`           | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantLocationsPanel      | `MerchantLocationsPanel.tsx`            | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantPricingFields       | `MerchantPricingFields.tsx`             | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantPricingPanel        | `MerchantPricingPanel.tsx`              | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantPrivacyCard         | `MerchantPrivacyCard.tsx`               | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantStandingOrdersCard  | `MerchantStandingOrdersCard.tsx`        | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-MerchantTeamPanel           | `MerchantTeamPanel.tsx`                 | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-RateCardPreview             | `RateCardPreview.tsx`                   | render · save success · validation · RBAC hide · optimistic rollback |
| UI-AD-AddSeat                     | `settings/.../AddMerchantSeatModal.tsx` | invite · duplicate email · role options                              |
| UI-AD-AR                          | `FinanceMerchantArPanel.tsx`            | preview · generate · error                                           |

### Portal component dirs

For each dir under `apps/merchant-portal/src/components/{auth,billing,booking,bulk,dashboard,help,integrations,onboarding,orders,referrals,reports,routes,settings,team,tracking,maps,nav}`:

| ID pattern    | Cases                                                                        |
| ------------- | ---------------------------------------------------------------------------- |
| UI-MP-<dir>-* | mount with fixture API · loading · empty · error · primary CTA · module gate |

---

## 9. Suggested implementation backlog (dev layer first)

**Sensors completed (2026-09-17):** Graphify (prior) → CodeGraph (`MapsService`, preview schemas, `MODULE_PERMISSIONS`) → Ripwire (`booking_preview`, `shopify` thin routers).

**Automation seed:** [`docs/testing/merchant_p0_registry.json`](testing/merchant_p0_registry.json)

```bash
pnpm test:merchant-p0:api    # pytest tests/merchant_p0 + arch pack
pnpm test:merchant-p0:e2e    # Playwright skeletons @p0 (needs portal + install)
pnpm test:merchant-p0        # both
```

1. **P0 contract pack** — NEG-ARCH-* (`test_merchant_matrix_p0_arch.py`) + handshake pack (`tests/merchant_p0/test_p0_handshakes.py`) — **landed**.
2. **P0 handshake pack** — MapsService Valhalla→OSRM labels, Clerk merchant triad, thin Shopify/booking routers — **landed**.
3. **P0 e2e pack** — Playwright skeletons for owner/dispatcher/accounting/viewer + admin AD-* merchant tabs — **stubs landed**; fill asserts with `MERCHANT_E2E_LIVE=1`.
4. **P1 fill gaps** — NetSuite/Zapier/OAuth, reports scheduled, privacy erasure, COD Connect.
5. **P2/P3** — chaos (Valhalla down, Fleetbase 500, Redis flush), a11y, soak webhook retries.

Do not blindly re-implement the 34 existing `test_merchant_*` files — extend via registry `covers` links.
---

## 10. Also covered (beyond the prompt)

SpiceDB module checks, EventBus/worker, Redis rate limits, Mailpit, webhook signing/retry, NetSuite + Zapier + OAuth clients, merchant-api key surface, COD Connect, sandbox commercial label, org membership switcher, standing orders, compliance dossier PDFs, data-moat, staff step-up for privacy, intentional-skip negatives (no hard DELETE, no Google routing, no in-engine VROOM).

Out of merchant persona scope (track separately): driver mobile verification, customer retail Checkout website GTM copy, Phase 2 CRM/AI flags.
