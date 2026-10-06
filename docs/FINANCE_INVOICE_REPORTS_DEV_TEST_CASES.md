# Finance · Invoice · Reports · Management — development test cases

> **Cutover (2026-10):** Fleetbase adapter and VROOM client are **removed**. POD → invoice
> stays PorterChain (`order.pod_completed` → `billing_engine`). Dispatch/GPS/day plan live in
> `dispatch_engine` + Redis. Ignore historical `FB-*` / FleetbaseClient rows below unless
> rewritten; SSOT is [ARCHITECTURE.md](../ARCHITECTURE.md).

**Status:** living catalog for local/CI development (not prod Doppler validation).  
**Mapped:** 2026-09-17 via Graphify (`query` / `explain` / `path` / `god-nodes`) → CodeGraph CLI `explore` → Ripwire (`--for` / `--callers` / `--expand` / `--impact`).  
**Architecture SSOT:** [ARCHITECTURE.md](../ARCHITECTURE.md) — `billing_engine` owns ledger/COD policy; Stripe SDK only in `porterchain_services/stripe/sdk.py`; PorterChain owns execution (POD → invoice trigger) and commercial money.  
**Charter:** Protect **money integrity**, **one AR total**, **tenant isolation** — never rebuild dispatch/POD/TSP inside finance.

### Sensor trail (this pass)

| Moment | Tool          | What it named                                                                                                                                                                                                                                                                                |
| ------ | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A      | Graphify      | Invoice community: `AdminFinanceService`, `SettlementService`, `finance_board`, `BillingLedgerEntry`, `MerchantReportsService`, `BillingClient`, FleetbaseClient modules, god nodes (`Settings`, `Order`, `MerchantContext`, `AdminContext`)                                                 |
| B      | CodeGraph CLI | `InvoiceService.finalize_after_pod` → `ensure_invoice` → attach document; `SettlementService` queue actions; `MapsService` Valhalla→OSRM; `NotificationRecord` blast radius; ServiceRegistry stripe/maps/notifications                                                                       |
| C      | Ripwire       | Thin `routers/admin/finance.py` (dashboard/reports/collections/GL/AR/remind/COD); merchant `billing.py` + `reports.py`; `overview_payload` / credit notes; impact: `SettlementService` → worker `process_billing` (radius_tested=3 / untested=7); FleetbaseAdapter → Orchestrator/POD/Orders |

**Sibling catalogs (do not duplicate blindly):**

| Doc                                                                            | Overlap                                                                                |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| [DEVELOPMENT_TEST_CASES_CATALOG.md](DEVELOPMENT_TEST_CASES_CATALOG.md)         | System-wide index (`PAY-*`, `NOTIF-*`, surfaces)                                       |
| [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md)     | Merchant billing/reports endpoint census                                               |
| [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md) | Fleetbase / Clerk / Shopify / ERP handshakes                                           |
| [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md)   | VROOM / Maps (feeds delivery → invoice)                                                |
| [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md)                           | Held: client-supplied invoice cents, scheduled report email, aging-as-dedicated-report |

**Existing coverage seed:**

| File                                                    | Focus                            |
| ------------------------------------------------------- | -------------------------------- |
| `apps/api/tests/test_billing_processor.py`              | Worker → `SettlementService`     |
| `apps/api/tests/test_invoice_detail_and_pay_all.py`     | Invoice detail + pay outstanding |
| `apps/api/tests/test_invoice_pdf_csv_cents.py`          | PDF/CSV ≡ GET cents              |
| `apps/api/tests/test_invoice_remind_pay_link.py`        | Remind → pay link                |
| `apps/api/tests/test_merchant_invoice_pay.py`           | Merchant Pay now                 |
| `apps/api/tests/test_merchant_billing_pack.py`          | Overview / remittance pack       |
| `apps/api/tests/test_merchant_reports.py`               | Merchant report payloads         |
| `apps/api/tests/test_collections_bl.py`                 | Collections chase order          |
| `apps/api/tests/test_one_ar_total_bd.py`                | One AR total SSOT                |
| `apps/api/tests/test_dod_quote_book_channel_invoice.py` | Quote≡Book≡channel≡invoice       |
| `apps/api/tests/test_shopify_billing_wave_remaining.py` | Shopify billing wave             |
| `apps/api/tests/test_stripe_*.py`                       | Checkout / COD / webhook         |
| `apps/api/tests/test_notification_*.py`                 | Push / email / SLI               |
| `apps/api/tests/test_fleetbase_*.py`                    | Adapter / sync / webhook         |
| `apps/api/tests/services/test_aux_service_coverage.py`  | Settlement action smoke          |
| `scripts/verify_notifications_billing_depth.py`         | Billing↔notif depth gate         |

---

## 0. ID scheme & layers

