# New-addition gate — schema / custody clean-up (Oct 2026)

Every new table, module, endpoint or state machine in this change was put
through the gate below. The exact gate wording was not in the repo, so these
are the questions used; adjust the headings if your checklist differs.

1. **Need** — what real problem does it solve today?
2. **Reuse** — does something existing already do it?
3. **Smallest form** — is this the least new surface that works?
4. **Phase 1 rules** — consistent with no COD, Interac-only merchants, no
   hot/cold food, no dangerous goods / UN3373 / cold chain / controlled
   substances, no white glove, signature + no unattended drop for pharmacy,
   recipient emails redacted from logs?
5. **Rollback** — can it be undone safely on real data?
6. **Proof** — which tests cover it?

## Passed

### `fk_orphan_quarantine` table (dm2fkorphan0002, dm3custody0003)

1. Adding 39 foreign keys to real data fails on any orphan row; deleting them silently loses data.
2. Nothing existing records migration casualties (`legacy_external_refs` is a key/value archive with no row shape).
3. One table: table, column, row pk, bad value, action (`nulled`/`moved`/`reported`), full row JSON.
4. No impact. Row JSON is internal ops data and never logged.
5. Downgrade restores every nulled value and re-inserts every moved row, then drops the table.
6. `tests/test_fk_orphan_migration.py` (null + move + restore).

### Package state machine (`PackageState`, `PACKAGE_TRANSITIONS`, `set_package_status`)

1. `packages.status` was free text written from three places; a delivered box could go back to manifested.
2. Reuses the existing order pattern (`ORDER_TRANSITIONS` + single writer `transition_order_state`) and the existing `order_events` table for audit — no new audit table.
3. One enum, one dict, one writer function, one DB CHECK (`ck_packages_status_known`).
4. Pharmacy signature rule untouched (`signature_required` unchanged).
5. CHECK is added NOT VALID and only validated when no unknown statuses exist (otherwise they are reported to quarantine); downgrade drops it.
6. `tests/merchant_p0/test_custody_state_and_external_ids.py`.

### Rejected-transition audit (`order.transition_rejected`, `package.transition_rejected`)

1. Illegal transitions raised and vanished with the request rollback — no trace for disputes.
2. Writes to the existing `order_events`; no new table.
3. One helper (`platform/transition_audit.py`), own short transaction, `lock_timeout 2s`.
   `lock_order` moved to `FOR NO KEY UPDATE` so the audit row's FK check cannot block on the caller's lock.
4. Payload holds ids and states only — no recipient email.
5. Code-only; revert the commit.
6. Same test file (order + package rejection rows survive rollback).

### `package_external_identifiers` + `/v1/merchant/orders/{id}/external-ids`

1. Shopify/marketplace boxes arrive already labelled; drivers had to relabel or type ids.
2. `packages.barcode` holds our own PC1 barcode (one per box); partner codes are many-per-box and per-source.
3. One table (source ∈ shopify / merchant / marketplace / partner_carrier, normalized value, unique per source), list/add/delete endpoints behind the existing `orders` / `orders_write` modules, scan-gate fallback.
4. Not a tracking number, not shown to recipients.
5. Downgrade drops the table; PC1 scanning is unaffected.
6. Same test file (normalize, duplicates, resolve, endpoints, RBAC).

## Failed (not added)

### A new PorterChain tracking number

Fails **Reuse**: every package already has a signed PC1 label (`reporting/qr_codec.py`),
`tracking_suffix` and `barcode`, and orders have `tracking_number`. Partner codes
are cross-referenced instead.
