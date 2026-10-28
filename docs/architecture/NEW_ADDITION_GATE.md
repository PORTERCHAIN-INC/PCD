# New-addition gate

Anything new (table, column, endpoint, state machine, UI, flag, service) must pass **all six**
checks below **before** it is built. Each answer is cross-checked against the existing docs and
code and must cite them (file paths, tables, tests). One failed check = not added, or fixed
first.

| #   | Check                  | Question                                                                                                                                                                                              |
| --- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Clashes**            | Does it conflict with an existing rule, model, state, name, route or business rule (no COD, Interac-only merchants, Phase-1 refusals, pharmacy signature, no white glove, recipient emails redacted)? |
| 2   | **Duplication**        | Does something in the code or docs already do this (fully or partly)? If so, reuse or extend it instead.                                                                                              |
| 3   | **Measurable benefit** | Which number gets better, and how is it read (query, metric, test)?                                                                                                                                   |
| 4   | **Practicality**       | Is it the smallest change that works, and safe on real data and real traffic (locks, migration time, existing clients)?                                                                               |
| 5   | **Control**            | Who can turn it on/off or change it in production without a deploy (admin setting, per-merchant flag, RBAC module) — or why no switch is needed?                                                      |
| 6   | **Rollback**           | The exact revert: migration downgrade id and/or commit to revert, and what happens to data written meanwhile.                                                                                         |

---

## Evaluation — schema / custody change (Oct 2026)

### 1. `fk_orphan_quarantine` table — **PASS**

- **Clashes:** none. New name; only written by `dm2fkorphan0002` / `dm3custody0003`
  (`apps/api/alembic/versions/`), model `FkOrphanQuarantine` in
  `apps/api/src/porterchain_api/schema_extras.py`. No API, never logged.
- **Duplication:** checked `legacy_external_refs` (same file): it is a key/value archive
  (`entity, field, value`) and cannot hold a whole moved row or the action taken. Kept
  separate on purpose; dm4 archives COD values to `legacy_external_refs`, which fits its shape.
- **Measurable benefit:** 0 rows silently deleted while adding 39 FKs. Read with
  `SELECT table_name, action, count(*) FROM fk_orphan_quarantine GROUP BY 1,2;`
  (rehearsal counts in `docs/runbooks/LIVE_MIGRATION_REHEARSAL.md`).
- **Practicality:** one table, one index; written once at migration time.
- **Control:** ops/DBA only (SQL). No runtime switch needed: no code path reads it.
- **Rollback:** `alembic downgrade dm1driftfix0001` restores nulled values and moved rows,
  then drops the table (`tests/test_fk_orphan_migration.py`).

### 2. Package state machine (`PackageState`, `PACKAGE_TRANSITIONS`, `set_package_status`) — **PASS**

- **Clashes:** `PackageState` in `domain/states.py` is the only package status enum; DB CHECK
  `ck_packages_status_known` lists the same values. Pharmacy `signature_required` untouched.
- **Duplication:** reuses the order pattern (`ORDER_TRANSITIONS` + `transition_order_state`
  in `booking_engine/order_transitions.py`) and the existing `order_events` table.
- **Measurable benefit:** illegal package moves (e.g. delivered → manifested) went from
  silent to 0 persisted. Read: `SELECT count(*) FROM order_events WHERE event_type='package.transition_rejected'`.
- **Practicality:** one enum, one dict, one writer (`merchant_engine/package_state.py`); CHECK
  added `NOT VALID`, validated only when no unknown statuses exist.
- **Control:** no flag — it is a data-integrity rule like the order state machine, which also
  has none. Staff can still move a package via the admin override path that uses the same writer.
  _If the live rehearsal shows legitimate flows being refused, the fix is a transition-table
  change, not a switch._
- **Rollback:** code — revert `e346b965`; schema — `alembic downgrade dm2fkorphan0002` drops
  the CHECK and the external-id table.

### 3. Custody refusal audit (`order.transition_rejected`, `package.transition_rejected`) — **PASS**