| Prefix     | Layer                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------------ |
| `A-FIN-*`  | Admin Finance Center UI `:3002` `/finance` tabs + invoice detail                                 |
| `A-MGT-*`  | Admin management surfaces touching money (merchants 360, support finance, settings, diagnostics) |
| `M-BIL-*`  | Merchant portal Billing `:3001` `/billing` tabs + invoice detail                                 |
| `M-RPT-*`  | Merchant portal Reports `/reports`                                                               |
| `C-UI-*`   | Customer portal invoices/receipts (adjacent)                                                     |
| `D-FIN-*`  | Driver earnings / payouts (wallet ledger)                                                        |
| `API-AF-*` | Staff `/v1/admin/finance/*`                                                                      |
| `API-MB-*` | Merchant `/v1/merchant/billing/*`                                                                |
| `API-MR-*` | Merchant `/v1/merchant/reports/*`                                                                |
| `API-AM-*` | Admin merchant org invoices / billing-contacts / lifecycle money                                 |
| `ENG-*`    | `AdminFinanceService`, `finance_board`, `InvoiceService`, `SettlementService`, AR, credit notes  |
| `WRK-*`    | Worker billing processor / EventBus invoice events                                               |
| `PAY-*`    | Stripe Checkout / COD Connect / webhooks                                                         |
| `FB-*`     | Fleetbase POD → `order.pod_completed` → invoice finalize handshake                               |
| `MAP-*`    | Valhalla/OSRM distance feeding priced invoices (not Google routing)                              |
| `VRM-*`    | VROOM via Fleetbase only (delivery complete → invoice path)                                      |
| `AUTH-*`   | Clerk portals · staff IdP · `finance_read` / `finance` · step-up                                 |
| `NOTIF-*`  | Invoice remind email · FCM · Mailpit · finance audience                                          |
| `SHOP-*`   | Shopify carrier quote → book → invoice channel                                                   |
| `INT-*`    | Partner API / NetSuite / Zapier / ERP-shaped ingest                                              |
| `DB-*`     | `Invoice`, `Payment`, `BillingLedgerEntry`, `CreditNote`, `InvoiceLine`, Alembic                 |
| `DOC-*`    | Docker Postgres/Redis/Mailpit/Valhalla/OSRM/VROOM/Fleetbase                                      |
| `ARCH-*`   | Ownership laws, thin-router waves, OpenAPI census, verify scripts                                |
| `DIAG-*`   | System-tests / e2e_validation finance & billing surfaces                                         |
| `UX-*`     | Cross-links, empty states, cents formatting, CSV/PDF parity                                      |
| `HS-*`     | End-to-end handshakes across systems                                                             |

**Priority:** P0 = ship-blocker (money/authz/integrity) · P1 = trust/collections/ops · P2 = polish/exports · P3 = held / Phase-2 per intentional skips.

Each case: **Precondition → Steps → Expected → Layer tags**.

---

## 1. Canonical money handshake map (Graphify SSOT)

```
Retail/Merchant book ──Stripe Checkout / COD policy──► Payment(SUCCEEDED)
        │
Order execution ──Fleetbase adapter (orders/drivers/POD)──► order.pod_completed
        │
SettlementService (worker billing queue)
        │ action=finalize_after_pod
InvoiceService.finalize_after_pod → ensure_invoice + OrderState.INVOICED
        │ INVOICE_CREATED / order.invoiced events
        ▼
notification_engine (email + push) ──Mailpit local / FCM──► customer·merchant·finance
        │
Admin Finance Center / Merchant Billing / Merchant Reports
        │  one AR total (merchant_ar + Invoice outstanding − credits)
        ▼
GL export / collections / credit notes / COD queue / driver payouts
```

**Ownership split (must stay true):**

| Concern                                       | Owner                                               | Forbidden                            |
| --------------------------------------------- | --------------------------------------------------- | ------------------------------------ |
| POD / dispatch / GPS / vehicles               | Fleetbase via adapter                               | Rebuild in `admin_engine` finance    |
| Invoice create / AR / ledger / COD **policy** | `billing_engine` + `InvoiceService`                 | Client-supplied amount cents         |
| Stripe SDK HTTP                               | `porterchain_services/stripe/sdk.py`                | `import stripe` elsewhere            |
| Distance for priced invoices                  | Valhalla → OSRM via `MapsService`                   | Google Distance Matrix               |
| Multi-stop TSP before delivery                | VROOM via Fleetbase orchestrator                    | PC VROOM HTTP client                 |
| Reports aggregates                            | `merchant_engine/reports_service` + `finance_board` | Second reporting warehouse in portal |

**God nodes (regression magnets):** `Settings`, `Order`, `MerchantContext`, `AdminContext`, `Merchant`, `require_module`, `OrderState`.

---

## 2. Surface inventory (every page / subpage / file)

### 2.1 Admin Finance Center (`apps/admin`) — `/finance`

| Tab / sub-surface | Files                                                                                                                 | APIs                                                            |
| ----------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Shell + tabs      | `app/(ops)/finance/page.tsx` — Tabs: overview, invoices, payments, payouts, collections, merchant-ar, ledger, reports | `financeApi.*` in `lib/finance.ts`                              |
| Overview          | same page                                                                                                             | `GET /finance/dashboard`, `/finance/summary`                    |
| Invoices grid     | `components/finance/FinanceInvoicesGrid.tsx`                                                                          | `GET /finance/invoices`                                         |
| Invoice detail    | `app/(ops)/finance/invoices/[id]/page.tsx`, `FinanceInvoiceDetailView.tsx`                                            | `GET …/invoices/{id}`, `POST …/record-payment`, `POST …/remind` |
| Payments          | `FinancePaymentsGrid.tsx`                                                                                             | `GET /finance/payments`                                         |
| Payouts           | page tab                                                                                                              | `GET /finance/payouts`                                          |
| Collections       | `FinanceCollectionsPanel.tsx`                                                                                         | `GET /finance/collections`                                      |
| Merchant AR       | `FinanceMerchantArPanel.tsx`                                                                                          | `GET …/merchant-ar/preview`, `POST …/generate`                  |
| Ledger            | page tab                                                                                                              | `GET /finance/ledger`                                           |
| Reports + GL      | page tab + export                                                                                                     | `GET /finance/reports`, `GET /finance/export`                   |
| COD queue         | collections/COD                                                                                                       | `GET /finance/cod`                                              |
| Duplicates        | (API-backed)                                                                                                          | `GET /finance/duplicates`                                       |
| Credit notes      | write path                                                                                                            | `POST /finance/credit-notes` (+ step-up)                        |

### 2.2 Admin management surfaces (money-adjacent)

