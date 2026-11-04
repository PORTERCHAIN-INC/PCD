# Foreign-key decisions (dm2fkorphan0002)

39 FKs were added. Each is created `NOT VALID`, orphans are handled, then `VALIDATE CONSTRAINT`.

## ON DELETE rules

| Rule       | Columns                                                                                                                                                                                  | Why                                              |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `RESTRICT` | billing ledger columns, `interac_transfers.merchant_id`                                                                                                                                  | money records must never disappear with a parent |
| `CASCADE`  | `pricing_fsa_rates`, `pricing_tariffs`, `promotions`, `user_invitations` `.merchant_id`; `driver_stop_meta`, `reorder_nudges`, `finance_reminder_drafts`, `abandoned_checkouts.quote_id` | rows are meaningless without the parent          |
| `SET NULL` | everything else (CRM links, customer/quote/order back-references, ...)                                                                                                                   | history is kept, link is cleared                 |

CRM `lead_id` columns point at `crm_leads`.

## Orphan handling

- Nullable column → value set to NULL, recorded in `fk_orphan_quarantine` with `action='nulled'`.
- NOT NULL column → whole row moved out, kept as `row_data` JSON with `action='moved'`.
- Downgrade puts every value/row back exactly.

Review after running: `SELECT table_name, column_name, action, count(*) FROM fk_orphan_quarantine GROUP BY 1,2,3;`

## Deliberately NOT linked

| Column                                                 | Reason                                                                     |
| ------------------------------------------------------ | -------------------------------------------------------------------------- |
| `quotes/customers/crm_leads.visitor_session_id`        | anonymous cookie key, written before (or without) a `visitor_sessions` row |
| `notification_*.user_id`                               | polymorphic (customer / merchant user / driver / admin)                    |
| `dispatch_routes.vehicle_id`, `driver_shifts.route_id` | synthetic ids from the router, no parent table                             |
| `stripe_payouts.stripe_payout_id`                      | Stripe's external id                                                       |

## Tables without FKs (reviewed)

The remaining tables with no FK are standalone by design: lookup/config tables
(pricing zones, settings, feature flags), append-only logs and event stores
(`domain_events`, webhook inboxes, `ai_usage_logs`), and archives
(`legacy_external_refs`, `fk_orphan_quarantine`). None hold an id that has a
reliable parent row, so no further FK was added.

## Low-use tables (reviewed, kept)

`legacy_external_refs` (Fleetbase + migration archive, now modelled),
`crm_conversations` / `crm_messages`, `crm_lead_identities`, `crm_referral_credits`,
`customer_notes`, `order_ratings`, `reorder_nudges`, `dispatch_stop_times`,
`marketing_subscribers`: each is still read or written by live code, so none
were dropped. `blog_focus_oct2026_backup` was dropped (rows archived to
`legacy_external_refs` by dm1driftfix0001).

## Production notes

- `VALIDATE CONSTRAINT` takes SHARE UPDATE EXCLUSIVE (reads/writes continue) but scans each table.
- New indexes are not `CONCURRENTLY` (inside the Alembic transaction) — run in a quiet window.