- **Clashes:** event names follow the existing `order.*` style; payload is ids + states only
  (no recipient email). Not in the merchant webhook catalog (`gateway_engine/merchant_api.py`),
  so not sent to merchants.
- **Duplication:** writes to existing `order_events`; helper `platform/transition_audit.py`.
- **Measurable benefit:** every refusal is countable per driver/order (query above); before,
  refusals vanished with the request rollback.
- **Practicality:** own short transaction with `lock_timeout = 2s`; `lock_order` uses
  `FOR NO KEY UPDATE` so the audit FK check cannot wait on the caller's lock.
- **Control:** none needed — audit only, no behaviour change; readable by staff in Order 360.
- **Rollback:** revert `e346b965` (code only, no migration). Existing audit rows stay harmless.

### 4. Partner barcode cross-reference (`package_external_identifiers`, `/v1/merchant/orders/{id}/external-ids`, Partner Barcodes card) — **PASS after fix**

- **Clashes:** not a tracking number and never shown to recipients. `packages.barcode` /
  `tracking_suffix` stay the PC1 identity; scan lookup tries PC1 first
  (`merchant_engine/scan_gate_service.py::_package_for_scan`), external ids only as fallback,
  always scoped to the scanned order.
- **Duplication:** checked `packages.barcode` (one per box, ours), `orders.tracking_number`,
  `legacy_external_refs`: none holds many-per-box, per-source partner codes.
- **Measurable benefit:** drivers stop relabelling pre-labelled boxes. Read: share of pickup
  scans resolved via external id — `SELECT count(*) FROM package_external_identifiers` plus
  scan events with `resolved_via` (follow-up), and fewer `invalid_label_qr` errors per order.
- **Practicality:** one table + 3 endpoints behind existing RBAC modules (`orders` read,
  `orders_write` add/delete — `authz/schema.zed`), one card in `Order360View`.
- **Control — was FAIL, now fixed:** originally only RBAC; ops had no way to switch it off for
  a merchant without a deploy. Added per-merchant flag `profile.custody.partner_barcodes_enabled`
  (default on), staff-editable via `PATCH /v1/admin/merchants/{id}` `{"partner_barcodes_enabled": false}`
  (audited as `merchant.terms_updated`). Off ⇒ register returns 403 and scans accept PC1 only.
  Test: `test_admin_switch_turns_partner_barcodes_off`.
- **Rollback:** flag off (instant); full — `alembic downgrade dm2fkorphan0002` drops the table,
  revert `e346b965` + `2940f53f` (UI card). PC1 scanning is unaffected either way.

### 5. A new PorterChain tracking number — **FAIL (not built)**

- **Duplication:** fails — every package already has a signed PC1 label
  (`reporting/qr_codec.py`), `tracking_suffix` and `barcode`; orders have `tracking_number`.
- **Clashes:** a second customer-facing id would conflict with the tracking page and
  notification templates that use `tracking_number`.
- **Measurable benefit:** none identified beyond what (4) gives.
- Proposal: keep rejected; partner codes are cross-referenced by (4) instead.

---

## Evaluation — invoice waive / void / credit (Oct 2026)

### 6. Invoice credit notes (`credit_notes` columns, `invoices.credited_cents`, `/v1/admin/finance/invoices/{id}/credit-notes`, Credits & adjustments panel) — **PASS after fix**

- **Clashes:** keeps the no-COD and Interac-only-merchant rules: money paid above the new
  total goes to the merchant credit balance (`add_merchant_credit`) for Interac, or a Stripe
  refund for retail card orders (`billing_engine/invoice_adjustments.py::_issue`). New statuses
  `partially_credited` / `credited`; `void` is kept and now means "fully credited by a void credit
  note" (`merchant_service.invoice_status`). The email holds only the customer-facing reason, and
  the recipient is masked in logs (`platform/credit_note_email.py::mask_email`). Rules:
  `docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md`.