| Surface              | Files                                                                      | Money relevance                                 |
| -------------------- | -------------------------------------------------------------------------- | ----------------------------------------------- |
| Merchants list       | `app/(ops)/merchants/page.tsx`                                             | AR badges / status                              |
| Merchant 360 Billing | `merchants/[id]/page.tsx` tabs `money` / panels invoices·credits·statement | Invoices, remind, AR, convert/close gated on AR |
| Billing contacts     | `MerchantBillingContactsCard.tsx`                                          | Remind recipients                               |
| Pricing / GTA        | `MerchantPricing*`, `/pricing`                                             | Feeds invoice amounts                           |
| Standing orders      | `MerchantStandingOrdersCard.tsx`                                           | Recurring billables                             |
| Support → finance    | `support/page.tsx` module tab `finance`                                    | Ticket↔invoice status                           |
| Claims               | `/claims`                                                                  | Refunds → credit notes / reverse logistics      |
| Operations           | `/operations` + PushHealthStrip                                            | Post-POD invoice events / push health           |
| Notifications        | `/notifications`                                                           | Finance audience                                |
| Settings             | SettingsCenter / Integration / EnvOwned                                    | Stripe, Mailpit, Firebase, Clerk                |
| System / diagnostics | SystemCenter, DiagnosticsTestCenter, `/system-tests`                       | Billing/finance consistency surfaces            |
| Account security     | `/account/security`                                                        | Staff step-up for money writes                  |
| Dashboard            | `/dashboard`                                                               | Revenue widgets vs finance dashboard parity     |

### 2.3 Merchant portal (`apps/merchant-portal`)

| Surface                     | Files                                                      | Tabs / notes                                                                         |
| --------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Billing                     | `app/(portal)/billing/page.tsx`, `BillingClient.tsx`       | overview, invoices, statement, payments, credits, history, tax, rates, contacts, cod |
| Invoice detail              | `billing/invoices/[invoice_id]`, `InvoiceDetailClient.tsx` | Pay now / PDF / remind                                                               |
| Rate card                   | `RateCardPanel.tsx`                                        | Contract pricing                                                                     |
| Billing contacts            | `BillingContactsPanel.tsx`                                 | AP contacts                                                                          |
| Reports                     | `app/(portal)/reports/page.tsx`, `ReportsClient.tsx`       | executive, delivery, invoices, claims, saved                                         |
| Settings (billing contacts) | settings panels                                            | Must not own invoice write                                                           |
| Shopify                     | `/shopify`                                                 | Carrier → book → invoice channel                                                     |
| Orders / track              | orders, track                                              | Delivered → expect invoice in Billing                                                |
| Client libs                 | `lib/billing.ts`, `lib/reports.ts`                         | Contract shapes                                                                      |

### 2.4 API routers (thin — Wave 17/45/50)

| Family           | File                                        | Handlers                                                                                                                                                                                  |
| ---------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Admin finance    | `routers/admin/finance.py`                  | dashboard, reports, collections, export, invoices(+detail), payments, payouts, ledger, duplicates, credit-notes, merchant-ar preview/generate, record-payment, remind, summary, cod       |
| Merchant billing | `routers/merchant/billing.py`               | overview, statement(+detail), invoices(+pdf/remind/pay), pay-outstanding, payments, credit-notes, history, tax, contract, rate-card, CSV exports, COD status/connect/enable               |
| Merchant reports | `routers/merchant/reports.py`               | summary, overview, executive, delivery-performance, order-volume, invoices, drivers, vehicles, destinations, claims, sla-history, switching-costs, saved CRUD, scheduled, export csv/xlsx |
| Admin merchants  | `routers/merchants.py`                      | invoices, credit-notes, billing-contacts (compose via `merchant_org` / lifecycle)                                                                                                         |
| Shopify          | `routers/shopify.py`, `merchant/shopify.py` | Carrier rates + OAuth (priced, not VROOM)                                                                                                                                                 |

### 2.5 Engines / models / worker

| Piece                 | Path                                                                   |
| --------------------- | ---------------------------------------------------------------------- |
| Admin finance writes  | `admin_engine/finance_service.py`                                      |
| Admin finance reads   | `admin_engine/finance_board.py`                                        |
| Merchant AR           | `admin_engine/merchant_ar_service.py`                                  |
| Invoice lifecycle     | `booking_engine/invoice_service.py`                                    |
| Settlement / ledger   | `billing_engine/settlement_service.py`, `models.py`                    |
| AR helpers            | `billing_engine/ar.py`                                                 |
| Credit notes          | `billing_engine/credit_notes.py`                                       |
| Invoice PDF/doc       | `billing_engine/invoice_document.py`                                   |
| COD policy            | `billing_engine/stripe_cod_service.py`                                 |
| Merchant billing pack | `merchant_engine/billing_service.py`, `billing_pack.py`                |
| Merchant reports      | `merchant_engine/reports_service.py`                                   |
| Shopify               | `merchant_engine/shopify_service.py`, `integrations/shopify_orders.py` |
| Worker                | `apps/worker/processors/billing.py`                                    |
| Fleetbase bridge      | `services/fleetbase-adapter/.../{orders,pod,drivers,orchestrator}`     |
| Maps                  | `services/python/porterchain_services/maps/service.py`                 |
| Notifications         | `notification_engine/*`, booking `notification_service.py`             |
| Schemas               | `schemas_admin.py` Finance*, `schemas_merchant.py` Billing*/Report*    |

---

## 3. Admin Finance UI (`A-FIN-*`)

