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