- **Duplication — was FAIL, now fixed:** a `credit_notes` table and `POST /finance/credit-notes`
  (`finance_service.record_credit_note`) already existed, but the endpoint was broken (ledger
  only, no number, no tax split, invoice balance unchanged). Extended that same table rather than
  adding a new one, removed the broken endpoint, and reused `InvoiceNumberSequence` (scope
  `CN:YYYY`), `add_merchant_credit`, `create_refund`, `persist_invoice_status`, the notification
  templates and the PDF stack (`reporting/order_documents.py` style).
- **Measurable benefit:** every waiver now has a numbered credit note with the GST/HST reversed,
  and AR/reminders/Interac matching use the net balance. Read:
  `SELECT reason_code, count(*), sum(amount_cents), sum(tax_cents) FROM credit_notes WHERE status='issued' GROUP BY 1;`
  and `SELECT count(*) FROM invoices WHERE credited_cents > 0 AND status IN ('open','overdue') AND amount_cents - credited_cents <= 0;` (must be 0).
  Tests: `apps/api/tests/test_invoice_credit_notes.py` (24).
- **Practicality:** additive migration `cn5creditnotes0005` (20 nullable columns + one unique
  index on `credit_notes`, one `NOT NULL DEFAULT 0` column on `invoices` — metadata-only on
  PG ≥ 11). Number row locked per year; numbers allocated only on issue, so no gaps.
- **Control:** RBAC module `finance` plus staff step-up on every write; audit entries
  `finance.credit_note.*`. Second-admin approval above `finance_settings.credit_note_approval_threshold_cents`
  (default 50000 = $500), editable without a deploy; the same admin cannot approve their own request.
- **Rollback:** `alembic downgrade dm4nocod0004` drops the new columns and index (issued credit
  note numbers/tax splits are lost; ledger rows `invoice_credit_note` and merchant credits stay
  and must be reviewed by hand) and revert the commit. Invoices with `credited_cents > 0`
  would show their gross balance again after downgrade, so do not downgrade once credits are
  issued on live — fix forward instead.

### 7. GST/HST registration (`tax_registrations`, `platform/tax_registration.py`, `GET/POST /v1/admin/finance/tax-registration`, Admin > Finance > GST/HST) — **PASS after fix**

- **Clashes:** tax was charged everywhere by default (13% `pricing_tax.hst_percent`,
  `default_tax_percent`) even with no registration number, which a non-registrant may not do
  (ETA s. 148 / s. 221; `docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md` §10). Now every tax
  computation (`billing_engine/tax.split_amount`, `pricing_engine/repository._load_tax_config`,
  `platform_settings.default_tax_percent`) and every tax line (invoice/credit-note PDFs, credit-note
  email, FSA rate card, tax report, portal and mobile copy) asks the one service. Unset ⇒ zero tax,
  no label, no number, no "(not set)".
- **Duplication — was FAIL, now fixed:** the number lived in `finance_settings.gst_hst_number`
  with no date or history; the 13.0 rate was hard-coded in 4 places. Replaced by the append-only
  table; the rate comes from the province table (`porterchain_pricing.tax.provinces`). The driver's
  own tax estimate is a separate setting (`driver_tax_estimate_percent`) and no longer tied to ours.
- **Measurable benefit:** `SELECT count(*) FROM invoices WHERE tax_cents > 0 AND issued_at::date < (SELECT min(effective_from) FROM tax_registrations WHERE gst_hst_number IS NOT NULL);`
  must stay 0 for invoices issued after this deploy. Tests: `apps/api/tests/test_tax_registration.py`.
- **Practicality:** additive migration `tr6taxreg0006` (one small table + index); copies a valid
  existing `finance_settings.gst_hst_number` with effective date 1970-01-01 so a live system that
  already has a number keeps charging tax.
- **Control:** RBAC `finance` + staff step-up, audit `finance.tax_registration.changed`, price version
  bumped so quotes reprice. Dates cannot go before the latest change; history is never edited.
- **Rollback:** `alembic downgrade cn5creditnotes0005` drops the table (history lost; re-enter the
  number in finance settings after reverting the code).