| ID        | P   | Precondition                 | Steps                           | Expected                                                                           |
| --------- | --- | ---------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| A-FIN-001 | P0  | Staff with `finance_read`    | Open `/finance`                 | Default tab overview; all 8 tabs render without crash                              |
| A-FIN-002 | P0  | Signed out                   | Hit `/finance`                  | Redirect / gate (AdminAccessGate) — no data leak                                   |
| A-FIN-003 | P0  | Dev bypass                   | Load overview                   | Dashboard KPIs: today/month revenue, outstanding/paid, overdue, payouts            |
| A-FIN-004 | P0  | Invoices exist               | Tab Invoices                    | Grid shows #, status styles, link to `/finance/invoices/{id}`                      |
| A-FIN-005 | P0  | Invoice id valid             | Open detail                     | Lines, tax, fees, channel/pricing_model if present; outstanding cents              |
| A-FIN-006 | P0  | Open invoice                 | Record payment (step-up)        | Status → paid; ledger entry; audit log                                             |
| A-FIN-007 | P0  | Open invoice                 | Remind                          | Mailpit message + pay link; no double-send storm                                   |
| A-FIN-008 | P1  | Many invoices                | Search/group/CSV export on grid | CSV cents match GET detail                                                         |
| A-FIN-009 | P1  | Overdue set                  | Collections tab                 | Chase order by aging; AP contact present when configured                           |
| A-FIN-010 | P0  | Merchant with cycle          | Merchant AR preview → generate  | InvoiceLine(s); one AR total unchanged across surfaces                             |
| A-FIN-011 | P1  | Payments exist               | Payments tab filters            | Pagination; sandbox excluded from live totals                                      |
| A-FIN-012 | P1  | Pending payouts              | Payouts tab                     | Pending sum matches dashboard pending_payouts                                      |
| A-FIN-013 | P1  | Ledger entries               | Ledger tab                      | `BillingLedgerEntry` kinds visible (payment_settled, finalize_after_pod, stripe_*) |
| A-FIN-014 | P1  | Data present                 | Reports tab                     | Payload keys stable; GL export downloadable                                        |
| A-FIN-015 | P1  | COD orders                   | COD queue                       | Matches `StripeCodService.list_collection_queue`                                   |
| A-FIN-016 | P2  | Dupes seeded                 | Duplicates API reflected        | No silent merge                                                                    |
| A-FIN-017 | P1  | Credit note write            | POST credit note with step-up   | Reduces outstanding; merchant portal credits tab updates                           |
| A-FIN-018 | P0  | Role without finance         | Open `/finance`                 | 403 / module deny — no KPI leak                                                    |
| A-FIN-019 | P1  | `?tab=merchant-ar` deep link | Navigate                        | Tab selected; URL sync                                                             |
| A-FIN-020 | P2  | Empty DB                     | All tabs                        | Empty states, not spinner forever                                                  |

**UX tags:** `UX-FIN-001` cents always via shared formatter; `UX-FIN-002` status chips use `INVOICE_STATUS_STYLES`; `UX-FIN-003` remind button disabled while in-flight.

---

## 4. Admin management money surfaces (`A-MGT-*`)

| ID        | P   | Surface                   | Case                                                                          |
| --------- | --- | ------------------------- | ----------------------------------------------------------------------------- |
| A-MGT-001 | P0  | Merchants 360 `tab=money` | Invoices panel lists ops AR; link to Finance detail                           |
| A-MGT-002 | P0  | Money → remind            | Same remind path as Finance (step-up)                                         |
| A-MGT-003 | P0  | Close merchant with AR    | Blocked until collect/write-off path                                          |
| A-MGT-004 | P0  | Convert with AR           | Confirm write-off or collect first                                            |
| A-MGT-005 | P1  | Billing contacts card     | CRUD; used as remind recipient                                                |
| A-MGT-006 | P1  | Pricing → book → invoice  | Rate card / GTA matrix reflected on invoice lines                             |
| A-MGT-007 | P1  | Standing orders           | Generate cycle includes standing billables                                    |
| A-MGT-008 | P1  | Support finance tab       | Invoice status on ticket uses `platform/invoice_status`                       |
| A-MGT-009 | P1  | Claims → refund           | Credit note / refund event; reports claims slice updates                      |
| A-MGT-010 | P1  | Operations after POD      | Invoice event; finance dashboard outstanding moves                            |
| A-MGT-011 | P1  | Notifications page        | Finance audience rows for invoice.remind / paid                               |
| A-MGT-012 | P0  | Settings integrations     | Stripe/Mailpit/Firebase/Clerk health; finance still works if Google Maps down |
| A-MGT-013 | P1  | System-tests              | Consistency surfaces include `billing`, `finance`, `reports`                  |
| A-MGT-014 | P1  | Dashboard widgets         | Revenue cents align with finance dashboard (sandbox excluded)                 |
| A-MGT-015 | P2  | OpenFleetbaseButton       | Console opens; money stays in PC (no Fleetbase invoice SSOT)                  |

---

## 5. Merchant Billing UI (`M-BIL-*`)

| ID        | P   | Tab / page           | Case                                                    |
| --------- | --- | -------------------- | ------------------------------------------------------- |
| M-BIL-001 | P0  | overview             | AR + remittance pack + headroom from `overview_payload` |
| M-BIL-002 | P0  | invoices             | List; open `/billing/invoices/{id}`                     |
| M-BIL-003 | P0  | invoice detail       | Line items; Pay now; PDF download                       |
| M-BIL-004 | P0  | Pay outstanding      | Pays all open; amounts server-locked                    |
| M-BIL-005 | P0  | IDOR                 | Merchant A token cannot GET B invoice/PDF               |
| M-BIL-006 | P1  | statement (+detail)  | Totals ≡ one AR; CSV export                             |
| M-BIL-007 | P1  | payments             | History matches Stripe settlements                      |
| M-BIL-008 | P1  | credits              | Credit notes list; reduce outstanding                   |
| M-BIL-009 | P1  | history / tax        | Tax summary cents ≡ invoice tax sum                     |
| M-BIL-010 | P1  | rates                | Rate card read-only vs admin pricing                    |
| M-BIL-011 | P1  | contacts             | AP contacts CRUD; remind uses them                      |
| M-BIL-012 | P0  | COD                  | status / connect / enable; Checkout path unbroken       |
| M-BIL-013 | P1  | CSV exports          | invoices/statement/history CSV ≡ GET                    |
| M-BIL-014 | P1  | Sandbox orders       | Excluded from live AR (flag `is_sandbox`)               |
| M-BIL-015 | P2  | Deep link `?tab=cod` | From admin merchant 360                                 |
| M-BIL-016 | P0  | Auth                 | Clerk merchant org + `X-Merchant-Id` switcher           |

---

## 6. Merchant Reports UI (`M-RPT-*`)

| ID        | P   | Case                                                                                                                         |
| --------- | --- | ---------------------------------------------------------------------------------------------------------------------------- |
| M-RPT-001 | P0  | `/reports` loads; tabs executive / delivery / invoices / claims / saved                                                      |
| M-RPT-002 | P0  | Executive + overview + summary authz + schema                                                                                |
| M-RPT-003 | P0  | Delivery performance after completed Fleetbase POD                                                                           |
| M-RPT-004 | P0  | Invoices report aligns with Billing invoices totals                                                                          |
| M-RPT-005 | P1  | Order volume / drivers / vehicles / destinations                                                                             |
| M-RPT-006 | P1  | Claims + SLA history after claim lifecycle                                                                                   |
| M-RPT-007 | P1  | Switching-costs stable (data moat)                                                                                           |
| M-RPT-008 | P1  | Export CSV/XLSX each `report_type` (503 if Excel missing — graceful)                                                         |
| M-RPT-009 | P1  | Saved reports CRUD                                                                                                           |
| M-RPT-010 | P3  | Scheduled reports store rows; **email delivery held** (`scheduled_email_available: false`) — assert flag, do not fail as bug |
| M-RPT-011 | P0  | Tenant isolation on all report endpoints                                                                                     |
| M-RPT-012 | P2  | Empty merchant — zeros / empty charts, not 500                                                                               |

---

## 7. Admin Finance API (`API-AF-*`)

For **every** endpoint in `routers/admin/finance.py`, run the matrix:

| Variant                              | Expect                                    |
| ------------------------------------ | ----------------------------------------- |
| Happy path (finance_read or finance) | 200 + schema                              |
| Missing auth                         | 401                                       |
| Wrong module                         | 403                                       |
| Staff step-up missing on writes      | 401/403 per `enforce_staff_step_up`       |
| Sandbox pollution                    | Live aggregates ignore `Order.is_sandbox` |

| ID         | P   | Endpoint                             | Extra asserts                                                       |
| ---------- | --- | ------------------------------------ | ------------------------------------------------------------------- |
| API-AF-001 | P0  | `GET /finance/dashboard`             | Keys match `FinanceDashboardResponse` / admin `FinanceDashboard` TS |
| API-AF-002 | P0  | `GET /finance/reports`               | Stable keys from `reports_payload`                                  |
| API-AF-003 | P0  | `GET /finance/collections`           | Aging + AP contact fields                                           |
| API-AF-004 | P1  | `GET /finance/export`                | GL rows reconcilable to ledger                                      |
| API-AF-005 | P0  | `GET /finance/invoices`              | Pagination filters                                                  |
| API-AF-006 | P0  | `GET /finance/invoices/{id}`         | 404 unknown; detail SOT                                             |
| API-AF-007 | P0  | `GET /finance/payments`              | Page filters                                                        |
| API-AF-008 | P1  | `GET /finance/payouts`               | Status filter                                                       |
| API-AF-009 | P1  | `GET /finance/ledger`                | Ledger kinds                                                        |
| API-AF-010 | P2  | `GET /finance/duplicates`            | Structured list                                                     |
| API-AF-011 | P0  | `POST /finance/credit-notes`         | Step-up + finance module + audit                                    |
| API-AF-012 | P0  | `GET /finance/merchant-ar/preview`   | Preview ≠ mutate                                                    |
| API-AF-013 | P0  | `POST /finance/merchant-ar/generate` | Idempotent-ish; InvoiceLine channel                                 |
| API-AF-014 | P0  | `POST …/record-payment`              | Amount server-side; audit                                           |
| API-AF-015 | P0  | `POST …/remind`                      | Notification + Mailpit                                              |
| API-AF-016 | P1  | `GET /finance/summary`               | Subset of dashboard                                                 |
| API-AF-017 | P1  | `GET /finance/cod`                   | COD queue                                                           |

---

## 8. Merchant Billing / Reports API (`API-MB-*` / `API-MR-*`)

Reuse census in [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md) (`API-MP-007`…`023`, `API-MP-092`…`108`). Depth add-ons:

| ID         | P   | Case                                                                              |
| ---------- | --- | --------------------------------------------------------------------------------- |
| API-MB-001 | P0  | Pay body cannot override `amount_cents` (intentional skip: client-supplied cents) |
| API-MB-002 | P0  | PDF bytes / CSV cents ≡ GET detail                                                |
| API-MB-003 | P0  | Remind requires billing module role                                               |
| API-MB-004 | P1  | COD connect returns Stripe Connect URL; enable flips flag in merchant_engine      |
| API-MB-005 | P1  | Contract + rate-card read paths                                                   |
| API-MR-001 | P0  | All report GETs return merchant-scoped aggregates only                            |
| API-MR-002 | P1  | Unknown `report_type` export → 4xx                                                |
| API-MR-003 | P2  | XLSX dependency missing → 503 with clear detail                                   |

---

## 9. Engines (`ENG-*`)

| ID      | P   | Unit                                            | Case                                                                                            |
| ------- | --- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| ENG-001 | P0  | `InvoiceService.finalize_after_pod`             | Only from `POD_COMPLETED`; idempotent if already `INVOICED`                                     |
| ENG-002 | P0  | `ensure_invoice`                                | Creates number/receipt; attaches document; emits `INVOICE_CREATED`                              |
| ENG-003 | P0  | `manual_invoice`                                | Admin/ops path commits when `commit=True`                                                       |
| ENG-004 | P0  | `SettlementService`                             | Actions: `payment_settled`, `payment_succeeded`, `finalize_after_pod`; unknown → ignored ledger |
| ENG-005 | P0  | `finance_board.dashboard_payload`               | Sandbox excluded; tax/payouts math                                                              |
| ENG-006 | P0  | `AdminFinanceService.remind_invoice`            | Resolves AP contact; notification_engine                                                        |
| ENG-007 | P0  | `MerchantArService.generate` / `record_payment` | One AR total with statement                                                                     |
| ENG-008 | P0  | `issue_credit_note`                             | Ledger + outstanding                                                                            |
| ENG-009 | P1  | `billing_pack.overview_payload`                 | Headroom / remittance                                                                           |
| ENG-010 | P1  | `MerchantReportsService.*`                      | Each report method schema                                                                       |
| ENG-011 | P1  | `StripeCodService.list_collection_queue`        | Router thin (Wave 17)                                                                           |
| ENG-012 | P0  | **Anti-case**                                   | No `db.query` left in `routers/admin/finance.py`                                                |
| ENG-013 | P0  | **Anti-case**                                   | Finance does not call Google for distance                                                       |
| ENG-014 | P0  | **Anti-case**                                   | No PC VROOM client under `*_engine`                                                             |
| ENG-015 | P1  | `attach_invoice_document`                       | Blocked doc hosts rejected                                                                      |

---

## 10. Worker / EventBus (`WRK-*`)

| ID      | P   | Case                                                                                                                           |
| ------- | --- | ------------------------------------------------------------------------------------------------------------------------------ |
| WRK-001 | P0  | `process_billing` delegates to `SettlementService`                                                                             |
| WRK-002 | P0  | `finalize_after_pod` job → invoice + ledger ok                                                                                 |
| WRK-003 | P0  | `payment_settled` / stripe success → ledger                                                                                    |
| WRK-004 | P0  | Required events: `payment.succeeded`, `order.pod_completed`, `order.invoiced`, `invoice` created aliases per `REQUIRED_EVENTS` |
| WRK-005 | P1  | Retry / poison: failed finalize does not double-invoice on success retry (idempotent ensure)                                   |
| WRK-006 | P1  | Queue drain in `apps/worker/run.py` still routes billing                                                                       |

---

## 11. Stripe / payments (`PAY-*` depth for this domain)

| ID          | P   | Case                                                             |
| ----------- | --- | ---------------------------------------------------------------- |
| PAY-FIN-001 | P0  | Checkout webhook idempotent; invoice/payment consistent          |
| PAY-FIN-002 | P0  | Signature fail → no ledger write                                 |
| PAY-FIN-003 | P0  | COD Connect additive; prepaid Checkout still green               |
| PAY-FIN-004 | P1  | Merchant Pay now → Stripe session → settle → `invoice.paid` path |
| PAY-FIN-005 | P1  | Pay all outstanding                                              |
| PAY-FIN-006 | P0  | Only `porterchain_services/stripe/sdk.py` imports stripe         |
| PAY-FIN-007 | P1  | Refund / reverse logistics → credit or refunded payment status   |

---

## 12. Fleetbase handshake (`FB-*`) — execution → invoice

| ID         | P   | Case                                                                    |
| ---------- | --- | ----------------------------------------------------------------------- |
| FB-FIN-001 | P0  | POD upload via adapter → PC receives pod_completed → invoice            |
| FB-FIN-002 | P0  | Fleetbase offline: order stuck pre-invoice; finance shows no false paid |
| FB-FIN-003 | P0  | Adapter circuit open: billing jobs queue; no silent drop                |
| FB-FIN-004 | P1  | Driver/order sync ids present before finalize                           |
| FB-FIN-005 | P1  | Ops mirror refresh does not invent invoices                             |
| FB-FIN-006 | P0  | **Anti-case:** Fleetbase is not invoice SSOT; PC `Invoice` row is       |
| FB-FIN-007 | P1  | Cancel on Fleetbase → no finalize invoice (or void path)                |
| FB-FIN-008 | P2  | Manifest/route complete multi-stop → each order invoiced once           |

---

## 13. Maps · Valhalla · OSRM · Google · VROOM (`MAP-*` / `VRM-*`)

| ID          | P   | Case                                                                   |
| ----------- | --- | ---------------------------------------------------------------------- |
| MAP-FIN-001 | P0  | Priced invoice distance from Valhalla (OSRM fallback)                  |
| MAP-FIN-002 | P0  | Google Maps down → Places UX degrades; **pricing/invoice still works** |
| MAP-FIN-003 | P0  | **Anti-case:** Google Distance Matrix never used for invoice amount    |
| VRM-FIN-001 | P1  | Optimize/commit (Fleetbase VROOM) → delivery → invoice path intact     |
| VRM-FIN-002 | P0  | Diagnostics VROOM probe via orchestrator engines only                  |

---

## 14. Auth · Clerk · RBAC · step-up (`AUTH-*`)

| ID           | P   | Case                                                              |
| ------------ | --- | ----------------------------------------------------------------- |
| AUTH-FIN-001 | P0  | Admin Clerk JWT / staff IdP for finance routes                    |
| AUTH-FIN-002 | P0  | Merchant Clerk + org membership + `X-Merchant-Id`                 |
| AUTH-FIN-003 | P0  | `finance_read` vs `finance` write separation                      |
| AUTH-FIN-004 | P0  | Staff step-up on credit-note, AR generate, record-payment, remind |
| AUTH-FIN-005 | P0  | Cross-merchant IDOR on all money GETs                             |
| AUTH-FIN-006 | P1  | Dev bypass local only; never in prod settings                     |
| AUTH-FIN-007 | P1  | SpiceDB / module matrix for merchant billing roles                |

---

## 15. Notifications · email · FCM · Firebase (`NOTIF-*`)

| ID            | P   | Case                                                                                           |
| ------------- | --- | ---------------------------------------------------------------------------------------------- |
| NOTIF-FIN-001 | P0  | Invoice created → email to customer/merchant (Mailpit local)                                   |
| NOTIF-FIN-002 | P0  | Remind → Mailpit + pay link                                                                    |
| NOTIF-FIN-003 | P1  | Finance audience in `NOTIFICATION_AUDIENCES`                                                   |
| NOTIF-FIN-004 | P1  | Admin FCM / firebase-messaging-sw for paid/overdue ops alerts                                  |
| NOTIF-FIN-005 | P1  | Push health strip after billing events                                                         |
| NOTIF-FIN-006 | P0  | Firebase failure scenario does not corrupt invoice state                                       |
| NOTIF-FIN-007 | P1  | Preference opt-outs respected for marketing; transactional invoice still sends (policy assert) |
| NOTIF-FIN-008 | P2  | ZeptoMail HTTPS path unit (non-local)                                                          |

---

## 16. Shopify · ERP · partner (`SHOP-*` / `INT-*`)

| ID           | P   | Case                                                            |
| ------------ | --- | --------------------------------------------------------------- |
| SHOP-FIN-001 | P0  | Carrier rates → quote_id → book → invoice channel/pricing_model |
| SHOP-FIN-002 | P0  | Quote≡Book≡channel≡invoice (DoD)                                |
| SHOP-FIN-003 | P1  | Shopify billing wave remaining pytest green                     |
| SHOP-FIN-004 | P1  | Rate limit / OAuth hijack blocks                                |
| INT-FIN-001  | P1  | NetSuite/Zapier ingest does not bypass pricing/invoice engines  |
| INT-FIN-002  | P1  | Partner API book → same invoice finalize path                   |
| INT-FIN-003  | P2  | ERP webhook signature fail → no ledger                          |
| INT-FIN-004  | P3  | Future ERP invoice export — document only until product         |

**Missed items you asked to cover (explicitly added):**

| Area                                    | Case IDs                                                     |
| --------------------------------------- | ------------------------------------------------------------ |
| Redis restart mid-billing job           | DOC-FIN-004 + WRK-005                                        |
| Postgres restart                        | DOC-FIN-005                                                  |
| WebSocket / realtime inbox              | NOTIF-FIN-005 + admin notifications page                     |
| SpiceDB                                 | AUTH-FIN-007                                                 |
| Prometheus commerce metrics             | DIAG-FIN-003 (`shopify_quote`, `invoice_pay`, `ar_mismatch`) |
| Privacy DSR vs invoices                 | ARCH-FIN-004 (redact/export policy)                          |
| Investor / platform metrics             | A-MGT-014 adjacent — revenue not double-count sandbox        |
| CRM reports mixin                       | ENG-010 adjacent `collaboration_engine/crm_reports`          |
| Driver wallet / payouts                 | D-FIN below                                                  |
| Website retail prepaid                  | PAY-FIN-001                                                  |
| Customer portal receipt                 | C-UI-FIN-001                                                 |
| Mobile driver handshake (no invoice UI) | FB-FIN-001 only — money stays server                         |

---

## 17. Driver finance (`D-FIN-*`)

| ID        | P   | Case                                                               |
| --------- | --- | ------------------------------------------------------------------ |
| D-FIN-001 | P1  | Driver payout list on admin payouts tab                            |
| D-FIN-002 | P1  | Wallet ledger ownership (`driver_finance_service` / driver_engine) |
| D-FIN-003 | P1  | Earnings service does not invent invoices                          |
| D-FIN-004 | P2  | Mobile/driver portal shows earnings only — no merchant AR          |

---

## 18. Customer adjacent (`C-UI-*`)

| ID           | P   | Case                                                     |
| ------------ | --- | -------------------------------------------------------- |
| C-UI-FIN-001 | P1  | Customer sees receipt/invoice after retail prepaid + POD |
| C-UI-FIN-002 | P0  | Customer cannot access merchant AR / admin finance       |
| C-UI-FIN-003 | P1  | Refund request → admin/claims → credit path              |

---

## 19. Database · models · migrations (`DB-*`)

| ID         | P   | Case                                                                          |
| ---------- | --- | ----------------------------------------------------------------------------- |
| DB-FIN-001 | P0  | `Invoice` unique per order (ensure idempotent)                                |
| DB-FIN-002 | P0  | `Payment` status enum transitions                                             |
| DB-FIN-003 | P0  | `BillingLedgerEntry` written for settlement actions                           |
| DB-FIN-004 | P0  | `CreditNote` / `InvoiceLine` FKs (integrity migrations)                       |
| DB-FIN-005 | P0  | `Order.is_sandbox` excluded from live finance aggregates                      |
| DB-FIN-006 | P1  | Alembic `u3v4w5x6y7z8_invoice_document` and billing-related heads apply clean |
| DB-FIN-007 | P0  | Tenant: `merchant_id` on invoice enforced in queries                          |
| DB-FIN-008 | P1  | Currency default `cad`; tax_cents from platform settings                      |

---

## 20. Docker · infra (`DOC-*`)

| ID          | P   | Case                                                              |
| ----------- | --- | ----------------------------------------------------------------- |
| DOC-FIN-001 | P0  | `porterchain-postgres` up; API finance endpoints healthy          |
| DOC-FIN-002 | P0  | `porterchain-redis` queue for billing worker                      |
| DOC-FIN-003 | P0  | `porterchain-mailpit` catches invoice/remind                      |
| DOC-FIN-004 | P1  | Redis restart: queued billing jobs recover                        |
| DOC-FIN-005 | P1  | Postgres restart: no partial invoice without ledger               |
| DOC-FIN-006 | P1  | Valhalla/OSRM pins exact tags; finance pricing still resolves     |
| DOC-FIN-007 | P1  | VROOM pin present; used only via Fleetbase                        |
| DOC-FIN-008 | P2  | Mailpit UI shows HTML pay link clickable                          |
| DOC-FIN-009 | P0  | **Anti-case:** no `:latest` images in compose for money-path deps |

---

## 21. Architecture / CI (`ARCH-*`)

| ID           | P   | Case                                                                              |
| ------------ | --- | --------------------------------------------------------------------------------- |
| ARCH-FIN-001 | P0  | `pnpm validate:architecture` / model ownership — finance writes in owning engines |
| ARCH-FIN-002 | P0  | Thin router: finance router has no inline `db.query`                              |
| ARCH-FIN-003 | P0  | Stripe import allowlist                                                           |
| ARCH-FIN-004 | P1  | Privacy/export does not leak other merchants' invoices                            |
| ARCH-FIN-005 | P1  | OpenAPI census includes all `/finance/*` and merchant billing/reports             |
| ARCH-FIN-006 | P1  | `scripts/verify_notifications_billing_depth.py` green                             |
| ARCH-FIN-007 | P2  | Folder law: no SocketCluster in admin finance UI                                  |

---

## 22. Diagnostics / E2E catalog (`DIAG-*`)

Aligned with `e2e_validation_catalog.py`:

| ID           | P   | Case                                                                                                                     |
| ------------ | --- | ------------------------------------------------------------------------------------------------------------------------ |
| DIAG-FIN-001 | P0  | Forward logistics steps include Invoice, Receipt, Reports Updated                                                        |
| DIAG-FIN-002 | P0  | Merchant scenario: Billing Run → Invoice → Statement → Reports                                                           |
| DIAG-FIN-003 | P1  | Consistency surfaces: `billing`, `finance`, `reports`                                                                    |
| DIAG-FIN-004 | P1  | Failure scenarios: stripe_webhook_failure, firebase_failure, notification_failure, fleetbase_offline — invoice integrity |
| DIAG-FIN-005 | P1  | E2E report files include billing/finance/notification sections                                                           |
| DIAG-FIN-006 | P2  | Admin DiagnosticsTestCenter can download related reports                                                                 |

---

## 23. End-to-end handshakes (`HS-*`)

| ID     | P   | Chain                                                                                                                      | Assert                                |
| ------ | --- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| HS-001 | P0  | Website quote → Stripe → Order → Fleetbase dispatch → POD → Invoice → Mailpit → Admin Finance + Merchant Billing + Reports | One invoice; one AR; cents equal      |
| HS-002 | P0  | Merchant CSV/bulk → optimize (Fleetbase VROOM) → deliver → billing run → statement                                         | Reports order-volume + invoices align |
| HS-003 | P0  | Shopify carrier → book → channel on invoice → Pay → webhook                                                                | Quote≡Book≡invoice                    |
| HS-004 | P1  | COD Connect enable → COD order → collections/COD queue → settle                                                            | Checkout prepaid unaffected           |
| HS-005 | P1  | Claim/damage → credit note → reports claims + AR drop                                                                      |                                       |
| HS-006 | P1  | Staff remind → Mailpit → customer pays → ledger + both portals                                                             |                                       |
| HS-007 | P1  | Clerk re-auth mid-pay                                                                                                      | No double charge / double invoice     |
| HS-008 | P2  | Google Places only on address entry during book; Valhalla prices; invoice uses priced amount                               |                                       |

---

## 24. Suggested execution order (dev layer)

1. **P0 authz + IDOR + amount lock** — API-AF/MB, AUTH-FIN, API-MB-001
2. **P0 POD→invoice→ledger** — ENG-001…004, WRK-_, FB-FIN-_
3. **P0 Admin + Merchant UI smoke** — A-FIN-001…007, M-BIL-001…005, M-RPT-001…004
4. **P0 Stripe + Mailpit** — PAY-FIN-*, NOTIF-FIN-001…002, DOC-FIN-003
5. **P1 AR / collections / credit notes / COD** — A-FIN-009…017, ENG-007…008
6. **P1 Shopify channel + reports exports** — SHOP-FIN-*, M-RPT-008…009
7. **P1 Maps/VROOM anti-cases + Docker chaos** — MAP-FIN-*, DOC-FIN-004…007
8. **P2 UX polish + diagnostics** — UX-_, DIAG-_, A-MGT-*
9. **P3 held** — M-RPT-010 scheduled email; aging dedicated report (see intentional skips)

---

## 25. Related

- [ARCHITECTURE.md](../ARCHITECTURE.md) · [INTEGRATIONS.md](../INTEGRATIONS.md) · [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md)
- [DEVELOPMENT_TEST_CASES_CATALOG.md](DEVELOPMENT_TEST_CASES_CATALOG.md) · [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md)
- [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md) · [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md)
- [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md)
- Pytest seeds listed in § sensor trail / Existing coverage seed
