# 04 — ER diagram and schema (AS-BUILT)

**Evidence:** read-only introspection of the local stack Postgres (`pcd-local-pg`, 127.0.0.1:55632, db `porterchain`) via `information_schema` inside a `default_transaction_read_only` session, alembic head `tr6taxreg0006`. ORM cross-check: every DB table has a matching `__tablename__` in `apps/api/src` (129 model tables; only `alembic_version` is DB-only).

Totals: **130 tables**, **152 FK constraints** (column-level), **1708 columns**. Every table has a PK. Every `merchant_id` column carries an FK to `merchants`. 32 tables have no FK in or out (isolated; listed in section 3).

Diagram shows PK and FK columns only (all other columns are in the table listing). Relationship label = the FK column on the child table.

## 1. Full ER diagram

```mermaid
erDiagram
  abandoned_checkouts {
    character id PK
    character quote_id FK
    character customer_id FK
  }
  access_audit_logs {
    character id PK
  }
  addresses {
    character id PK
  }
  admin_audit_logs {
    character id PK
  }
  admin_users {
    character id PK
    character porterchain_user_id FK
  }
  ai_usage_logs {
    character id PK
  }
  alembic_version {
    character version_num PK
  }
  billing_ledger_entries {
    character id PK
    character payment_id FK
    character order_id FK
    character merchant_id FK
    character invoice_id FK
  }
  blog_authors {
    character id PK
  }
  blog_posts {
    character id PK
  }
  booking_attachment_events {
    character id PK
    character order_id FK
  }
  booking_attachments {
    character id PK
    character order_id FK
    character merchant_id FK
    character customer_id FK
  }
  booking_draft_audits {
    character id PK
    character booking_draft_id FK
  }
  booking_drafts {
    character id PK
    character customer_id FK
    character quote_id FK
    character booking_id FK
    character order_id FK
  }
  bookings {
    character id PK
    character quote_id FK
    character customer_id FK
    character order_id FK
  }
  bulk_import_jobs {
    character id PK
    character merchant_id FK
  }
  claims {
    character id PK
    character order_id FK
    character merchant_id FK
  }
  clerk_webhook_events {
    character id PK
  }
  credit_notes {
    character id PK
    character merchant_id FK
    character invoice_id FK
  }
  crm_activities {
    character id PK
  }
  crm_companies {
    character id PK
    character merchant_id FK
  }
  crm_contacts {
    character id PK
    character company_id FK
  }
  crm_contracts {
    character id PK
    character company_id FK
  }
  crm_conversation_messages {
    character id PK
    character conversation_id FK
  }
  crm_conversations {
    character id PK
    character lead_id FK
  }
  crm_deals {
    character id PK
    character company_id FK
  }
  crm_documents {
    character id PK
  }
  crm_invoices {
    character id PK
    character company_id FK
    character operational_invoice_id FK
  }
  crm_lead_identities {
    character id PK
    character lead_id FK
  }
  crm_lead_ingest_events {
    character id PK
    character lead_id FK
  }
  crm_leads {
    character id PK
    character company_id FK
    character quote_id FK
    character booking_draft_id FK
    character order_id FK
  }
  crm_quotations {
    character id PK
    character company_id FK
  }
  crm_referral_credits {
    character id PK
    character lead_id FK
    character company_id FK
  }
  crm_sales_tasks {
    character id PK
    character company_id FK
  }
  crm_suppressions {
    character id PK
    character lead_id FK
  }
  customer_addresses {
    character id PK
    character customer_id FK
  }
  customer_consents {
    character id PK
    character customer_id FK
  }
  customer_credits {
    character id PK
    character customer_id FK
    character order_id FK
  }
  customer_notes {
    character id PK
    character customer_id FK
  }
  customers {
    character id PK
    character porterchain_user_id FK
  }
  deleted_batches {
    character id PK
  }
  dispatch_fix_actions {
    character id PK
    character order_id FK
  }
  dispatch_job_offers {
    character id PK
    character order_id FK
    character driver_id FK
  }
  dispatch_plans {
    character id PK
  }
  dispatch_routes {
    character id PK
    character plan_id FK
    character driver_id FK
  }
  dispatch_stop_events {
    character id PK
    character route_id FK
    character order_id FK
    character driver_id FK
  }
  dispatch_stop_times {
    character id PK
  }
  domain_events {
    character id PK
  }
  driver_bonuses {
    character id PK
    character driver_id FK
  }
  driver_documents {
    character id PK
    character driver_id FK
  }
  driver_incidents {
    character id PK
    character driver_id FK
    character order_id FK
  }
  driver_location_pings {
    character id PK
    character driver_id FK
  }
  driver_offline_actions {
    character id PK
    character driver_id FK
  }
  driver_payout_runs {
    character id PK
  }
  driver_payouts {
    character id PK
    character driver_id FK
  }
  driver_shift_activities {
    character id PK
    character shift_id FK
    character driver_id FK
  }
  driver_shifts {
    character id PK
    character driver_id FK
  }
  driver_stop_meta {
    character id PK
    character order_id FK
    character driver_id FK
  }
  driver_wallet_transactions {
    character id PK
    character driver_id FK
  }
  drivers {
    character id PK
    character porterchain_user_id FK
    character crm_lead_id FK
  }
  finance_reminder_drafts {
    character id PK
    character merchant_id FK
  }
  fk_orphan_quarantine {
    bigint id PK
  }
  forensic_audit_chain {
    bigint seq PK
  }
  forensic_checkpoints {
    bigint id PK
  }
  identity_links {
    character id PK
    character platform_user_id FK
  }
  identity_migration_records {
    character id PK
    character run_id FK
  }
  identity_migration_runs {
    character id PK
  }
  interac_transfers {
    character id PK
    character invoice_id FK
    character merchant_id FK
    character payment_id FK
  }
  invoice_lines {
    character id PK
    character invoice_id FK
    character order_id FK
    character package_id FK
  }
  invoice_number_sequences {
    character scope PK
  }
  invoices {
    character id PK
    character order_id FK
    character customer_id FK
    character merchant_id FK
  }
  leads {
    character id PK
    character quote_id FK
    character customer_id FK
    character crm_lead_id FK
  }
  legacy_external_refs {
    bigint id PK
  }
  logistics_partners {
    character id PK
  }
  marketing_subscribers {
    character id PK
    character lead_id FK
  }
  merchant_alerts {
    character id PK
    character merchant_id FK
  }
  merchant_api_keys {
    character id PK
    character merchant_id FK
  }
  merchant_api_usage_logs {
    character id PK
    character merchant_id FK
    character api_key_id FK
  }
  merchant_audit_logs {
    character id PK
    character merchant_id FK
  }
  merchant_booking_templates {
    character id PK
    character merchant_id FK
  }
  merchant_contracts {
    character id PK
    character merchant_id FK
    character crm_contract_id FK
  }
  merchant_documents {
    character id PK
    character merchant_id FK
  }
  merchant_merges {
    character id PK
  }
  merchant_recipients {
    character id PK
    character merchant_id FK
  }
  merchant_users {
    character id PK
    character merchant_id FK
    character porterchain_user_id FK
  }
  merchant_webhook_deliveries {
    character id PK
    character merchant_id FK
    character webhook_id FK
  }
  merchant_webhooks {
    character id PK
    character merchant_id FK
  }
  merchants {
    character id PK
    character parent_merchant_id FK
  }
  notification_admin_settings {
    character key PK
  }
  notification_delivery_logs {
    character id PK
  }
  notification_devices {
    character id PK
  }
  notification_email_suppressions {
    character email PK
  }
  notification_preferences {
    character id PK
  }
  notification_records {
    character id PK
  }
  notification_template_copy {
    character id PK
  }
  notification_user_settings {
    character id PK
  }
  order_events {
    character id PK
    character order_id FK
  }
  order_exceptions {
    character id PK
    character order_id FK
  }
  order_legs {
    character id PK
    character order_id FK
    character partner_id FK
  }
  order_ratings {
    character id PK
    character order_id FK
  }
  orders {
    character id PK
    character quote_id FK
    character customer_id FK
    character merchant_id FK
    character assigned_driver_id FK
  }
  package_external_identifiers {
    character id PK
    character package_id FK
    character order_id FK
  }
  packages {
    character id PK
    character order_id FK
  }
  payments {
    character id PK
    character quote_id FK
    character order_id FK
    character customer_id FK
    character invoice_id FK
  }
  porterchain_users {
    character id PK
  }
  pricing_fsa_rates {
    character id PK
    character merchant_id FK
  }
  pricing_tariffs {
    character id PK
    character merchant_id FK
  }
  pricing_zones {
    character id PK
  }
  privacy_deletion_jobs {
    character id PK
    character customer_id FK
  }
  promotions {
    character id PK
    character merchant_id FK
  }
  quotes {
    character id PK
    character customer_id FK
  }
  reorder_nudges {
    character id PK
    character customer_id FK
    character order_id FK
  }
  route_center_templates {
    character id PK
    character merchant_id FK
  }
  saved_addresses {
    character id PK
    character merchant_id FK
    character address_id FK
  }
  shopify_data_subject_requests {
    character id PK
    character shop_id FK
    character merchant_id FK
  }
  shopify_ingress_dlq {
    character id PK
    character merchant_id FK
    character shop_id FK
  }
  shopify_rate_quotes {
    character id PK
    character shop_id FK
    character merchant_id FK
  }
  shopify_shops {
    character id PK
    character merchant_id FK
    character default_pickup_address_id FK
  }
  staff_webauthn_credentials {
    character id PK
    character admin_user_id FK
  }
  standing_orders {
    character id PK
    character merchant_id FK
    character booking_template_id FK
  }
  stops {
    character id PK
    character order_id FK
    character address_id FK
  }
  stripe_payouts {
    character id PK
  }
  stripe_webhook_events {
    character id PK
  }
  support_tickets {
    character id PK
    character customer_id FK
    character merchant_id FK
    character driver_id FK
    character order_id FK
  }
  system_config {
    character key PK
  }
  tax_registrations {
    character id PK
  }
  user_emails {
    character id PK
    character user_id FK
  }
  user_invitations {
    character id PK
    character merchant_id FK
    character porterchain_user_id FK
  }
  vehicles {
    character id PK
    character driver_id FK
  }
  visitor_sessions {
    character id PK
    character customer_id FK
  }
  customers ||--o{ abandoned_checkouts : "customer_id"
  quotes ||--o{ abandoned_checkouts : "quote_id"
  porterchain_users ||--o{ admin_users : "porterchain_user_id"
  invoices ||--o{ billing_ledger_entries : "invoice_id"
  merchants ||--o{ billing_ledger_entries : "merchant_id"
  orders ||--o{ billing_ledger_entries : "order_id"
  payments ||--o{ billing_ledger_entries : "payment_id"
  orders ||--o{ booking_attachment_events : "order_id"
  orders ||--o{ booking_attachments : "order_id"
  merchants ||--o{ booking_attachments : "merchant_id"
  customers ||--o{ booking_attachments : "customer_id"
  booking_drafts ||--o{ booking_draft_audits : "booking_draft_id"
  customers ||--o{ booking_drafts : "customer_id"
  bookings ||--o{ booking_drafts : "booking_id"
  orders ||--o{ booking_drafts : "order_id"
  quotes ||--o{ booking_drafts : "quote_id"
  quotes ||--o{ bookings : "quote_id"
  customers ||--o{ bookings : "customer_id"
  orders ||--o{ bookings : "order_id"
  merchants ||--o{ bulk_import_jobs : "merchant_id"
  orders ||--o{ claims : "order_id"
  merchants ||--o{ claims : "merchant_id"
  invoices ||--o{ credit_notes : "invoice_id"
  merchants ||--o{ credit_notes : "merchant_id"
  merchants ||--o{ crm_companies : "merchant_id"
  crm_companies ||--o{ crm_contacts : "company_id"
  crm_companies ||--o{ crm_contracts : "company_id"
  crm_conversations ||--o{ crm_conversation_messages : "conversation_id"
  crm_leads ||--o{ crm_conversations : "lead_id"
  crm_companies ||--o{ crm_deals : "company_id"
  invoices ||--o{ crm_invoices : "operational_invoice_id"
  crm_companies ||--o{ crm_invoices : "company_id"
  crm_leads ||--o{ crm_lead_identities : "lead_id"
  crm_leads ||--o{ crm_lead_ingest_events : "lead_id"
  quotes ||--o{ crm_leads : "quote_id"
  crm_companies ||--o{ crm_leads : "company_id"
  booking_drafts ||--o{ crm_leads : "booking_draft_id"
  orders ||--o{ crm_leads : "order_id"
  crm_companies ||--o{ crm_quotations : "company_id"
  crm_leads ||--o{ crm_referral_credits : "lead_id"
  crm_companies ||--o{ crm_referral_credits : "company_id"
  crm_companies ||--o{ crm_sales_tasks : "company_id"
  crm_leads ||--o{ crm_suppressions : "lead_id"
  customers ||--o{ customer_addresses : "customer_id"
  customers ||--o{ customer_consents : "customer_id"
  customers ||--o{ customer_credits : "customer_id"
  orders ||--o{ customer_credits : "order_id"
  customers ||--o{ customer_notes : "customer_id"
  porterchain_users ||--o{ customers : "porterchain_user_id"
  orders ||--o{ dispatch_fix_actions : "order_id"
  drivers ||--o{ dispatch_job_offers : "driver_id"
  orders ||--o{ dispatch_job_offers : "order_id"
  drivers ||--o{ dispatch_routes : "driver_id"
  dispatch_plans ||--o{ dispatch_routes : "plan_id"
  dispatch_routes ||--o{ dispatch_stop_events : "route_id"
  drivers ||--o{ dispatch_stop_events : "driver_id"
  orders ||--o{ dispatch_stop_events : "order_id"
  drivers ||--o{ driver_bonuses : "driver_id"
  drivers ||--o{ driver_documents : "driver_id"
  orders ||--o{ driver_incidents : "order_id"
  drivers ||--o{ driver_incidents : "driver_id"
  drivers ||--o{ driver_location_pings : "driver_id"
  drivers ||--o{ driver_offline_actions : "driver_id"
  drivers ||--o{ driver_payouts : "driver_id"
  drivers ||--o{ driver_shift_activities : "driver_id"
  driver_shifts ||--o{ driver_shift_activities : "shift_id"
  drivers ||--o{ driver_shifts : "driver_id"
  drivers ||--o{ driver_stop_meta : "driver_id"
  orders ||--o{ driver_stop_meta : "order_id"
  drivers ||--o{ driver_wallet_transactions : "driver_id"
  porterchain_users ||--o{ drivers : "porterchain_user_id"
  crm_leads ||--o{ drivers : "crm_lead_id"
  merchants ||--o{ finance_reminder_drafts : "merchant_id"
  porterchain_users ||--o{ identity_links : "platform_user_id"
  identity_migration_runs ||--o{ identity_migration_records : "run_id"
  payments ||--o{ interac_transfers : "payment_id"
  merchants ||--o{ interac_transfers : "merchant_id"
  invoices ||--o{ interac_transfers : "invoice_id"
  packages ||--o{ invoice_lines : "package_id"
  invoices ||--o{ invoice_lines : "invoice_id"
  orders ||--o{ invoice_lines : "order_id"
  customers ||--o{ invoices : "customer_id"
  orders ||--o{ invoices : "order_id"
  merchants ||--o{ invoices : "merchant_id"
  customers ||--o{ leads : "customer_id"
  crm_leads ||--o{ leads : "crm_lead_id"
  quotes ||--o{ leads : "quote_id"
  crm_leads ||--o{ marketing_subscribers : "lead_id"
  merchants ||--o{ merchant_alerts : "merchant_id"
  merchants ||--o{ merchant_api_keys : "merchant_id"
  merchant_api_keys ||--o{ merchant_api_usage_logs : "api_key_id"
  merchants ||--o{ merchant_api_usage_logs : "merchant_id"
  merchants ||--o{ merchant_audit_logs : "merchant_id"
  merchants ||--o{ merchant_booking_templates : "merchant_id"
  merchants ||--o{ merchant_contracts : "merchant_id"
  crm_contracts ||--o{ merchant_contracts : "crm_contract_id"
  merchants ||--o{ merchant_documents : "merchant_id"
  merchants ||--o{ merchant_recipients : "merchant_id"
  merchants ||--o{ merchant_users : "merchant_id"
  porterchain_users ||--o{ merchant_users : "porterchain_user_id"
  merchants ||--o{ merchant_webhook_deliveries : "merchant_id"
  merchant_webhooks ||--o{ merchant_webhook_deliveries : "webhook_id"
  merchants ||--o{ merchant_webhooks : "merchant_id"
  merchants ||--o{ merchants : "parent_merchant_id"
  orders ||--o{ order_events : "order_id"
  orders ||--o{ order_exceptions : "order_id"
  logistics_partners ||--o{ order_legs : "partner_id"
  orders ||--o{ order_legs : "order_id"
  orders ||--o{ order_ratings : "order_id"
  drivers ||--o{ orders : "assigned_driver_id"
  customers ||--o{ orders : "customer_id"
  quotes ||--o{ orders : "quote_id"
  merchants ||--o{ orders : "merchant_id"
  packages ||--o{ package_external_identifiers : "package_id"
  orders ||--o{ package_external_identifiers : "order_id"
  orders ||--o{ packages : "order_id"
  quotes ||--o{ payments : "quote_id"
  invoices ||--o{ payments : "invoice_id"
  customers ||--o{ payments : "customer_id"
  orders ||--o{ payments : "order_id"
  merchants ||--o{ pricing_fsa_rates : "merchant_id"
  merchants ||--o{ pricing_tariffs : "merchant_id"
  customers ||--o{ privacy_deletion_jobs : "customer_id"
  merchants ||--o{ promotions : "merchant_id"
  customers ||--o{ quotes : "customer_id"
  customers ||--o{ reorder_nudges : "customer_id"
  orders ||--o{ reorder_nudges : "order_id"
  merchants ||--o{ route_center_templates : "merchant_id"
  merchants ||--o{ saved_addresses : "merchant_id"
  addresses ||--o{ saved_addresses : "address_id"
  merchants ||--o{ shopify_data_subject_requests : "merchant_id"
  shopify_shops ||--o{ shopify_data_subject_requests : "shop_id"
  shopify_shops ||--o{ shopify_ingress_dlq : "shop_id"
  merchants ||--o{ shopify_ingress_dlq : "merchant_id"
  merchants ||--o{ shopify_rate_quotes : "merchant_id"
  shopify_shops ||--o{ shopify_rate_quotes : "shop_id"
  saved_addresses ||--o{ shopify_shops : "default_pickup_address_id"
  merchants ||--o{ shopify_shops : "merchant_id"
  admin_users ||--o{ staff_webauthn_credentials : "admin_user_id"
  merchants ||--o{ standing_orders : "merchant_id"
  merchant_booking_templates ||--o{ standing_orders : "booking_template_id"
  addresses ||--o{ stops : "address_id"
  orders ||--o{ stops : "order_id"
  customers ||--o{ support_tickets : "customer_id"
  orders ||--o{ support_tickets : "order_id"
  merchants ||--o{ support_tickets : "merchant_id"
  drivers ||--o{ support_tickets : "driver_id"
  porterchain_users ||--o{ user_emails : "user_id"
  merchants ||--o{ user_invitations : "merchant_id"
  porterchain_users ||--o{ user_invitations : "porterchain_user_id"
  drivers ||--o{ vehicles : "driver_id"
  customers ||--o{ visitor_sessions : "customer_id"
```

## 2. Schema listing by domain

### Audit / forensics

| Table                  | Cols | PK  | FKs (col → parent) | Local rows |
| ---------------------- | ---: | --- | ------------------ | ---------: |
| `forensic_audit_chain` |   13 | seq | —                  |          7 |
| `forensic_checkpoints` |    7 | id  | —                  |          0 |

### Billing

| Table                      | Cols | PK    | FKs (col → parent)                                                               | Local rows |
| -------------------------- | ---: | ----- | -------------------------------------------------------------------------------- | ---------: |
| `billing_ledger_entries`   |   12 | id    | invoice_id→invoices, merchant_id→merchants, order_id→orders, payment_id→payments |          0 |
| `credit_notes`             |   27 | id    | invoice_id→invoices, merchant_id→merchants                                       |          0 |
| `finance_reminder_drafts`  |   12 | id    | merchant_id→merchants                                                            |          0 |
| `invoice_lines`            |    9 | id    | invoice_id→invoices, order_id→orders, package_id→packages                        |          0 |
| `invoice_number_sequences` |    3 | scope | —                                                                                |          0 |
| `invoices`                 |   27 | id    | customer_id→customers, merchant_id→merchants, order_id→orders                    |          0 |
| `tax_registrations`        |    7 | id    | —                                                                                |          1 |

### Booking / orders

| Table                          | Cols | PK  | FKs (col → parent)                                                                        | Local rows |
| ------------------------------ | ---: | --- | ----------------------------------------------------------------------------------------- | ---------: |
| `booking_attachment_events`    |    8 | id  | order_id→orders                                                                           |          0 |
| `booking_attachments`          |   27 | id  | customer_id→customers, merchant_id→merchants, order_id→orders                             |          0 |
| `booking_draft_audits`         |    9 | id  | booking_draft_id→booking_drafts                                                           |          0 |
| `booking_drafts`               |   35 | id  | booking_id→bookings, customer_id→customers, order_id→orders, quote_id→quotes              |          0 |
| `bookings`                     |    7 | id  | customer_id→customers, order_id→orders, quote_id→quotes                                   |          0 |
| `order_events`                 |   10 | id  | order_id→orders                                                                           |          0 |
| `order_exceptions`             |   10 | id  | order_id→orders                                                                           |          0 |
| `order_legs`                   |   11 | id  | order_id→orders, partner_id→logistics_partners                                            |          0 |
| `order_ratings`                |    5 | id  | order_id→orders                                                                           |          0 |
| `orders`                       |   31 | id  | assigned_driver_id→drivers, customer_id→customers, merchant_id→merchants, quote_id→quotes |          0 |
| `package_external_identifiers` |    8 | id  | order_id→orders, package_id→packages                                                      |          0 |
| `packages`                     |   23 | id  | order_id→orders                                                                           |          0 |
| `quotes`                       |   28 | id  | customer_id→customers                                                                     |          0 |
| `stops`                        |    9 | id  | address_id→addresses, order_id→orders                                                     |          0 |

### CRM / sales

| Table                       | Cols | PK  | FKs (col → parent)                                                                          | Local rows |
| --------------------------- | ---: | --- | ------------------------------------------------------------------------------------------- | ---------: |
| `crm_activities`            |   10 | id  | —                                                                                           |          0 |
| `crm_companies`             |   35 | id  | merchant_id→merchants                                                                       |          0 |
| `crm_contacts`              |   19 | id  | company_id→crm_companies                                                                    |          0 |
| `crm_contracts`             |   21 | id  | company_id→crm_companies                                                                    |          0 |
| `crm_conversation_messages` |   12 | id  | conversation_id→crm_conversations                                                           |          0 |
| `crm_conversations`         |    7 | id  | lead_id→crm_leads                                                                           |          0 |
| `crm_deals`                 |   21 | id  | company_id→crm_companies                                                                    |          0 |
| `crm_documents`             |   10 | id  | —                                                                                           |          0 |
| `crm_invoices`              |   20 | id  | company_id→crm_companies, operational_invoice_id→invoices                                   |          0 |
| `crm_lead_identities`       |    6 | id  | lead_id→crm_leads                                                                           |          0 |
| `crm_lead_ingest_events`    |   10 | id  | lead_id→crm_leads                                                                           |          0 |
| `crm_leads`                 |   52 | id  | booking_draft_id→booking_drafts, company_id→crm_companies, order_id→orders, quote_id→quotes |          0 |
| `crm_quotations`            |   22 | id  | company_id→crm_companies                                                                    |          0 |
| `crm_referral_credits`      |    9 | id  | company_id→crm_companies, lead_id→crm_leads                                                 |          0 |
| `crm_sales_tasks`           |   20 | id  | company_id→crm_companies                                                                    |          0 |
| `crm_suppressions`          |    6 | id  | lead_id→crm_leads                                                                           |          0 |

### Content

| Table                   | Cols | PK  | FKs (col → parent) | Local rows |
| ----------------------- | ---: | --- | ------------------ | ---------: |
| `blog_authors`          |    6 | id  | —                  |          2 |
| `blog_posts`            |   26 | id  | —                  |          0 |
| `marketing_subscribers` |   15 | id  | lead_id→crm_leads  |          0 |

### Customers

| Table                | Cols | PK  | FKs (col → parent)                     | Local rows |
| -------------------- | ---: | --- | -------------------------------------- | ---------: |
| `customer_addresses` |   19 | id  | customer_id→customers                  |          0 |
| `customer_consents`  |    8 | id  | customer_id→customers                  |          0 |
| `customer_credits`   |    8 | id  | customer_id→customers, order_id→orders |          0 |
| `customer_notes`     |    9 | id  | customer_id→customers                  |          0 |
| `customers`          |   17 | id  | porterchain_user_id→porterchain_users  |          0 |

### Dispatch

| Table                  | Cols | PK  | FKs (col → parent)                                           | Local rows |
| ---------------------- | ---: | --- | ------------------------------------------------------------ | ---------: |
| `dispatch_fix_actions` |    8 | id  | order_id→orders                                              |          0 |
| `dispatch_job_offers`  |   10 | id  | driver_id→drivers, order_id→orders                           |          0 |
| `dispatch_plans`       |   15 | id  | —                                                            |          0 |
| `dispatch_routes`      |   14 | id  | driver_id→drivers, plan_id→dispatch_plans                    |          0 |
| `dispatch_stop_events` |   12 | id  | driver_id→drivers, order_id→orders, route_id→dispatch_routes |          0 |
| `dispatch_stop_times`  |    7 | id  | —                                                            |          0 |

### Drivers

| Table                        | Cols | PK  | FKs (col → parent)                                           | Local rows |
| ---------------------------- | ---: | --- | ------------------------------------------------------------ | ---------: |
| `driver_bonuses`             |    8 | id  | driver_id→drivers                                            |          0 |
| `driver_documents`           |   13 | id  | driver_id→drivers                                            |          0 |
| `driver_incidents`           |    9 | id  | driver_id→drivers, order_id→orders                           |          0 |
| `driver_location_pings`      |    9 | id  | driver_id→drivers                                            |          0 |
| `driver_offline_actions`     |    7 | id  | driver_id→drivers                                            |          0 |
| `driver_payout_runs`         |   13 | id  | —                                                            |          0 |
| `driver_payouts`             |    7 | id  | driver_id→drivers                                            |          0 |
| `driver_shift_activities`    |    6 | id  | driver_id→drivers, shift_id→driver_shifts                    |          0 |
| `driver_shifts`              |   11 | id  | driver_id→drivers                                            |          0 |
| `driver_stop_meta`           |    5 | id  | driver_id→drivers, order_id→orders                           |          0 |
| `driver_wallet_transactions` |    8 | id  | driver_id→drivers                                            |          0 |
| `drivers`                    |   25 | id  | crm_lead_id→crm_leads, porterchain_user_id→porterchain_users |          0 |

### Identity

| Table                        | Cols | PK  | FKs (col → parent)                                           | Local rows |
| ---------------------------- | ---: | --- | ------------------------------------------------------------ | ---------: |
| `clerk_webhook_events`       |    6 | id  | —                                                            |          0 |
| `identity_links`             |   16 | id  | platform_user_id→porterchain_users                           |          1 |
| `identity_migration_records` |   13 | id  | run_id→identity_migration_runs                               |          0 |
| `identity_migration_runs`    |    9 | id  | —                                                            |          0 |
| `porterchain_users`          |   12 | id  | —                                                            |          2 |
| `staff_webauthn_credentials` |    8 | id  | admin_user_id→admin_users                                    |          0 |
| `user_emails`                |    8 | id  | user_id→porterchain_users                                    |          1 |
| `user_invitations`           |   16 | id  | merchant_id→merchants, porterchain_user_id→porterchain_users |          0 |

### Merchants

| Table                         | Cols | PK  | FKs (col → parent)                                           | Local rows |
| ----------------------------- | ---: | --- | ------------------------------------------------------------ | ---------: |
| `merchant_alerts`             |    8 | id  | merchant_id→merchants                                        |          0 |
| `merchant_api_keys`           |   13 | id  | merchant_id→merchants                                        |          0 |
| `merchant_api_usage_logs`     |    9 | id  | api_key_id→merchant_api_keys, merchant_id→merchants          |          0 |
| `merchant_audit_logs`         |    8 | id  | merchant_id→merchants                                        |          0 |
| `merchant_booking_templates`  |   11 | id  | merchant_id→merchants                                        |          0 |
| `merchant_contracts`          |   10 | id  | crm_contract_id→crm_contracts, merchant_id→merchants         |          0 |
| `merchant_documents`          |   13 | id  | merchant_id→merchants                                        |          0 |
| `merchant_merges`             |    8 | id  | —                                                            |          0 |
| `merchant_recipients`         |   12 | id  | merchant_id→merchants                                        |          0 |
| `merchant_users`              |    8 | id  | merchant_id→merchants, porterchain_user_id→porterchain_users |          1 |
| `merchant_webhook_deliveries` |   13 | id  | merchant_id→merchants, webhook_id→merchant_webhooks          |          0 |
| `merchant_webhooks`           |   10 | id  | merchant_id→merchants                                        |          0 |
| `merchants`                   |   34 | id  | parent_merchant_id→merchants                                 |          1 |

### Notifications

| Table                             | Cols | PK    | FKs (col → parent) | Local rows |
| --------------------------------- | ---: | ----- | ------------------ | ---------: |
| `notification_admin_settings`     |    4 | key   | —                  |          0 |
| `notification_delivery_logs`      |    9 | id    | —                  |          0 |
| `notification_devices`            |   16 | id    | —                  |          0 |
| `notification_email_suppressions` |   11 | email | —                  |          0 |
| `notification_preferences`        |   10 | id    | —                  |          0 |
| `notification_records`            |   35 | id    | —                  |          0 |
| `notification_template_copy`      |    9 | id    | —                  |          0 |
| `notification_user_settings`      |   12 | id    | —                  |          0 |

### Other

| Table                    | Cols | PK          | FKs (col → parent)                                                    | Local rows |
| ------------------------ | ---: | ----------- | --------------------------------------------------------------------- | ---------: |
| `abandoned_checkouts`    |    8 | id          | customer_id→customers, quote_id→quotes                                |          0 |
| `access_audit_logs`      |    8 | id          | —                                                                     |          0 |
| `addresses`              |   13 | id          | —                                                                     |          0 |
| `admin_audit_logs`       |    7 | id          | —                                                                     |          0 |
| `admin_users`            |    9 | id          | porterchain_user_id→porterchain_users                                 |          1 |
| `ai_usage_logs`          |   14 | id          | —                                                                     |          0 |
| `alembic_version`        |    1 | version_num | —                                                                     |          1 |
| `bulk_import_jobs`       |   14 | id          | merchant_id→merchants                                                 |          0 |
| `deleted_batches`        |   15 | id          | —                                                                     |          0 |
| `domain_events`          |    9 | id          | —                                                                     |          0 |
| `fk_orphan_quarantine`   |    8 | id          | —                                                                     |          0 |
| `leads`                  |    9 | id          | crm_lead_id→crm_leads, customer_id→customers, quote_id→quotes         |          0 |
| `legacy_external_refs`   |    7 | id          | —                                                                     |          4 |
| `logistics_partners`     |   13 | id          | —                                                                     |          0 |
| `promotions`             |   14 | id          | merchant_id→merchants                                                 |          0 |
| `reorder_nudges`         |    8 | id          | customer_id→customers, order_id→orders                                |          0 |
| `route_center_templates` |   11 | id          | merchant_id→merchants                                                 |          0 |
| `saved_addresses`        |   12 | id          | address_id→addresses, merchant_id→merchants                           |          0 |
| `standing_orders`        |   14 | id          | booking_template_id→merchant_booking_templates, merchant_id→merchants |          0 |
| `system_config`          |    3 | key         | —                                                                     |         12 |
| `vehicles`               |   14 | id          | driver_id→drivers                                                     |          0 |
| `visitor_sessions`       |   17 | id          | customer_id→customers                                                 |          0 |

### Payments

| Table                   | Cols | PK  | FKs (col → parent)                                                           | Local rows |
| ----------------------- | ---: | --- | ---------------------------------------------------------------------------- | ---------: |
| `interac_transfers`     |   22 | id  | invoice_id→invoices, merchant_id→merchants, payment_id→payments              |          0 |
| `payments`              |   18 | id  | customer_id→customers, invoice_id→invoices, order_id→orders, quote_id→quotes |          0 |
| `stripe_payouts`        |   16 | id  | —                                                                            |          0 |
| `stripe_webhook_events` |    5 | id  | —                                                                            |          0 |

### Pricing

| Table               | Cols | PK  | FKs (col → parent)    | Local rows |
| ------------------- | ---: | --- | --------------------- | ---------: |
| `pricing_fsa_rates` |   12 | id  | merchant_id→merchants |          0 |
| `pricing_tariffs`   |   16 | id  | merchant_id→merchants |         20 |
| `pricing_zones`     |   11 | id  | —                     |          1 |

### Privacy

| Table                   | Cols | PK  | FKs (col → parent)    | Local rows |
| ----------------------- | ---: | --- | --------------------- | ---------: |
| `privacy_deletion_jobs` |   13 | id  | customer_id→customers |          0 |

### Shopify

| Table                           | Cols | PK  | FKs (col → parent)                                               | Local rows |
| ------------------------------- | ---: | --- | ---------------------------------------------------------------- | ---------: |
| `shopify_data_subject_requests` |   16 | id  | merchant_id→merchants, shop_id→shopify_shops                     |          0 |
| `shopify_ingress_dlq`           |   17 | id  | merchant_id→merchants, shop_id→shopify_shops                     |          0 |
| `shopify_rate_quotes`           |   12 | id  | merchant_id→merchants, shop_id→shopify_shops                     |          0 |
| `shopify_shops`                 |   25 | id  | default_pickup_address_id→saved_addresses, merchant_id→merchants |          0 |

### Support

| Table             | Cols | PK  | FKs (col → parent)                                                               | Local rows |
| ----------------- | ---: | --- | -------------------------------------------------------------------------------- | ---------: |
| `claims`          |   15 | id  | merchant_id→merchants, order_id→orders                                           |          0 |
| `support_tickets` |   18 | id  | customer_id→customers, driver_id→drivers, merchant_id→merchants, order_id→orders |          0 |

## 3. Isolated tables (no FK in or out)

These are not wrong by definition (logs, webhook inboxes, config), but each is a candidate for an FK or an explicit "log table" label. See audit 11 (A-DB-02).

- `access_audit_logs`
- `admin_audit_logs`
- `ai_usage_logs`
- `alembic_version`
- `blog_authors`
- `blog_posts`
- `clerk_webhook_events`
- `crm_activities`
- `crm_documents`
- `deleted_batches`
- `dispatch_stop_times`
- `domain_events`
- `driver_payout_runs`
- `fk_orphan_quarantine`
- `forensic_audit_chain`
- `forensic_checkpoints`
- `invoice_number_sequences`
- `legacy_external_refs`
- `merchant_merges`
- `notification_admin_settings`
- `notification_delivery_logs`
- `notification_devices`
- `notification_email_suppressions`
- `notification_preferences`
- `notification_records`
- `notification_template_copy`
- `notification_user_settings`
- `pricing_zones`
- `stripe_payouts`
- `stripe_webhook_events`
- `system_config`
- `tax_registrations`

## 4. Full column listing

<details><summary>All columns (table, column, type, nullable)</summary>

| Table                           | Column                           | Type                     | Null |
| ------------------------------- | -------------------------------- | ------------------------ | ---- |
| abandoned_checkouts             | id                               | character varying        | NO   |
| abandoned_checkouts             | quote_id                         | character varying        | NO   |
| abandoned_checkouts             | customer_id                      | character varying        | YES  |
| abandoned_checkouts             | email                            | character varying        | NO   |
| abandoned_checkouts             | phone                            | character varying        | YES  |
| abandoned_checkouts             | stripe_checkout_session_id       | character varying        | YES  |
| abandoned_checkouts             | reason                           | character varying        | NO   |
| abandoned_checkouts             | created_at                       | timestamp with time zone | NO   |
| access_audit_logs               | id                               | character varying        | NO   |
| access_audit_logs               | actor_user_id                    | character varying        | YES  |
| access_audit_logs               | action                           | character varying        | NO   |
| access_audit_logs               | resource_type                    | character varying        | YES  |
| access_audit_logs               | resource_id                      | character varying        | YES  |
| access_audit_logs               | outcome                          | character varying        | NO   |
| access_audit_logs               | detail                           | json                     | NO   |
| access_audit_logs               | created_at                       | timestamp with time zone | NO   |
| addresses                       | id                               | character varying        | NO   |
| addresses                       | formatted                        | character varying        | NO   |
| addresses                       | line1                            | character varying        | YES  |
| addresses                       | city                             | character varying        | YES  |
| addresses                       | region                           | character varying        | YES  |
| addresses                       | postal                           | character varying        | YES  |
| addresses                       | country                          | character varying        | NO   |
| addresses                       | lat                              | double precision         | YES  |
| addresses                       | lng                              | double precision         | YES  |
| addresses                       | place_id                         | character varying        | YES  |
| addresses                       | contact_name                     | character varying        | YES  |
| addresses                       | phone                            | character varying        | YES  |
| addresses                       | created_at                       | timestamp with time zone | NO   |
| admin_audit_logs                | id                               | character varying        | NO   |
| admin_audit_logs                | actor_user_id                    | character varying        | YES  |
| admin_audit_logs                | action                           | character varying        | NO   |
| admin_audit_logs                | resource_type                    | character varying        | NO   |
| admin_audit_logs                | resource_id                      | character varying        | YES  |
| admin_audit_logs                | payload                          | json                     | NO   |
| admin_audit_logs                | created_at                       | timestamp with time zone | NO   |
| admin_users                     | id                               | character varying        | NO   |
| admin_users                     | clerk_user_id                    | character varying        | YES  |
| admin_users                     | email                            | character varying        | NO   |
| admin_users                     | name                             | character varying        | YES  |
| admin_users                     | role                             | character varying        | NO   |
| admin_users                     | is_active                        | boolean                  | NO   |
| admin_users                     | created_at                       | timestamp with time zone | NO   |
| admin_users                     | porterchain_user_id              | character varying        | YES  |
| admin_users                     | phone                            | character varying        | YES  |
| ai_usage_logs                   | id                               | character varying        | NO   |
| ai_usage_logs                   | provider                         | character varying        | NO   |
| ai_usage_logs                   | model                            | character varying        | NO   |
| ai_usage_logs                   | feature                          | character varying        | NO   |
| ai_usage_logs                   | actor_type                       | character varying        | YES  |
| ai_usage_logs                   | actor_id                         | character varying        | YES  |
| ai_usage_logs                   | prompt_tokens                    | integer                  | NO   |
| ai_usage_logs                   | completion_tokens                | integer                  | NO   |
| ai_usage_logs                   | total_tokens                     | integer                  | NO   |
| ai_usage_logs                   | latency_ms                       | integer                  | YES  |
| ai_usage_logs                   | status                           | character varying        | NO   |
| ai_usage_logs                   | error                            | text                     | YES  |
| ai_usage_logs                   | meta                             | json                     | NO   |
| ai_usage_logs                   | created_at                       | timestamp with time zone | NO   |
| alembic_version                 | version_num                      | character varying        | NO   |
| billing_ledger_entries          | id                               | character varying        | NO   |
| billing_ledger_entries          | kind                             | character varying        | NO   |
| billing_ledger_entries          | payment_id                       | character varying        | YES  |
| billing_ledger_entries          | order_id                         | character varying        | YES  |
| billing_ledger_entries          | merchant_id                      | character varying        | YES  |
| billing_ledger_entries          | amount_cents                     | integer                  | YES  |
| billing_ledger_entries          | currency                         | character varying        | NO   |
| billing_ledger_entries          | status                           | character varying        | NO   |
| billing_ledger_entries          | metadata                         | json                     | NO   |
| billing_ledger_entries          | created_at                       | timestamp with time zone | NO   |
| billing_ledger_entries          | invoice_id                       | character varying        | YES  |
| billing_ledger_entries          | idempotency_key                  | character varying        | YES  |
| blog_authors                    | id                               | character varying        | NO   |
| blog_authors                    | name                             | character varying        | NO   |
| blog_authors                    | role                             | character varying        | NO   |
| blog_authors                    | bio                              | text                     | NO   |
| blog_authors                    | created_at                       | timestamp with time zone | NO   |
| blog_authors                    | updated_at                       | timestamp with time zone | NO   |
| blog_posts                      | id                               | character varying        | NO   |
| blog_posts                      | slug                             | character varying        | NO   |
| blog_posts                      | locale                           | character varying        | NO   |
| blog_posts                      | title                            | character varying        | NO   |
| blog_posts                      | description                      | text                     | NO   |
| blog_posts                      | body_md                          | text                     | NO   |
| blog_posts                      | category                         | character varying        | NO   |
| blog_posts                      | author_id                        | character varying        | NO   |
| blog_posts                      | status                           | character varying        | NO   |
| blog_posts                      | featured                         | boolean                  | NO   |
| blog_posts                      | trending                         | boolean                  | NO   |
| blog_posts                      | case_study                       | boolean                  | NO   |
| blog_posts                      | on_time_percent                  | character varying        | YES  |
| blog_posts                      | cost_delta_percent               | character varying        | YES  |
| blog_posts                      | volume_metric                    | character varying        | YES  |
| blog_posts                      | tags                             | json                     | NO   |
| blog_posts                      | published_at                     | date                     | YES  |
| blog_posts                      | created_by                       | character varying        | YES  |
| blog_posts                      | created_at                       | timestamp with time zone | NO   |
| blog_posts                      | updated_at                       | timestamp with time zone | NO   |
| blog_posts                      | cover_image_url                  | character varying        | YES  |
| blog_posts                      | scheduled_publish_at             | timestamp with time zone | YES  |
| blog_posts                      | deleted_at                       | timestamp with time zone | YES  |
| blog_posts                      | deleted_by                       | character varying        | YES  |
| blog_posts                      | delete_reason                    | character varying        | YES  |
| blog_posts                      | delete_batch_id                  | character varying        | YES  |
| booking_attachment_events       | id                               | character varying        | NO   |
| booking_attachment_events       | attachment_id                    | character varying        | NO   |
| booking_attachment_events       | order_id                         | character varying        | YES  |
| booking_attachment_events       | actor_type                       | character varying        | NO   |
| booking_attachment_events       | actor_id                         | character varying        | YES  |
| booking_attachment_events       | action                           | character varying        | NO   |
| booking_attachment_events       | payload                          | json                     | NO   |
| booking_attachment_events       | created_at                       | timestamp with time zone | NO   |
| booking_attachments             | id                               | character varying        | NO   |
| booking_attachments             | order_id                         | character varying        | YES  |
| booking_attachments             | merchant_id                      | character varying        | YES  |
| booking_attachments             | customer_id                      | character varying        | YES  |
| booking_attachments             | stop                             | character varying        | NO   |
| booking_attachments             | kind                             | character varying        | NO   |
| booking_attachments             | filename                         | character varying        | NO   |
| booking_attachments             | content_type                     | character varying        | NO   |
| booking_attachments             | size_bytes                       | integer                  | NO   |
| booking_attachments             | sha256                           | character varying        | NO   |
| booking_attachments             | content                          | bytea                    | YES  |
| booking_attachments             | note                             | character varying        | YES  |
| booking_attachments             | required_at_stop                 | boolean                  | NO   |
| booking_attachments             | location_key                     | character varying        | YES  |
| booking_attachments             | is_location_template             | boolean                  | NO   |
| booking_attachments             | source_template_id               | character varying        | YES  |
| booking_attachments             | uploaded_by                      | character varying        | YES  |
| booking_attachments             | first_viewed_by_driver_at        | timestamp with time zone | YES  |
| booking_attachments             | shown_at                         | timestamp with time zone | YES  |
| booking_attachments             | shown_by_driver_id               | character varying        | YES  |
| booking_attachments             | proof_content                    | bytea                    | YES  |
| booking_attachments             | proof_content_type               | character varying        | YES  |
| booking_attachments             | link_token_hash                  | character varying        | YES  |
| booking_attachments             | link_expires_at                  | timestamp with time zone | YES  |
| booking_attachments             | purged_at                        | timestamp with time zone | YES  |
| booking_attachments             | deleted_at                       | timestamp with time zone | YES  |
| booking_attachments             | created_at                       | timestamp with time zone | NO   |
| booking_draft_audits            | id                               | character varying        | NO   |
| booking_draft_audits            | booking_draft_id                 | character varying        | NO   |
| booking_draft_audits            | from_state                       | character varying        | YES  |
| booking_draft_audits            | to_state                         | character varying        | NO   |
| booking_draft_audits            | event_label                      | character varying        | NO   |
| booking_draft_audits            | actor_type                       | character varying        | NO   |
| booking_draft_audits            | actor_id                         | character varying        | YES  |
| booking_draft_audits            | payload                          | json                     | NO   |
| booking_draft_audits            | occurred_at                      | timestamp with time zone | NO   |
| booking_drafts                  | id                               | character varying        | NO   |
| booking_drafts                  | session_id                       | character varying        | NO   |
| booking_drafts                  | customer_id                      | character varying        | YES  |
| booking_drafts                  | quote_id                         | character varying        | YES  |
| booking_drafts                  | state                            | character varying        | NO   |
| booking_drafts                  | current_step                     | character varying        | NO   |
| booking_drafts                  | pickup                           | json                     | YES  |
| booking_drafts                  | dropoff                          | json                     | YES  |
| booking_drafts                  | additional_stops                 | json                     | YES  |
| booking_drafts                  | vehicle_class                    | character varying        | YES  |
| booking_drafts                  | package_type                     | character varying        | YES  |
| booking_drafts                  | weight_kg                        | double precision         | YES  |
| booking_drafts                  | dimensions                       | character varying        | YES  |
| booking_drafts                  | declared_value_cents             | integer                  | YES  |
| booking_drafts                  | special_instructions             | text                     | YES  |
| booking_drafts                  | pricing_breakdown                | json                     | YES  |
| booking_drafts                  | taxes_cents                      | integer                  | NO   |
| booking_drafts                  | discounts_cents                  | integer                  | NO   |
| booking_drafts                  | promo_code                       | character varying        | YES  |
| booking_drafts                  | amount_cents                     | integer                  | YES  |
| booking_drafts                  | currency                         | character varying        | NO   |
| booking_drafts                  | distance_meters                  | integer                  | YES  |
| booking_drafts                  | estimated_pickup                 | timestamp with time zone | YES  |
| booking_drafts                  | estimated_delivery               | timestamp with time zone | YES  |
| booking_drafts                  | schedule_mode                    | character varying        | NO   |
| booking_drafts                  | stripe_checkout_session_id       | character varying        | YES  |
| booking_drafts                  | booking_id                       | character varying        | YES  |
| booking_drafts                  | order_id                         | character varying        | YES  |
| booking_drafts                  | expires_at                       | timestamp with time zone | NO   |
| booking_drafts                  | created_at                       | timestamp with time zone | NO   |
| booking_drafts                  | updated_at                       | timestamp with time zone | NO   |
| booking_drafts                  | deleted_at                       | timestamp with time zone | YES  |
| booking_drafts                  | deleted_by                       | character varying        | YES  |
| booking_drafts                  | delete_reason                    | character varying        | YES  |
| booking_drafts                  | delete_batch_id                  | character varying        | YES  |
| bookings                        | id                               | character varying        | NO   |
| bookings                        | booking_number                   | character varying        | NO   |
| bookings                        | state                            | character varying        | NO   |
| bookings                        | quote_id                         | character varying        | NO   |
| bookings                        | customer_id                      | character varying        | NO   |
| bookings                        | order_id                         | character varying        | YES  |
| bookings                        | created_at                       | timestamp with time zone | NO   |
| bulk_import_jobs                | id                               | character varying        | NO   |
| bulk_import_jobs                | merchant_id                      | character varying        | NO   |
| bulk_import_jobs                | status                           | character varying        | NO   |
| bulk_import_jobs                | filename                         | character varying        | NO   |
| bulk_import_jobs                | total_rows                       | integer                  | NO   |
| bulk_import_jobs                | valid_rows                       | integer                  | NO   |
| bulk_import_jobs                | error_rows                       | integer                  | NO   |
| bulk_import_jobs                | duplicate_rows                   | integer                  | NO   |
| bulk_import_jobs                | preview                          | json                     | NO   |
| bulk_import_jobs                | errors                           | json                     | NO   |
| bulk_import_jobs                | order_ids                        | json                     | NO   |
| bulk_import_jobs                | created_at                       | timestamp with time zone | NO   |
| bulk_import_jobs                | kind                             | character varying        | NO   |
| bulk_import_jobs                | job_config                       | json                     | YES  |
| claims                          | id                               | character varying        | NO   |
| claims                          | order_id                         | character varying        | YES  |
| claims                          | claim_type                       | character varying        | NO   |
| claims                          | status                           | character varying        | NO   |
| claims                          | description                      | text                     | YES  |
| claims                          | evidence                         | json                     | NO   |
| claims                          | resolution                       | json                     | YES  |
| claims                          | assigned_to                      | character varying        | YES  |
| claims                          | created_at                       | timestamp with time zone | NO   |
| claims                          | resolved_at                      | timestamp with time zone | YES  |
| claims                          | merchant_id                      | character varying        | YES  |
| claims                          | deleted_at                       | timestamp with time zone | YES  |
| claims                          | deleted_by                       | character varying        | YES  |
| claims                          | delete_reason                    | character varying        | YES  |
| claims                          | delete_batch_id                  | character varying        | YES  |
| clerk_webhook_events            | id                               | character varying        | NO   |
| clerk_webhook_events            | clerk_event_id                   | character varying        | NO   |
| clerk_webhook_events            | event_type                       | character varying        | NO   |
| clerk_webhook_events            | status                           | character varying        | NO   |
| clerk_webhook_events            | created_at                       | timestamp with time zone | NO   |
| clerk_webhook_events            | processed_at                     | timestamp with time zone | YES  |
| credit_notes                    | id                               | character varying        | NO   |
| credit_notes                    | merchant_id                      | character varying        | YES  |
| credit_notes                    | invoice_id                       | character varying        | YES  |
| credit_notes                    | amount_cents                     | integer                  | NO   |
| credit_notes                    | reason                           | text                     | YES  |
| credit_notes                    | status                           | character varying        | NO   |
| credit_notes                    | created_at                       | timestamp with time zone | NO   |
| credit_notes                    | credit_note_number               | character varying        | YES  |
| credit_notes                    | kind                             | character varying        | YES  |
| credit_notes                    | reason_code                      | character varying        | YES  |
| credit_notes                    | internal_note                    | text                     | YES  |
| credit_notes                    | customer_reason                  | text                     | YES  |
| credit_notes                    | subtotal_cents                   | integer                  | YES  |
| credit_notes                    | tax_cents                        | integer                  | YES  |
| credit_notes                    | tax_province                     | character varying        | YES  |
| credit_notes                    | currency                         | character varying        | YES  |
| credit_notes                    | lines_json                       | json                     | YES  |
| credit_notes                    | original_invoice_number          | character varying        | YES  |
| credit_notes                    | original_invoice_date            | timestamp with time zone | YES  |
| credit_notes                    | customer_id                      | character varying        | YES  |
| credit_notes                    | recipient_name                   | character varying        | YES  |
| credit_notes                    | issued_by                        | character varying        | YES  |
| credit_notes                    | approved_by                      | character varying        | YES  |
| credit_notes                    | issued_at                        | timestamp with time zone | YES  |
| credit_notes                    | settlement                       | character varying        | YES  |
| credit_notes                    | settlement_cents                 | integer                  | YES  |
| credit_notes                    | settlement_ref                   | character varying        | YES  |
| crm_activities                  | id                               | character varying        | NO   |
| crm_activities                  | entity_type                      | character varying        | NO   |
| crm_activities                  | entity_id                        | character varying        | NO   |
| crm_activities                  | activity_type                    | character varying        | NO   |
| crm_activities                  | subject                          | character varying        | YES  |
| crm_activities                  | body                             | text                     | YES  |
| crm_activities                  | metadata_json                    | json                     | NO   |
| crm_activities                  | actor_id                         | character varying        | YES  |
| crm_activities                  | occurred_at                      | timestamp with time zone | NO   |
| crm_activities                  | created_at                       | timestamp with time zone | NO   |
| crm_companies                   | id                               | character varying        | NO   |
| crm_companies                   | legal_name                       | character varying        | NO   |
| crm_companies                   | operating_name                   | character varying        | YES  |
| crm_companies                   | business_number                  | character varying        | YES  |
| crm_companies                   | hst_number                       | character varying        | YES  |
| crm_companies                   | industry                         | character varying        | YES  |
| crm_companies                   | business_type                    | character varying        | YES  |
| crm_companies                   | website                          | character varying        | YES  |
| crm_companies                   | linkedin_url                     | character varying        | YES  |
| crm_companies                   | logo_url                         | character varying        | YES  |
| crm_companies                   | phone                            | character varying        | YES  |
| crm_companies                   | email                            | character varying        | YES  |
| crm_companies                   | address                          | jsonb                    | NO   |
| crm_companies                   | branches                         | json                     | NO   |
| crm_companies                   | warehouse_locations              | json                     | NO   |
| crm_companies                   | pickup_locations                 | json                     | NO   |
| crm_companies                   | billing_details                  | json                     | NO   |
| crm_companies                   | estimated_deliveries_per_month   | integer                  | YES  |
| crm_companies                   | estimated_monthly_revenue_cents  | integer                  | YES  |
| crm_companies                   | preferred_vehicle                | character varying        | YES  |
| crm_companies                   | service_area                     | character varying        | YES  |
| crm_companies                   | current_logistics_provider       | character varying        | YES  |
| crm_companies                   | merchant_status                  | character varying        | NO   |
| crm_companies                   | merchant_id                      | character varying        | YES  |
| crm_companies                   | owner_id                         | character varying        | YES  |
| crm_companies                   | tags                             | json                     | NO   |
| crm_companies                   | is_pinned                        | boolean                  | NO   |
| crm_companies                   | is_favorite                      | boolean                  | NO   |
| crm_companies                   | custom_fields                    | jsonb                    | NO   |
| crm_companies                   | created_at                       | timestamp with time zone | NO   |
| crm_companies                   | updated_at                       | timestamp with time zone | NO   |
| crm_companies                   | deleted_at                       | timestamp with time zone | YES  |
| crm_companies                   | deleted_by                       | character varying        | YES  |
| crm_companies                   | delete_reason                    | character varying        | YES  |
| crm_companies                   | delete_batch_id                  | character varying        | YES  |
| crm_contacts                    | id                               | character varying        | NO   |
| crm_contacts                    | company_id                       | character varying        | YES  |
| crm_contacts                    | first_name                       | character varying        | NO   |
| crm_contacts                    | last_name                        | character varying        | YES  |
| crm_contacts                    | designation                      | character varying        | YES  |
| crm_contacts                    | department                       | character varying        | YES  |
| crm_contacts                    | phone                            | character varying        | YES  |
| crm_contacts                    | mobile                           | character varying        | YES  |
| crm_contacts                    | email                            | character varying        | YES  |
| crm_contacts                    | linkedin                         | character varying        | YES  |
| crm_contacts                    | birthday                         | date                     | YES  |
| crm_contacts                    | roles                            | json                     | NO   |
| crm_contacts                    | is_primary                       | boolean                  | NO   |
| crm_contacts                    | created_at                       | timestamp with time zone | NO   |
| crm_contacts                    | updated_at                       | timestamp with time zone | NO   |
| crm_contacts                    | deleted_at                       | timestamp with time zone | YES  |
| crm_contacts                    | deleted_by                       | character varying        | YES  |
| crm_contacts                    | delete_reason                    | character varying        | YES  |
| crm_contacts                    | delete_batch_id                  | character varying        | YES  |
| crm_contracts                   | id                               | character varying        | NO   |
| crm_contracts                   | contract_number                  | character varying        | NO   |
| crm_contracts                   | company_id                       | character varying        | YES  |
| crm_contracts                   | deal_id                          | character varying        | YES  |
| crm_contracts                   | quotation_id                     | character varying        | YES  |
| crm_contracts                   | status                           | character varying        | NO   |
| crm_contracts                   | net_terms                        | character varying        | NO   |
| crm_contracts                   | sla                              | json                     | NO   |
| crm_contracts                   | service_areas                    | json                     | NO   |
| crm_contracts                   | vehicles                         | json                     | NO   |
| crm_contracts                   | insurance                        | json                     | NO   |
| crm_contracts                   | pricing_sheet_url                | character varying        | YES  |
| crm_contracts                   | signed_document_url              | character varying        | YES  |
| crm_contracts                   | documents                        | json                     | NO   |
| crm_contracts                   | value_cents                      | integer                  | NO   |
| crm_contracts                   | effective_from                   | date                     | YES  |
| crm_contracts                   | expiry_date                      | date                     | YES  |
| crm_contracts                   | renewal_reminder_at              | date                     | YES  |
| crm_contracts                   | created_by                       | character varying        | YES  |
| crm_contracts                   | created_at                       | timestamp with time zone | NO   |
| crm_contracts                   | updated_at                       | timestamp with time zone | NO   |
| crm_conversation_messages       | id                               | character varying        | NO   |
| crm_conversation_messages       | conversation_id                  | character varying        | NO   |
| crm_conversation_messages       | direction                        | character varying        | NO   |
| crm_conversation_messages       | body                             | text                     | NO   |
| crm_conversation_messages       | actor_type                       | character varying        | NO   |
| crm_conversation_messages       | actor_id                         | character varying        | YES  |
| crm_conversation_messages       | external_message_id              | character varying        | YES  |
| crm_conversation_messages       | metadata_json                    | json                     | NO   |
| crm_conversation_messages       | occurred_at                      | timestamp with time zone | NO   |
| crm_conversation_messages       | created_at                       | timestamp with time zone | NO   |
| crm_conversation_messages       | channel                          | character varying        | YES  |
| crm_conversation_messages       | delivery_status                  | character varying        | YES  |
| crm_conversations               | id                               | character varying        | NO   |
| crm_conversations               | lead_id                          | character varying        | NO   |
| crm_conversations               | channel                          | character varying        | NO   |
| crm_conversations               | external_thread_id               | character varying        | YES  |
| crm_conversations               | status                           | character varying        | NO   |
| crm_conversations               | created_at                       | timestamp with time zone | NO   |
| crm_conversations               | updated_at                       | timestamp with time zone | NO   |
| crm_deals                       | id                               | character varying        | NO   |
| crm_deals                       | name                             | character varying        | NO   |
| crm_deals                       | company_id                       | character varying        | YES  |
| crm_deals                       | contact_id                       | character varying        | YES  |
| crm_deals                       | pipeline                         | character varying        | NO   |
| crm_deals                       | stage                            | character varying        | NO   |
| crm_deals                       | position                         | integer                  | NO   |
| crm_deals                       | expected_revenue_cents           | integer                  | NO   |
| crm_deals                       | probability                      | integer                  | NO   |
| crm_deals                       | expected_close_date              | date                     | YES  |
| crm_deals                       | competitor                       | character varying        | YES  |
| crm_deals                       | reason_lost                      | character varying        | YES  |
| crm_deals                       | owner_id                         | character varying        | YES  |
| crm_deals                       | tags                             | json                     | NO   |
| crm_deals                       | closed_at                        | timestamp with time zone | YES  |
| crm_deals                       | created_at                       | timestamp with time zone | NO   |
| crm_deals                       | updated_at                       | timestamp with time zone | NO   |
| crm_deals                       | deleted_at                       | timestamp with time zone | YES  |
| crm_deals                       | deleted_by                       | character varying        | YES  |
| crm_deals                       | delete_reason                    | character varying        | YES  |
| crm_deals                       | delete_batch_id                  | character varying        | YES  |
| crm_documents                   | id                               | character varying        | NO   |
| crm_documents                   | entity_type                      | character varying        | NO   |
| crm_documents                   | entity_id                        | character varying        | NO   |
| crm_documents                   | name                             | character varying        | NO   |
| crm_documents                   | category                         | character varying        | NO   |
| crm_documents                   | url                              | character varying        | YES  |
| crm_documents                   | size_bytes                       | integer                  | YES  |
| crm_documents                   | version                          | integer                  | NO   |
| crm_documents                   | uploaded_by                      | character varying        | YES  |
| crm_documents                   | created_at                       | timestamp with time zone | NO   |
| crm_invoices                    | id                               | character varying        | NO   |
| crm_invoices                    | invoice_number                   | character varying        | NO   |
| crm_invoices                    | company_id                       | character varying        | YES  |
| crm_invoices                    | deal_id                          | character varying        | YES  |
| crm_invoices                    | contract_id                      | character varying        | YES  |
| crm_invoices                    | status                           | character varying        | NO   |
| crm_invoices                    | amount_cents                     | integer                  | NO   |
| crm_invoices                    | tax_cents                        | integer                  | NO   |
| crm_invoices                    | total_cents                      | integer                  | NO   |
| crm_invoices                    | currency                         | character varying        | NO   |
| crm_invoices                    | net_terms                        | character varying        | NO   |
| crm_invoices                    | line_items                       | json                     | NO   |
| crm_invoices                    | notes                            | text                     | YES  |
| crm_invoices                    | issue_date                       | date                     | YES  |
| crm_invoices                    | due_date                         | date                     | YES  |
| crm_invoices                    | paid_at                          | timestamp with time zone | YES  |
| crm_invoices                    | created_by                       | character varying        | YES  |
| crm_invoices                    | created_at                       | timestamp with time zone | NO   |
| crm_invoices                    | updated_at                       | timestamp with time zone | NO   |
| crm_invoices                    | operational_invoice_id           | character varying        | YES  |
| crm_lead_identities             | id                               | character varying        | NO   |
| crm_lead_identities             | lead_id                          | character varying        | NO   |
| crm_lead_identities             | kind                             | character varying        | NO   |
| crm_lead_identities             | value_normalized                 | character varying        | NO   |
| crm_lead_identities             | raw_value                        | character varying        | YES  |
| crm_lead_identities             | created_at                       | timestamp with time zone | NO   |
| crm_lead_ingest_events          | id                               | character varying        | NO   |
| crm_lead_ingest_events          | provider                         | character varying        | NO   |
| crm_lead_ingest_events          | external_event_id                | character varying        | NO   |
| crm_lead_ingest_events          | channel                          | character varying        | YES  |
| crm_lead_ingest_events          | lead_id                          | character varying        | YES  |
| crm_lead_ingest_events          | payload                          | jsonb                    | NO   |
| crm_lead_ingest_events          | status                           | character varying        | NO   |
| crm_lead_ingest_events          | error                            | text                     | YES  |
| crm_lead_ingest_events          | processed_at                     | timestamp with time zone | NO   |
| crm_lead_ingest_events          | created_at                       | timestamp with time zone | NO   |
| crm_leads                       | id                               | character varying        | NO   |
| crm_leads                       | company_name                     | character varying        | NO   |
| crm_leads                       | industry                         | character varying        | YES  |
| crm_leads                       | website                          | character varying        | YES  |
| crm_leads                       | business_type                    | character varying        | YES  |
| crm_leads                       | address                          | jsonb                    | NO   |
| crm_leads                       | primary_contact_name             | character varying        | YES  |
| crm_leads                       | phone                            | character varying        | YES  |
| crm_leads                       | email                            | character varying        | YES  |
| crm_leads                       | estimated_deliveries_per_month   | integer                  | YES  |
| crm_leads                       | estimated_revenue_cents          | integer                  | YES  |
| crm_leads                       | preferred_vehicle                | character varying        | YES  |
| crm_leads                       | service_area                     | character varying        | YES  |
| crm_leads                       | current_logistics_provider       | character varying        | YES  |
| crm_leads                       | source                           | character varying        | NO   |
| crm_leads                       | status                           | character varying        | NO   |
| crm_leads                       | priority                         | character varying        | NO   |
| crm_leads                       | assigned_to                      | character varying        | YES  |
| crm_leads                       | expected_close_date              | date                     | YES  |
| crm_leads                       | tags                             | json                     | NO   |
| crm_leads                       | internal_notes                   | text                     | YES  |
| crm_leads                       | lead_score                       | integer                  | NO   |
| crm_leads                       | company_id                       | character varying        | YES  |
| crm_leads                       | deal_id                          | character varying        | YES  |
| crm_leads                       | contact_id                       | character varying        | YES  |
| crm_leads                       | custom_fields                    | jsonb                    | NO   |
| crm_leads                       | created_at                       | timestamp with time zone | NO   |
| crm_leads                       | updated_at                       | timestamp with time zone | NO   |
| crm_leads                       | channel                          | character varying        | NO   |
| crm_leads                       | intent_type                      | character varying        | NO   |
| crm_leads                       | decision_status                  | character varying        | NO   |
| crm_leads                       | referred_by_merchant_id          | character varying        | YES  |
| crm_leads                       | merge_candidate_of               | character varying        | YES  |
| crm_leads                       | sla_first_response_due_at        | timestamp with time zone | YES  |
| crm_leads                       | last_touch_at                    | timestamp with time zone | YES  |
| crm_leads                       | consent                          | jsonb                    | NO   |
| crm_leads                       | quote_id                         | character varying        | YES  |
| crm_leads                       | visitor_session_id               | character varying        | YES  |
| crm_leads                       | booking_draft_id                 | character varying        | YES  |
| crm_leads                       | awaiting_reply                   | boolean                  | NO   |
| crm_leads                       | last_inbound_at                  | timestamp with time zone | YES  |
| crm_leads                       | first_response_at                | timestamp with time zone | YES  |
| crm_leads                       | order_id                         | character varying        | YES  |
| crm_leads                       | quoted_at                        | timestamp with time zone | YES  |
| crm_leads                       | won_at                           | timestamp with time zone | YES  |
| crm_leads                       | lost_at                          | timestamp with time zone | YES  |
| crm_leads                       | lost_reason                      | character varying        | YES  |
| crm_leads                       | legacy_status                    | character varying        | YES  |
| crm_leads                       | deleted_at                       | timestamp with time zone | YES  |
| crm_leads                       | deleted_by                       | character varying        | YES  |
| crm_leads                       | delete_reason                    | character varying        | YES  |
| crm_leads                       | delete_batch_id                  | character varying        | YES  |
| crm_quotations                  | id                               | character varying        | NO   |
| crm_quotations                  | quote_number                     | character varying        | NO   |
| crm_quotations                  | version                          | integer                  | NO   |
| crm_quotations                  | deal_id                          | character varying        | YES  |
| crm_quotations                  | company_id                       | character varying        | YES  |
| crm_quotations                  | status                           | character varying        | NO   |
| crm_quotations                  | line_items                       | json                     | NO   |
| crm_quotations                  | subtotal_cents                   | integer                  | NO   |
| crm_quotations                  | tax_cents                        | integer                  | NO   |
| crm_quotations                  | total_cents                      | integer                  | NO   |
| crm_quotations                  | currency                         | character varying        | NO   |
| crm_quotations                  | valid_until                      | date                     | YES  |
| crm_quotations                  | notes                            | text                     | YES  |
| crm_quotations                  | approved_by                      | character varying        | YES  |
| crm_quotations                  | sent_at                          | timestamp with time zone | YES  |
| crm_quotations                  | created_by                       | character varying        | YES  |
| crm_quotations                  | created_at                       | timestamp with time zone | NO   |
| crm_quotations                  | updated_at                       | timestamp with time zone | NO   |
| crm_quotations                  | deleted_at                       | timestamp with time zone | YES  |
| crm_quotations                  | deleted_by                       | character varying        | YES  |
| crm_quotations                  | delete_reason                    | character varying        | YES  |
| crm_quotations                  | delete_batch_id                  | character varying        | YES  |
| crm_referral_credits            | id                               | character varying        | NO   |
| crm_referral_credits            | referring_merchant_id            | character varying        | NO   |
| crm_referral_credits            | lead_id                          | character varying        | YES  |
| crm_referral_credits            | company_id                       | character varying        | YES  |
| crm_referral_credits            | amount_cents                     | integer                  | NO   |
| crm_referral_credits            | status                           | character varying        | NO   |
| crm_referral_credits            | notes                            | text                     | YES  |
| crm_referral_credits            | created_at                       | timestamp with time zone | NO   |
| crm_referral_credits            | granted_at                       | timestamp with time zone | YES  |
| crm_sales_tasks                 | id                               | character varying        | NO   |
| crm_sales_tasks                 | title                            | character varying        | NO   |
| crm_sales_tasks                 | description                      | text                     | YES  |
| crm_sales_tasks                 | task_type                        | character varying        | NO   |
| crm_sales_tasks                 | status                           | character varying        | NO   |
| crm_sales_tasks                 | priority                         | character varying        | NO   |
| crm_sales_tasks                 | entity_type                      | character varying        | YES  |
| crm_sales_tasks                 | entity_id                        | character varying        | YES  |
| crm_sales_tasks                 | company_id                       | character varying        | YES  |
| crm_sales_tasks                 | deal_id                          | character varying        | YES  |
| crm_sales_tasks                 | assigned_to                      | character varying        | YES  |
| crm_sales_tasks                 | due_at                           | timestamp with time zone | YES  |
| crm_sales_tasks                 | remind_at                        | timestamp with time zone | YES  |
| crm_sales_tasks                 | is_recurring                     | boolean                  | NO   |
| crm_sales_tasks                 | recurrence_rule                  | character varying        | YES  |
| crm_sales_tasks                 | completed_at                     | timestamp with time zone | YES  |
| crm_sales_tasks                 | created_by                       | character varying        | YES  |
| crm_sales_tasks                 | created_at                       | timestamp with time zone | NO   |
| crm_sales_tasks                 | updated_at                       | timestamp with time zone | NO   |
| crm_sales_tasks                 | zoho_event_uid                   | character varying        | YES  |
| crm_suppressions                | id                               | character varying        | NO   |
| crm_suppressions                | hash_kind                        | character varying        | NO   |
| crm_suppressions                | value_hash                       | character varying        | NO   |
| crm_suppressions                | source                           | character varying        | NO   |
| crm_suppressions                | lead_id                          | character varying        | YES  |
| crm_suppressions                | created_at                       | timestamp with time zone | NO   |
| customer_addresses              | id                               | character varying        | NO   |
| customer_addresses              | customer_id                      | character varying        | NO   |
| customer_addresses              | address_key                      | character varying        | NO   |
| customer_addresses              | label                            | character varying        | YES  |
| customer_addresses              | formatted                        | character varying        | NO   |
| customer_addresses              | postal                           | character varying        | YES  |
| customer_addresses              | lat                              | double precision         | YES  |
| customer_addresses              | lng                              | double precision         | YES  |
| customer_addresses              | place_id                         | character varying        | YES  |
| customer_addresses              | contact_name                     | character varying        | YES  |
| customer_addresses              | phone                            | character varying        | YES  |
| customer_addresses              | saved                            | boolean                  | NO   |
| customer_addresses              | use_count                        | integer                  | NO   |
| customer_addresses              | last_used_at                     | timestamp with time zone | YES  |
| customer_addresses              | created_at                       | timestamp with time zone | NO   |
| customer_addresses              | deleted_at                       | timestamp with time zone | YES  |
| customer_addresses              | deleted_by                       | character varying        | YES  |
| customer_addresses              | delete_reason                    | character varying        | YES  |
| customer_addresses              | delete_batch_id                  | character varying        | YES  |
| customer_consents               | id                               | character varying        | NO   |
| customer_consents               | customer_id                      | character varying        | NO   |
| customer_consents               | kind                             | character varying        | NO   |
| customer_consents               | granted                          | boolean                  | NO   |
| customer_consents               | source                           | character varying        | NO   |
| customer_consents               | wording                          | character varying        | YES  |
| customer_consents               | ip_hash                          | character varying        | YES  |
| customer_consents               | created_at                       | timestamp with time zone | NO   |
| customer_credits                | id                               | character varying        | NO   |
| customer_credits                | customer_id                      | character varying        | NO   |
| customer_credits                | amount_cents                     | integer                  | NO   |
| customer_credits                | currency                         | character varying        | NO   |
| customer_credits                | reason                           | character varying        | NO   |
| customer_credits                | order_id                         | character varying        | YES  |
| customer_credits                | actor                            | character varying        | NO   |
| customer_credits                | created_at                       | timestamp with time zone | NO   |
| customer_notes                  | id                               | character varying        | NO   |
| customer_notes                  | customer_id                      | character varying        | NO   |
| customer_notes                  | author                           | character varying        | NO   |
| customer_notes                  | body                             | character varying        | NO   |
| customer_notes                  | created_at                       | timestamp with time zone | NO   |
| customer_notes                  | deleted_at                       | timestamp with time zone | YES  |
| customer_notes                  | deleted_by                       | character varying        | YES  |
| customer_notes                  | delete_reason                    | character varying        | YES  |
| customer_notes                  | delete_batch_id                  | character varying        | YES  |
| customers                       | id                               | character varying        | NO   |
| customers                       | clerk_user_id                    | character varying        | NO   |
| customers                       | email                            | character varying        | NO   |
| customers                       | phone                            | character varying        | YES  |
| customers                       | visitor_session_id               | character varying        | YES  |
| customers                       | customer_reference               | character varying        | YES  |
| customers                       | created_at                       | timestamp with time zone | NO   |
| customers                       | porterchain_user_id              | character varying        | YES  |
| customers                       | privacy_status                   | character varying        | YES  |
| customers                       | privacy_hold_reference           | character varying        | YES  |
| customers                       | privacy_hold_at                  | timestamp with time zone | YES  |
| customers                       | stripe_customer_id               | character varying        | YES  |
| customers                       | full_name                        | character varying        | YES  |
| customers                       | deleted_at                       | timestamp with time zone | YES  |
| customers                       | deleted_by                       | character varying        | YES  |
| customers                       | delete_reason                    | character varying        | YES  |
| customers                       | delete_batch_id                  | character varying        | YES  |
| deleted_batches                 | id                               | character varying        | NO   |
| deleted_batches                 | entity                           | character varying        | NO   |
| deleted_batches                 | root_id                          | character varying        | NO   |
| deleted_batches                 | label                            | character varying        | NO   |
| deleted_batches                 | reason                           | character varying        | YES  |
| deleted_batches                 | deleted_by                       | character varying        | YES  |
| deleted_batches                 | deleted_by_email                 | character varying        | YES  |
| deleted_batches                 | deleted_at                       | timestamp with time zone | NO   |
| deleted_batches                 | purge_after                      | timestamp with time zone | YES  |
| deleted_batches                 | children                         | json                     | NO   |
| deleted_batches                 | side_effects                     | json                     | NO   |
| deleted_batches                 | state                            | character varying        | NO   |
| deleted_batches                 | closed_at                        | timestamp with time zone | YES  |
| deleted_batches                 | closed_by                        | character varying        | YES  |
| deleted_batches                 | outcome                          | json                     | NO   |
| dispatch_fix_actions            | id                               | character varying        | NO   |
| dispatch_fix_actions            | item_id                          | character varying        | NO   |
| dispatch_fix_actions            | order_id                         | character varying        | NO   |
| dispatch_fix_actions            | action                           | character varying        | NO   |
| dispatch_fix_actions            | params                           | json                     | NO   |
| dispatch_fix_actions            | result                           | json                     | NO   |
| dispatch_fix_actions            | approved_by                      | character varying        | NO   |
| dispatch_fix_actions            | at                               | timestamp with time zone | NO   |
| dispatch_job_offers             | id                               | character varying        | NO   |
| dispatch_job_offers             | order_id                         | character varying        | NO   |
| dispatch_job_offers             | driver_id                        | character varying        | NO   |
| dispatch_job_offers             | status                           | character varying        | NO   |
| dispatch_job_offers             | rank                             | integer                  | NO   |
| dispatch_job_offers             | offered_at                       | timestamp with time zone | NO   |
| dispatch_job_offers             | expires_at                       | timestamp with time zone | NO   |
| dispatch_job_offers             | responded_at                     | timestamp with time zone | YES  |
| dispatch_job_offers             | offered_by                       | character varying        | YES  |
| dispatch_job_offers             | meta                             | json                     | NO   |
| dispatch_plans                  | id                               | character varying        | NO   |
| dispatch_plans                  | service_date                     | date                     | NO   |
| dispatch_plans                  | status                           | character varying        | NO   |
| dispatch_plans                  | solver                           | character varying        | NO   |
| dispatch_plans                  | version                          | integer                  | NO   |
| dispatch_plans                  | parent_id                        | character varying        | YES  |
| dispatch_plans                  | summary                          | json                     | NO   |
| dispatch_plans                  | created_by                       | character varying        | YES  |
| dispatch_plans                  | created_at                       | timestamp with time zone | NO   |
| dispatch_plans                  | committed_by                     | character varying        | YES  |
| dispatch_plans                  | committed_at                     | timestamp with time zone | YES  |
| dispatch_plans                  | deleted_at                       | timestamp with time zone | YES  |
| dispatch_plans                  | deleted_by                       | character varying        | YES  |
| dispatch_plans                  | delete_reason                    | character varying        | YES  |
| dispatch_plans                  | delete_batch_id                  | character varying        | YES  |
| dispatch_routes                 | id                               | character varying        | NO   |
| dispatch_routes                 | plan_id                          | character varying        | NO   |
| dispatch_routes                 | vehicle_id                       | character varying        | NO   |
| dispatch_routes                 | driver_id                        | character varying        | YES  |
| dispatch_routes                 | vehicle_class                    | character varying        | NO   |
| dispatch_routes                 | stops                            | json                     | NO   |
| dispatch_routes                 | seconds                          | integer                  | NO   |
| dispatch_routes                 | cost_cents                       | integer                  | NO   |
| dispatch_routes                 | fill_pct                         | double precision         | NO   |
| dispatch_routes                 | status                           | character varying        | NO   |
| dispatch_routes                 | deleted_at                       | timestamp with time zone | YES  |
| dispatch_routes                 | deleted_by                       | character varying        | YES  |
| dispatch_routes                 | delete_reason                    | character varying        | YES  |
| dispatch_routes                 | delete_batch_id                  | character varying        | YES  |
| dispatch_stop_events            | id                               | character varying        | NO   |
| dispatch_stop_events            | route_id                         | character varying        | YES  |
| dispatch_stop_events            | stop_key                         | character varying        | NO   |
| dispatch_stop_events            | order_id                         | character varying        | NO   |
| dispatch_stop_events            | driver_id                        | character varying        | NO   |
| dispatch_stop_events            | event                            | character varying        | NO   |
| dispatch_stop_events            | lat                              | double precision         | YES  |
| dispatch_stop_events            | lng                              | double precision         | YES  |
| dispatch_stop_events            | accuracy_m                       | double precision         | YES  |
| dispatch_stop_events            | note                             | character varying        | YES  |
| dispatch_stop_events            | at                               | timestamp with time zone | NO   |
| dispatch_stop_events            | client_id                        | character varying        | YES  |
| dispatch_stop_times             | id                               | character varying        | NO   |
| dispatch_stop_times             | scope                            | character varying        | NO   |
| dispatch_stop_times             | scope_key                        | character varying        | NO   |
| dispatch_stop_times             | kind                             | character varying        | NO   |
| dispatch_stop_times             | median_s                         | integer                  | NO   |
| dispatch_stop_times             | samples                          | integer                  | NO   |
| dispatch_stop_times             | updated_at                       | timestamp with time zone | NO   |
| domain_events                   | id                               | character varying        | NO   |
| domain_events                   | event_type                       | character varying        | NO   |
| domain_events                   | aggregate_type                   | character varying        | NO   |
| domain_events                   | aggregate_id                     | character varying        | NO   |
| domain_events                   | correlation_id                   | character varying        | YES  |
| domain_events                   | actor_type                       | character varying        | NO   |
| domain_events                   | actor_id                         | character varying        | YES  |
| domain_events                   | payload                          | json                     | NO   |
| domain_events                   | occurred_at                      | timestamp with time zone | NO   |
| driver_bonuses                  | id                               | character varying        | NO   |
| driver_bonuses                  | driver_id                        | character varying        | NO   |
| driver_bonuses                  | title                            | character varying        | NO   |
| driver_bonuses                  | amount_cents                     | integer                  | NO   |
| driver_bonuses                  | status                           | character varying        | NO   |
| driver_bonuses                  | criteria                         | json                     | NO   |
| driver_bonuses                  | expires_at                       | timestamp with time zone | YES  |
| driver_bonuses                  | created_at                       | timestamp with time zone | NO   |
| driver_documents                | id                               | character varying        | NO   |
| driver_documents                | driver_id                        | character varying        | NO   |
| driver_documents                | doc_type                         | character varying        | NO   |
| driver_documents                | label                            | character varying        | YES  |
| driver_documents                | file_url                         | character varying        | YES  |
| driver_documents                | reference_number                 | character varying        | YES  |
| driver_documents                | status                           | character varying        | NO   |
| driver_documents                | verified                         | boolean                  | NO   |
| driver_documents                | expires_at                       | timestamp with time zone | YES  |
| driver_documents                | notes                            | text                     | YES  |
| driver_documents                | uploaded_by                      | character varying        | YES  |
| driver_documents                | created_at                       | timestamp with time zone | NO   |
| driver_documents                | updated_at                       | timestamp with time zone | NO   |
| driver_incidents                | id                               | character varying        | NO   |
| driver_incidents                | driver_id                        | character varying        | NO   |
| driver_incidents                | order_id                         | character varying        | YES  |
| driver_incidents                | incident_type                    | character varying        | NO   |
| driver_incidents                | description                      | text                     | NO   |
| driver_incidents                | location                         | json                     | NO   |
| driver_incidents                | evidence                         | json                     | NO   |
| driver_incidents                | status                           | character varying        | NO   |
| driver_incidents                | created_at                       | timestamp with time zone | NO   |
| driver_location_pings           | id                               | character varying        | NO   |
| driver_location_pings           | driver_id                        | character varying        | NO   |
| driver_location_pings           | lat                              | double precision         | NO   |
| driver_location_pings           | lng                              | double precision         | NO   |
| driver_location_pings           | accuracy_m                       | double precision         | YES  |
| driver_location_pings           | heading                          | double precision         | YES  |
| driver_location_pings           | speed_mps                        | double precision         | YES  |
| driver_location_pings           | source                           | character varying        | NO   |
| driver_location_pings           | created_at                       | timestamp with time zone | NO   |
| driver_offline_actions          | id                               | character varying        | NO   |
| driver_offline_actions          | driver_id                        | character varying        | NO   |
| driver_offline_actions          | action_type                      | character varying        | NO   |
| driver_offline_actions          | payload                          | json                     | NO   |
| driver_offline_actions          | status                           | character varying        | NO   |
| driver_offline_actions          | error                            | text                     | YES  |
| driver_offline_actions          | created_at                       | timestamp with time zone | NO   |
| driver_payout_runs              | id                               | character varying        | NO   |
| driver_payout_runs              | period_start                     | timestamp with time zone | NO   |
| driver_payout_runs              | period_end                       | timestamp with time zone | NO   |
| driver_payout_runs              | status                           | character varying        | NO   |
| driver_payout_runs              | lines                            | json                     | NO   |
| driver_payout_runs              | total_cents                      | integer                  | NO   |
| driver_payout_runs              | driver_count                     | integer                  | NO   |
| driver_payout_runs              | created_by                       | character varying        | YES  |
| driver_payout_runs              | approved_by                      | character varying        | YES  |
| driver_payout_runs              | approved_at                      | timestamp with time zone | YES  |
| driver_payout_runs              | paid_by                          | character varying        | YES  |
| driver_payout_runs              | paid_at                          | timestamp with time zone | YES  |
| driver_payout_runs              | created_at                       | timestamp with time zone | NO   |
| driver_payouts                  | id                               | character varying        | NO   |
| driver_payouts                  | driver_id                        | character varying        | NO   |
| driver_payouts                  | amount_cents                     | integer                  | NO   |
| driver_payouts                  | currency                         | character varying        | NO   |
| driver_payouts                  | status                           | character varying        | NO   |
| driver_payouts                  | reference                        | character varying        | YES  |
| driver_payouts                  | created_at                       | timestamp with time zone | NO   |
| driver_shift_activities         | id                               | character varying        | NO   |
| driver_shift_activities         | shift_id                         | character varying        | YES  |
| driver_shift_activities         | driver_id                        | character varying        | NO   |
| driver_shift_activities         | activity_type                    | character varying        | NO   |
| driver_shift_activities         | payload                          | json                     | NO   |
| driver_shift_activities         | created_at                       | timestamp with time zone | NO   |
| driver_shifts                   | id                               | character varying        | NO   |
| driver_shifts                   | driver_id                        | character varying        | NO   |
| driver_shifts                   | status                           | character varying        | NO   |
| driver_shifts                   | started_at                       | timestamp with time zone | NO   |
| driver_shifts                   | ended_at                         | timestamp with time zone | YES  |
| driver_shifts                   | break_started_at                 | timestamp with time zone | YES  |
| driver_shifts                   | vehicle_id                       | character varying        | YES  |
| driver_shifts                   | route_id                         | character varying        | YES  |
| driver_shifts                   | mileage_km                       | double precision         | NO   |
| driver_shifts                   | break_minutes                    | integer                  | NO   |
| driver_shifts                   | meta                             | json                     | NO   |
| driver_stop_meta                | id                               | character varying        | NO   |
| driver_stop_meta                | order_id                         | character varying        | NO   |
| driver_stop_meta                | driver_id                        | character varying        | NO   |
| driver_stop_meta                | meta                             | json                     | NO   |
| driver_stop_meta                | updated_at                       | timestamp with time zone | NO   |
| driver_wallet_transactions      | id                               | character varying        | NO   |
| driver_wallet_transactions      | driver_id                        | character varying        | NO   |
| driver_wallet_transactions      | tx_type                          | character varying        | NO   |
| driver_wallet_transactions      | amount_cents                     | integer                  | NO   |
| driver_wallet_transactions      | balance_after_cents              | integer                  | NO   |
| driver_wallet_transactions      | reference_id                     | character varying        | YES  |
| driver_wallet_transactions      | description                      | character varying        | YES  |
| driver_wallet_transactions      | created_at                       | timestamp with time zone | NO   |
| drivers                         | id                               | character varying        | NO   |
| drivers                         | status                           | character varying        | NO   |
| drivers                         | clerk_user_id                    | character varying        | YES  |
| drivers                         | email                            | character varying        | NO   |
| drivers                         | phone                            | character varying        | YES  |
| drivers                         | full_name                        | character varying        | NO   |
| drivers                         | license_verified                 | boolean                  | NO   |
| drivers                         | insurance_verified               | boolean                  | NO   |
| drivers                         | vehicle_verified                 | boolean                  | NO   |
| drivers                         | background_check_status          | character varying        | NO   |
| drivers                         | rating                           | double precision         | YES  |
| drivers                         | is_online                        | boolean                  | NO   |
| drivers                         | availability                     | character varying        | NO   |
| drivers                         | wallet_balance_cents             | integer                  | NO   |
| drivers                         | documents                        | json                     | NO   |
| drivers                         | performance                      | json                     | NO   |
| drivers                         | created_at                       | timestamp with time zone | NO   |
| drivers                         | updated_at                       | timestamp with time zone | NO   |
| drivers                         | medical_transport_certified      | boolean                  | NO   |
| drivers                         | porterchain_user_id              | character varying        | YES  |
| drivers                         | crm_lead_id                      | character varying        | YES  |
| drivers                         | deleted_at                       | timestamp with time zone | YES  |
| drivers                         | deleted_by                       | character varying        | YES  |
| drivers                         | delete_reason                    | character varying        | YES  |
| drivers                         | delete_batch_id                  | character varying        | YES  |
| finance_reminder_drafts         | id                               | character varying        | NO   |
| finance_reminder_drafts         | merchant_id                      | character varying        | NO   |
| finance_reminder_drafts         | invoice_ids                      | json                     | NO   |
| finance_reminder_drafts         | to_email                         | character varying        | YES  |
| finance_reminder_drafts         | subject                          | character varying        | NO   |
| finance_reminder_drafts         | body                             | text                     | NO   |
| finance_reminder_drafts         | amount_cents                     | integer                  | NO   |
| finance_reminder_drafts         | oldest_days                      | integer                  | NO   |
| finance_reminder_drafts         | status                           | character varying        | NO   |
| finance_reminder_drafts         | decided_by                       | character varying        | YES  |
| finance_reminder_drafts         | decided_at                       | timestamp with time zone | YES  |
| finance_reminder_drafts         | created_at                       | timestamp with time zone | NO   |
| fk_orphan_quarantine            | id                               | bigint                   | NO   |
| fk_orphan_quarantine            | table_name                       | character varying        | NO   |
| fk_orphan_quarantine            | column_name                      | character varying        | NO   |
| fk_orphan_quarantine            | row_pk                           | character varying        | NO   |
| fk_orphan_quarantine            | bad_value                        | character varying        | NO   |
| fk_orphan_quarantine            | row_data                         | jsonb                    | NO   |
| fk_orphan_quarantine            | action                           | character varying        | NO   |
| fk_orphan_quarantine            | quarantined_at                   | timestamp with time zone | NO   |
| forensic_audit_chain            | seq                              | bigint                   | NO   |
| forensic_audit_chain            | at                               | character varying        | NO   |
| forensic_audit_chain            | category                         | character varying        | NO   |
| forensic_audit_chain            | action                           | character varying        | NO   |
| forensic_audit_chain            | actor                            | character varying        | YES  |
| forensic_audit_chain            | target_type                      | character varying        | YES  |
| forensic_audit_chain            | target_id                        | character varying        | YES  |
| forensic_audit_chain            | ip                               | character varying        | YES  |
| forensic_audit_chain            | outcome                          | character varying        | NO   |
| forensic_audit_chain            | source                           | character varying        | NO   |
| forensic_audit_chain            | detail                           | json                     | NO   |
| forensic_audit_chain            | prev_hash                        | character varying        | NO   |
| forensic_audit_chain            | hash                             | character varying        | NO   |
| forensic_checkpoints            | id                               | bigint                   | NO   |
| forensic_checkpoints            | created_at                       | timestamp with time zone | NO   |
| forensic_checkpoints            | seq                              | bigint                   | NO   |
| forensic_checkpoints            | head_hash                        | character varying        | NO   |
| forensic_checkpoints            | key_id                           | character varying        | NO   |
| forensic_checkpoints            | algorithm                        | character varying        | NO   |
| forensic_checkpoints            | signature                        | text                     | NO   |
| identity_links                  | id                               | character varying        | NO   |
| identity_links                  | clerk_user_id                    | character varying        | NO   |
| identity_links                  | email                            | character varying        | YES  |
| identity_links                  | user_type                        | character varying        | NO   |
| identity_links                  | platform_user_id                 | character varying        | NO   |
| identity_links                  | platform_org_id                  | character varying        | YES  |
| identity_links                  | last_synced_at                   | timestamp with time zone | YES  |
| identity_links                  | created_at                       | timestamp with time zone | NO   |
| identity_links                  | updated_at                       | timestamp with time zone | NO   |
| identity_links                  | provider                         | character varying        | YES  |
| identity_links                  | issuer                           | character varying        | YES  |
| identity_links                  | subject                          | character varying        | YES  |
| identity_links                  | is_current                       | boolean                  | NO   |
| identity_links                  | is_legacy                        | boolean                  | NO   |
| identity_links                  | linked_at                        | timestamp with time zone | YES  |
| identity_links                  | deactivated_at                   | timestamp with time zone | YES  |
| identity_migration_records      | id                               | character varying        | NO   |
| identity_migration_records      | run_id                           | character varying        | NO   |
| identity_migration_records      | source_app                       | character varying        | NO   |
| identity_migration_records      | source_issuer                    | character varying        | YES  |
| identity_migration_records      | source_clerk_user_id             | character varying        | NO   |
| identity_migration_records      | internal_user_id                 | character varying        | YES  |
| identity_migration_records      | target_clerk_user_id             | character varying        | YES  |
| identity_migration_records      | status                           | character varying        | NO   |
| identity_migration_records      | conflict_reason                  | text                     | YES  |
| identity_migration_records      | proposed_roles                   | json                     | NO   |
| identity_migration_records      | detail                           | json                     | NO   |
| identity_migration_records      | created_at                       | timestamp with time zone | NO   |
| identity_migration_records      | updated_at                       | timestamp with time zone | NO   |
| identity_migration_runs         | id                               | character varying        | NO   |
| identity_migration_runs         | label                            | character varying        | NO   |
| identity_migration_runs         | status                           | character varying        | NO   |
| identity_migration_runs         | dry_run                          | boolean                  | NO   |
| identity_migration_runs         | source_summary                   | json                     | NO   |
| identity_migration_runs         | counts                           | json                     | NO   |
| identity_migration_runs         | started_at                       | timestamp with time zone | YES  |
| identity_migration_runs         | finished_at                      | timestamp with time zone | YES  |
| identity_migration_runs         | created_at                       | timestamp with time zone | NO   |
| interac_transfers               | id                               | character varying        | NO   |
| interac_transfers               | message_id                       | character varying        | NO   |
| interac_transfers               | kind                             | character varying        | NO   |
| interac_transfers               | received_at                      | timestamp with time zone | YES  |
| interac_transfers               | sender_name                      | character varying        | YES  |
| interac_transfers               | sender_email                     | character varying        | YES  |
| interac_transfers               | amount_cents                     | integer                  | NO   |
| interac_transfers               | currency                         | character varying        | NO   |
| interac_transfers               | memo                             | character varying        | YES  |
| interac_transfers               | interac_reference                | character varying        | YES  |
| interac_transfers               | auth_ok                          | boolean                  | NO   |
| interac_transfers               | auth_detail                      | character varying        | YES  |
| interac_transfers               | invoice_id                       | character varying        | YES  |
| interac_transfers               | merchant_id                      | character varying        | YES  |
| interac_transfers               | match_method                     | character varying        | YES  |
| interac_transfers               | match_note                       | character varying        | YES  |
| interac_transfers               | status                           | character varying        | NO   |
| interac_transfers               | payment_id                       | character varying        | YES  |
| interac_transfers               | reviewed_by                      | character varying        | YES  |
| interac_transfers               | reviewed_at                      | timestamp with time zone | YES  |
| interac_transfers               | review_note                      | character varying        | YES  |
| interac_transfers               | created_at                       | timestamp with time zone | NO   |
| invoice_lines                   | id                               | character varying        | NO   |
| invoice_lines                   | invoice_id                       | character varying        | NO   |
| invoice_lines                   | order_id                         | character varying        | YES  |
| invoice_lines                   | package_id                       | character varying        | YES  |
| invoice_lines                   | description                      | character varying        | NO   |
| invoice_lines                   | amount_cents                     | integer                  | NO   |
| invoice_lines                   | tax_cents                        | integer                  | NO   |
| invoice_lines                   | created_at                       | timestamp with time zone | NO   |
| invoice_lines                   | tax_province                     | character varying        | YES  |
| invoice_number_sequences        | scope                            | character varying        | NO   |
| invoice_number_sequences        | last_value                       | integer                  | NO   |
| invoice_number_sequences        | updated_at                       | timestamp with time zone | NO   |
| invoices                        | id                               | character varying        | NO   |
| invoices                        | invoice_number                   | character varying        | NO   |
| invoices                        | receipt_number                   | character varying        | YES  |
| invoices                        | order_id                         | character varying        | YES  |
| invoices                        | customer_id                      | character varying        | YES  |
| invoices                        | amount_cents                     | integer                  | NO   |
| invoices                        | tax_cents                        | integer                  | NO   |
| invoices                        | fees_cents                       | integer                  | NO   |
| invoices                        | currency                         | character varying        | NO   |
| invoices                        | stripe_receipt_url               | character varying        | YES  |
| invoices                        | pdf_url                          | character varying        | YES  |
| invoices                        | created_at                       | timestamp with time zone | NO   |
| invoices                        | merchant_id                      | character varying        | YES  |
| invoices                        | due_at                           | timestamp with time zone | YES  |
| invoices                        | billing_period_start             | timestamp with time zone | YES  |
| invoices                        | billing_period_end               | timestamp with time zone | YES  |
| invoices                        | last_reminded_at                 | timestamp with time zone | YES  |
| invoices                        | status                           | character varying        | NO   |
| invoices                        | issued_at                        | timestamp with time zone | YES  |
| invoices                        | paid_at                          | timestamp with time zone | YES  |
| invoices                        | voided_at                        | timestamp with time zone | YES  |
| invoices                        | updated_at                       | timestamp with time zone | NO   |
| invoices                        | payment_reference                | character varying        | YES  |
| invoices                        | amount_paid_cents                | integer                  | NO   |
| invoices                        | billing_kind                     | character varying        | NO   |
| invoices                        | tax_province                     | character varying        | YES  |
| invoices                        | credited_cents                   | integer                  | NO   |
| leads                           | id                               | character varying        | NO   |
| leads                           | source                           | character varying        | NO   |
| leads                           | email                            | character varying        | NO   |
| leads                           | phone                            | character varying        | YES  |
| leads                           | quote_id                         | character varying        | YES  |
| leads                           | customer_id                      | character varying        | YES  |
| leads                           | stage                            | character varying        | NO   |
| leads                           | created_at                       | timestamp with time zone | NO   |
| leads                           | crm_lead_id                      | character varying        | YES  |
| legacy_external_refs            | id                               | bigint                   | NO   |
| legacy_external_refs            | source                           | character varying        | NO   |
| legacy_external_refs            | entity                           | character varying        | NO   |
| legacy_external_refs            | entity_id                        | character varying        | NO   |
| legacy_external_refs            | field                            | character varying        | NO   |
| legacy_external_refs            | value                            | text                     | NO   |
| legacy_external_refs            | created_at                       | timestamp with time zone | NO   |
| logistics_partners              | id                               | character varying        | NO   |
| logistics_partners              | name                             | character varying        | NO   |
| logistics_partners              | kind                             | character varying        | NO   |
| logistics_partners              | lat                              | double precision         | YES  |
| logistics_partners              | lng                              | double precision         | YES  |
| logistics_partners              | fsa_coverage                     | json                     | NO   |
| logistics_partners              | rate_per_kg_cents                | integer                  | NO   |
| logistics_partners              | min_charge_cents                 | integer                  | NO   |
| logistics_partners              | transit_days                     | integer                  | NO   |
| logistics_partners              | cutoff_local                     | character varying        | YES  |
| logistics_partners              | active                           | boolean                  | NO   |
| logistics_partners              | created_at                       | timestamp with time zone | NO   |
| logistics_partners              | contact_email                    | character varying        | YES  |
| marketing_subscribers           | id                               | character varying        | NO   |
| marketing_subscribers           | email                            | character varying        | NO   |
| marketing_subscribers           | status                           | character varying        | NO   |
| marketing_subscribers           | confirm_token_hash               | character varying        | YES  |
| marketing_subscribers           | source                           | character varying        | YES  |
| marketing_subscribers           | source_page                      | character varying        | YES  |
| marketing_subscribers           | locale                           | character varying        | YES  |
| marketing_subscribers           | consent                          | jsonb                    | NO   |
| marketing_subscribers           | attribution                      | jsonb                    | NO   |
| marketing_subscribers           | lead_id                          | character varying        | YES  |
| marketing_subscribers           | confirm_sent_at                  | timestamp with time zone | YES  |
| marketing_subscribers           | confirmed_at                     | timestamp with time zone | YES  |
| marketing_subscribers           | unsubscribed_at                  | timestamp with time zone | YES  |
| marketing_subscribers           | created_at                       | timestamp with time zone | NO   |
| marketing_subscribers           | updated_at                       | timestamp with time zone | NO   |
| merchant_alerts                 | id                               | character varying        | NO   |
| merchant_alerts                 | merchant_id                      | character varying        | NO   |
| merchant_alerts                 | kind                             | character varying        | NO   |
| merchant_alerts                 | fingerprint                      | character varying        | NO   |
| merchant_alerts                 | recipient                        | character varying        | YES  |
| merchant_alerts                 | status                           | character varying        | NO   |
| merchant_alerts                 | payload                          | json                     | YES  |
| merchant_alerts                 | created_at                       | timestamp with time zone | NO   |
| merchant_api_keys               | id                               | character varying        | NO   |
| merchant_api_keys               | merchant_id                      | character varying        | NO   |
| merchant_api_keys               | name                             | character varying        | NO   |
| merchant_api_keys               | key_prefix                       | character varying        | NO   |
| merchant_api_keys               | key_hash                         | character varying        | NO   |
| merchant_api_keys               | scopes                           | json                     | NO   |
| merchant_api_keys               | environment                      | character varying        | NO   |
| merchant_api_keys               | rate_limit_per_minute            | integer                  | NO   |
| merchant_api_keys               | is_active                        | boolean                  | NO   |
| merchant_api_keys               | last_used_at                     | timestamp with time zone | YES  |
| merchant_api_keys               | created_at                       | timestamp with time zone | NO   |
| merchant_api_keys               | rotated_from_id                  | character varying        | YES  |
| merchant_api_keys               | expires_at                       | timestamp with time zone | YES  |
| merchant_api_usage_logs         | id                               | character varying        | NO   |
| merchant_api_usage_logs         | merchant_id                      | character varying        | NO   |
| merchant_api_usage_logs         | api_key_id                       | character varying        | NO   |
| merchant_api_usage_logs         | method                           | character varying        | NO   |
| merchant_api_usage_logs         | path                             | character varying        | NO   |
| merchant_api_usage_logs         | status_code                      | integer                  | NO   |
| merchant_api_usage_logs         | duration_ms                      | integer                  | NO   |
| merchant_api_usage_logs         | environment                      | character varying        | NO   |
| merchant_api_usage_logs         | created_at                       | timestamp with time zone | NO   |
| merchant_audit_logs             | id                               | character varying        | NO   |
| merchant_audit_logs             | merchant_id                      | character varying        | NO   |
| merchant_audit_logs             | actor_user_id                    | character varying        | YES  |
| merchant_audit_logs             | action                           | character varying        | NO   |
| merchant_audit_logs             | resource_type                    | character varying        | NO   |
| merchant_audit_logs             | resource_id                      | character varying        | YES  |
| merchant_audit_logs             | payload                          | json                     | NO   |
| merchant_audit_logs             | created_at                       | timestamp with time zone | NO   |
| merchant_booking_templates      | id                               | character varying        | NO   |
| merchant_booking_templates      | merchant_id                      | character varying        | NO   |
| merchant_booking_templates      | name                             | character varying        | NO   |
| merchant_booking_templates      | payload                          | json                     | NO   |
| merchant_booking_templates      | is_recurring                     | boolean                  | NO   |
| merchant_booking_templates      | recurrence_rule                  | character varying        | YES  |
| merchant_booking_templates      | created_at                       | timestamp with time zone | NO   |
| merchant_booking_templates      | deleted_at                       | timestamp with time zone | YES  |
| merchant_booking_templates      | deleted_by                       | character varying        | YES  |
| merchant_booking_templates      | delete_reason                    | character varying        | YES  |
| merchant_booking_templates      | delete_batch_id                  | character varying        | YES  |
| merchant_contracts              | id                               | character varying        | NO   |
| merchant_contracts              | merchant_id                      | character varying        | NO   |
| merchant_contracts              | name                             | character varying        | NO   |
| merchant_contracts              | rules                            | json                     | NO   |
| merchant_contracts              | minimum_monthly_commitment_cents | integer                  | NO   |
| merchant_contracts              | is_active                        | boolean                  | NO   |
| merchant_contracts              | effective_from                   | timestamp with time zone | YES  |
| merchant_contracts              | effective_to                     | timestamp with time zone | YES  |
| merchant_contracts              | created_at                       | timestamp with time zone | NO   |
| merchant_contracts              | crm_contract_id                  | character varying        | YES  |
| merchant_documents              | id                               | character varying        | NO   |
| merchant_documents              | merchant_id                      | character varying        | NO   |
| merchant_documents              | kind                             | character varying        | NO   |
| merchant_documents              | filename                         | character varying        | NO   |
| merchant_documents              | content_type                     | character varying        | NO   |
| merchant_documents              | size_bytes                       | integer                  | NO   |
| merchant_documents              | sha256                           | character varying        | NO   |
| merchant_documents              | content                          | bytea                    | YES  |
| merchant_documents              | expires_on                       | date                     | YES  |
| merchant_documents              | note                             | character varying        | YES  |
| merchant_documents              | uploaded_by                      | character varying        | YES  |
| merchant_documents              | deleted_at                       | timestamp with time zone | YES  |
| merchant_documents              | created_at                       | timestamp with time zone | NO   |
| merchant_merges                 | id                               | character varying        | NO   |
| merchant_merges                 | source_merchant_id               | character varying        | NO   |
| merchant_merges                 | target_merchant_id               | character varying        | NO   |
| merchant_merges                 | actor                            | character varying        | YES  |
| merchant_merges                 | moved                            | json                     | NO   |
| merchant_merges                 | status                           | character varying        | NO   |
| merchant_merges                 | created_at                       | timestamp with time zone | NO   |
| merchant_merges                 | undone_at                        | timestamp with time zone | YES  |
| merchant_recipients             | id                               | character varying        | NO   |
| merchant_recipients             | merchant_id                      | character varying        | NO   |
| merchant_recipients             | name                             | character varying        | NO   |
| merchant_recipients             | email                            | character varying        | YES  |
| merchant_recipients             | phone                            | character varying        | YES  |
| merchant_recipients             | company                          | character varying        | YES  |
| merchant_recipients             | default_address                  | json                     | YES  |
| merchant_recipients             | created_at                       | timestamp with time zone | NO   |
| merchant_recipients             | deleted_at                       | timestamp with time zone | YES  |
| merchant_recipients             | deleted_by                       | character varying        | YES  |
| merchant_recipients             | delete_reason                    | character varying        | YES  |
| merchant_recipients             | delete_batch_id                  | character varying        | YES  |
| merchant_users                  | id                               | character varying        | NO   |
| merchant_users                  | merchant_id                      | character varying        | NO   |
| merchant_users                  | clerk_user_id                    | character varying        | NO   |
| merchant_users                  | email                            | character varying        | NO   |
| merchant_users                  | role                             | character varying        | NO   |
| merchant_users                  | is_active                        | boolean                  | NO   |
| merchant_users                  | created_at                       | timestamp with time zone | NO   |
| merchant_users                  | porterchain_user_id              | character varying        | YES  |
| merchant_webhook_deliveries     | id                               | character varying        | NO   |
| merchant_webhook_deliveries     | merchant_id                      | character varying        | NO   |
| merchant_webhook_deliveries     | webhook_id                       | character varying        | NO   |
| merchant_webhook_deliveries     | event_type                       | character varying        | NO   |
| merchant_webhook_deliveries     | request_body                     | json                     | NO   |
| merchant_webhook_deliveries     | response_status                  | integer                  | YES  |
| merchant_webhook_deliveries     | response_body                    | text                     | YES  |
| merchant_webhook_deliveries     | attempt                          | integer                  | NO   |
| merchant_webhook_deliveries     | success                          | boolean                  | NO   |
| merchant_webhook_deliveries     | error_message                    | character varying        | YES  |
| merchant_webhook_deliveries     | duration_ms                      | integer                  | NO   |
| merchant_webhook_deliveries     | next_retry_at                    | timestamp with time zone | YES  |
| merchant_webhook_deliveries     | created_at                       | timestamp with time zone | NO   |
| merchant_webhooks               | id                               | character varying        | NO   |
| merchant_webhooks               | merchant_id                      | character varying        | NO   |
| merchant_webhooks               | url                              | character varying        | NO   |
| merchant_webhooks               | events                           | json                     | NO   |
| merchant_webhooks               | secret_hash                      | character varying        | NO   |
| merchant_webhooks               | is_active                        | boolean                  | NO   |
| merchant_webhooks               | created_at                       | timestamp with time zone | NO   |
| merchant_webhooks               | encrypted_signing_secret         | character varying        | YES  |
| merchant_webhooks               | updated_at                       | timestamp with time zone | NO   |
| merchant_webhooks               | environment                      | character varying        | NO   |
| merchants                       | id                               | character varying        | NO   |
| merchants                       | status                           | character varying        | NO   |
| merchants                       | company_name                     | character varying        | NO   |
| merchants                       | legal_name                       | character varying        | YES  |
| merchants                       | clerk_org_id                     | character varying        | YES  |
| merchants                       | email                            | character varying        | NO   |
| merchants                       | phone                            | character varying        | YES  |
| merchants                       | payment_terms                    | character varying        | NO   |
| merchants                       | credit_limit_cents               | integer                  | YES  |
| merchants                       | hst_number                       | character varying        | YES  |
| merchants                       | business_number                  | character varying        | YES  |
| merchants                       | billing_address                  | json                     | YES  |
| merchants                       | profile                          | json                     | NO   |
| merchants                       | pricing_config                   | json                     | NO   |
| merchants                       | preferred_vehicles               | json                     | YES  |
| merchants                       | delivery_zones                   | json                     | YES  |
| merchants                       | activated_at                     | timestamp with time zone | YES  |
| merchants                       | created_at                       | timestamp with time zone | NO   |
| merchants                       | updated_at                       | timestamp with time zone | NO   |
| merchants                       | billing_cycle                    | character varying        | NO   |
| merchants                       | parent_merchant_id               | character varying        | YES  |
| merchants                       | pricing_model                    | character varying        | NO   |
| merchants                       | website                          | character varying        | YES  |
| merchants                       | industry                         | character varying        | YES  |
| merchants                       | owner_admin_id                   | character varying        | YES  |
| merchants                       | segment_tags                     | json                     | YES  |
| merchants                       | credit_hold_mode                 | character varying        | NO   |
| merchants                       | credit_hold_reason               | character varying        | YES  |
| merchants                       | credit_hold_at                   | timestamp with time zone | YES  |
| merchants                       | credit_override_until            | timestamp with time zone | YES  |
| merchants                       | deleted_at                       | timestamp with time zone | YES  |
| merchants                       | deleted_by                       | character varying        | YES  |
| merchants                       | delete_reason                    | character varying        | YES  |
| merchants                       | delete_batch_id                  | character varying        | YES  |
| notification_admin_settings     | key                              | character varying        | NO   |
| notification_admin_settings     | value                            | json                     | NO   |
| notification_admin_settings     | updated_by                       | character varying        | YES  |
| notification_admin_settings     | updated_at                       | timestamp with time zone | NO   |
| notification_delivery_logs      | id                               | character varying        | NO   |
| notification_delivery_logs      | channel                          | character varying        | NO   |
| notification_delivery_logs      | template                         | character varying        | NO   |
| notification_delivery_logs      | recipient                        | character varying        | NO   |
| notification_delivery_logs      | status                           | character varying        | NO   |
| notification_delivery_logs      | error                            | text                     | YES  |
| notification_delivery_logs      | context                          | json                     | NO   |
| notification_delivery_logs      | created_at                       | timestamp with time zone | NO   |
| notification_delivery_logs      | notification_id                  | character varying        | YES  |
| notification_devices            | id                               | character varying        | NO   |
| notification_devices            | user_role                        | character varying        | NO   |
| notification_devices            | user_id                          | character varying        | NO   |
| notification_devices            | platform                         | character varying        | NO   |
| notification_devices            | device_name                      | character varying        | YES  |
| notification_devices            | app_version                      | character varying        | YES  |
| notification_devices            | os_version                       | character varying        | YES  |
| notification_devices            | fcm_token                        | character varying        | NO   |
| notification_devices            | language                         | character varying        | NO   |
| notification_devices            | timezone                         | character varying        | NO   |
| notification_devices            | notification_permission          | character varying        | NO   |
| notification_devices            | is_active                        | boolean                  | NO   |
| notification_devices            | last_seen_at                     | timestamp with time zone | YES  |
| notification_devices            | invalidated_at                   | timestamp with time zone | YES  |
| notification_devices            | created_at                       | timestamp with time zone | NO   |
| notification_devices            | updated_at                       | timestamp with time zone | NO   |
| notification_email_suppressions | email                            | character varying        | NO   |
| notification_email_suppressions | reason                           | character varying        | NO   |
| notification_email_suppressions | source                           | character varying        | NO   |
| notification_email_suppressions | active                           | boolean                  | NO   |
| notification_email_suppressions | bounce_count                     | integer                  | NO   |
| notification_email_suppressions | notification_id                  | character varying        | YES  |
| notification_email_suppressions | detail                           | text                     | YES  |
| notification_email_suppressions | released_by                      | character varying        | YES  |
| notification_email_suppressions | released_at                      | timestamp with time zone | YES  |
| notification_email_suppressions | created_at                       | timestamp with time zone | NO   |
| notification_email_suppressions | updated_at                       | timestamp with time zone | NO   |
| notification_preferences        | id                               | character varying        | NO   |
| notification_preferences        | user_role                        | character varying        | NO   |
| notification_preferences        | user_id                          | character varying        | NO   |
| notification_preferences        | category                         | character varying        | NO   |
| notification_preferences        | email_enabled                    | boolean                  | NO   |
| notification_preferences        | push_enabled                     | boolean                  | NO   |
| notification_preferences        | sms_enabled                      | boolean                  | NO   |
| notification_preferences        | in_app_enabled                   | boolean                  | NO   |
| notification_preferences        | created_at                       | timestamp with time zone | NO   |
| notification_preferences        | updated_at                       | timestamp with time zone | NO   |
| notification_records            | id                               | character varying        | NO   |
| notification_records            | event_type                       | character varying        | YES  |
| notification_records            | template_key                     | character varying        | NO   |
| notification_records            | category                         | character varying        | NO   |
| notification_records            | channel                          | character varying        | NO   |
| notification_records            | priority                         | character varying        | NO   |
| notification_records            | recipient_type                   | character varying        | NO   |
| notification_records            | recipient_id                     | character varying        | NO   |
| notification_records            | recipient_address                | character varying        | YES  |
| notification_records            | title                            | character varying        | NO   |
| notification_records            | body                             | text                     | NO   |
| notification_records            | html_body                        | text                     | YES  |
| notification_records            | deep_link                        | character varying        | YES  |
| notification_records            | status                           | character varying        | NO   |
| notification_records            | retry_count                      | integer                  | NO   |
| notification_records            | max_retries                      | integer                  | NO   |
| notification_records            | failure_reason                   | text                     | YES  |
| notification_records            | context                          | json                     | NO   |
| notification_records            | search_tags                      | json                     | NO   |
| notification_records            | is_read                          | boolean                  | NO   |
| notification_records            | is_archived                      | boolean                  | NO   |
| notification_records            | queued_at                        | timestamp with time zone | YES  |
| notification_records            | sent_at                          | timestamp with time zone | YES  |
| notification_records            | delivered_at                     | timestamp with time zone | YES  |
| notification_records            | opened_at                        | timestamp with time zone | YES  |
| notification_records            | clicked_at                       | timestamp with time zone | YES  |
| notification_records            | next_retry_at                    | timestamp with time zone | YES  |
| notification_records            | created_at                       | timestamp with time zone | NO   |
| notification_records            | updated_at                       | timestamp with time zone | NO   |
| notification_records            | is_sandbox                       | boolean                  | NO   |
| notification_records            | idempotency_key                  | character varying        | YES  |
| notification_records            | dedupe_family                    | character varying        | YES  |
| notification_records            | provider_message_id              | character varying        | YES  |
| notification_records            | delivery_status                  | character varying        | YES  |
| notification_records            | bounced_at                       | timestamp with time zone | YES  |
| notification_template_copy      | id                               | character varying        | NO   |
| notification_template_copy      | template_key                     | character varying        | NO   |
| notification_template_copy      | lang                             | character varying        | NO   |
| notification_template_copy      | version                          | integer                  | NO   |
| notification_template_copy      | subject                          | character varying        | YES  |
| notification_template_copy      | intro                            | text                     | YES  |
| notification_template_copy      | is_active                        | boolean                  | NO   |
| notification_template_copy      | created_by                       | character varying        | YES  |
| notification_template_copy      | created_at                       | timestamp with time zone | NO   |
| notification_user_settings      | id                               | character varying        | NO   |
| notification_user_settings      | user_role                        | character varying        | NO   |
| notification_user_settings      | user_id                          | character varying        | NO   |
| notification_user_settings      | quiet_hours_enabled              | boolean                  | NO   |
| notification_user_settings      | quiet_start_hour                 | integer                  | NO   |
| notification_user_settings      | quiet_end_hour                   | integer                  | NO   |
| notification_user_settings      | timezone                         | character varying        | NO   |
| notification_user_settings      | created_at                       | timestamp with time zone | NO   |
| notification_user_settings      | updated_at                       | timestamp with time zone | NO   |
| notification_user_settings      | language                         | character varying        | YES  |
| notification_user_settings      | marketing_consent_at             | timestamp with time zone | YES  |
| notification_user_settings      | marketing_consent_source         | character varying        | YES  |
| order_events                    | id                               | character varying        | NO   |
| order_events                    | order_id                         | character varying        | NO   |
| order_events                    | event_type                       | character varying        | NO   |
| order_events                    | from_state                       | character varying        | YES  |
| order_events                    | to_state                         | character varying        | YES  |
| order_events                    | actor_type                       | character varying        | NO   |
| order_events                    | actor_id                         | character varying        | YES  |
| order_events                    | correlation_id                   | character varying        | YES  |
| order_events                    | payload                          | json                     | NO   |
| order_events                    | occurred_at                      | timestamp with time zone | NO   |
| order_exceptions                | id                               | character varying        | NO   |
| order_exceptions                | order_id                         | character varying        | NO   |
| order_exceptions                | type                             | character varying        | NO   |
| order_exceptions                | status                           | character varying        | NO   |
| order_exceptions                | reported_by_type                 | character varying        | NO   |
| order_exceptions                | reported_by_id                   | character varying        | YES  |
| order_exceptions                | evidence                         | json                     | NO   |
| order_exceptions                | resolution                       | json                     | YES  |
| order_exceptions                | created_at                       | timestamp with time zone | NO   |
| order_exceptions                | resolved_at                      | timestamp with time zone | YES  |
| order_legs                      | id                               | character varying        | NO   |
| order_legs                      | order_id                         | character varying        | NO   |
| order_legs                      | seq                              | integer                  | NO   |
| order_legs                      | mode                             | character varying        | NO   |
| order_legs                      | partner_id                       | character varying        | YES  |
| order_legs                      | from_label                       | character varying        | NO   |
| order_legs                      | to_label                         | character varying        | NO   |
| order_legs                      | status                           | character varying        | NO   |
| order_legs                      | est_cost_cents                   | integer                  | NO   |
| order_legs                      | meta                             | json                     | NO   |
| order_legs                      | created_at                       | timestamp with time zone | NO   |
| order_ratings                   | id                               | character varying        | NO   |
| order_ratings                   | order_id                         | character varying        | NO   |
| order_ratings                   | score                            | integer                  | NO   |
| order_ratings                   | comment                          | character varying        | YES  |
| order_ratings                   | created_at                       | timestamp with time zone | NO   |
| orders                          | id                               | character varying        | NO   |
| orders                          | order_number                     | character varying        | NO   |
| orders                          | tracking_number                  | character varying        | NO   |
| orders                          | state                            | character varying        | NO   |
| orders                          | quote_id                         | character varying        | YES  |
| orders                          | customer_id                      | character varying        | YES  |
| orders                          | merchant_id                      | character varying        | YES  |
| orders                          | payment_terms                    | character varying        | NO   |
| orders                          | amount_cents                     | integer                  | NO   |
| orders                          | currency                         | character varying        | NO   |
| orders                          | stripe_payment_intent_id         | character varying        | YES  |
| orders                          | assigned_driver_id               | character varying        | YES  |
| orders                          | pickup                           | json                     | NO   |
| orders                          | dropoff                          | json                     | NO   |
| orders                          | scheduled_at                     | timestamp with time zone | NO   |
| orders                          | internal_reference               | character varying        | YES  |
| orders                          | purchase_order_number            | character varying        | YES  |
| orders                          | cost_centre                      | character varying        | YES  |
| orders                          | special_instructions             | text                     | YES  |
| orders                          | created_at                       | timestamp with time zone | NO   |
| orders                          | updated_at                       | timestamp with time zone | NO   |
| orders                          | order_source                     | character varying        | NO   |
| orders                          | order_type                       | character varying        | NO   |
| orders                          | compliance_metadata              | json                     | YES  |
| orders                          | idempotency_key                  | character varying        | YES  |
| orders                          | is_sandbox                       | boolean                  | NO   |
| orders                          | sla_deadline_at                  | timestamp with time zone | YES  |
| orders                          | deleted_at                       | timestamp with time zone | YES  |
| orders                          | deleted_by                       | character varying        | YES  |
| orders                          | delete_reason                    | character varying        | YES  |
| orders                          | delete_batch_id                  | character varying        | YES  |
| package_external_identifiers    | id                               | character varying        | NO   |
| package_external_identifiers    | package_id                       | character varying        | NO   |
| package_external_identifiers    | order_id                         | character varying        | NO   |
| package_external_identifiers    | source                           | character varying        | NO   |
| package_external_identifiers    | value                            | character varying        | NO   |
| package_external_identifiers    | value_normalized                 | character varying        | NO   |
| package_external_identifiers    | created_by                       | character varying        | YES  |
| package_external_identifiers    | created_at                       | timestamp with time zone | NO   |
| packages                        | id                               | character varying        | NO   |
| packages                        | order_id                         | character varying        | NO   |
| packages                        | stop_key                         | text                     | YES  |
| packages                        | parcel_index                     | integer                  | NO   |
| packages                        | total_parcels                    | integer                  | NO   |
| packages                        | tracking_suffix                  | text                     | NO   |
| packages                        | weight_kg                        | numeric                  | YES  |
| packages                        | dimensions                       | json                     | YES  |
| packages                        | status                           | character varying        | NO   |
| packages                        | stop_sequence                    | integer                  | YES  |
| packages                        | created_at                       | timestamp with time zone | NO   |
| packages                        | updated_at                       | timestamp with time zone | NO   |
| packages                        | barcode                          | character varying        | YES  |
| packages                        | label_url                        | character varying        | YES  |
| packages                        | signature_required               | boolean                  | NO   |
| packages                        | item_key                         | character varying        | YES  |
| packages                        | item_label                       | character varying        | YES  |
| packages                        | box_index                        | integer                  | YES  |
| packages                        | box_count                        | integer                  | YES  |
| packages                        | deleted_at                       | timestamp with time zone | YES  |
| packages                        | deleted_by                       | character varying        | YES  |
| packages                        | delete_reason                    | character varying        | YES  |
| packages                        | delete_batch_id                  | character varying        | YES  |
| payments                        | id                               | character varying        | NO   |
| payments                        | quote_id                         | character varying        | YES  |
| payments                        | order_id                         | character varying        | YES  |
| payments                        | customer_id                      | character varying        | YES  |
| payments                        | status                           | character varying        | NO   |
| payments                        | amount_cents                     | integer                  | NO   |
| payments                        | currency                         | character varying        | NO   |
| payments                        | stripe_payment_intent_id         | character varying        | YES  |
| payments                        | stripe_checkout_session_id       | character varying        | YES  |
| payments                        | payment_reference                | character varying        | YES  |
| payments                        | payment_method                   | character varying        | YES  |
| payments                        | transaction_id                   | character varying        | YES  |
| payments                        | receipt_url                      | character varying        | YES  |
| payments                        | failure_reason                   | character varying        | YES  |
| payments                        | retry_count                      | integer                  | NO   |
| payments                        | created_at                       | timestamp with time zone | NO   |
| payments                        | updated_at                       | timestamp with time zone | NO   |
| payments                        | invoice_id                       | character varying        | YES  |
| porterchain_users               | id                               | character varying        | NO   |
| porterchain_users               | clerk_user_id                    | character varying        | NO   |
| porterchain_users               | email                            | character varying        | YES  |
| porterchain_users               | phone                            | character varying        | YES  |
| porterchain_users               | role                             | character varying        | NO   |
| porterchain_users               | status                           | character varying        | NO   |
| porterchain_users               | profile                          | json                     | NO   |
| porterchain_users               | last_synced_at                   | timestamp with time zone | YES  |
| porterchain_users               | created_at                       | timestamp with time zone | NO   |
| porterchain_users               | updated_at                       | timestamp with time zone | NO   |
| porterchain_users               | onboarding_status                | character varying        | NO   |
| porterchain_users               | default_workspace                | character varying        | YES  |
| pricing_fsa_rates               | id                               | character varying        | NO   |
| pricing_fsa_rates               | merchant_id                      | character varying        | YES  |
| pricing_fsa_rates               | origin_fsa                       | character varying        | YES  |
| pricing_fsa_rates               | dest_fsa                         | character varying        | NO   |
| pricing_fsa_rates               | vehicle_class                    | character varying        | YES  |
| pricing_fsa_rates               | flat_cents                       | integer                  | NO   |
| pricing_fsa_rates               | includes_location_fees           | boolean                  | NO   |
| pricing_fsa_rates               | label                            | character varying        | YES  |
| pricing_fsa_rates               | is_active                        | boolean                  | NO   |
| pricing_fsa_rates               | config                           | json                     | NO   |
| pricing_fsa_rates               | created_at                       | timestamp with time zone | NO   |
| pricing_fsa_rates               | updated_at                       | timestamp with time zone | NO   |
| pricing_tariffs                 | id                               | character varying        | NO   |
| pricing_tariffs                 | name                             | character varying        | NO   |
| pricing_tariffs                 | tariff_type                      | character varying        | NO   |
| pricing_tariffs                 | vehicle_class                    | character varying        | YES  |
| pricing_tariffs                 | zone                             | character varying        | YES  |
| pricing_tariffs                 | merchant_id                      | character varying        | YES  |
| pricing_tariffs                 | base_cents                       | integer                  | NO   |
| pricing_tariffs                 | per_km_cents                     | integer                  | NO   |
| pricing_tariffs                 | fuel_surcharge_percent           | double precision         | NO   |
| pricing_tariffs                 | is_active                        | boolean                  | NO   |
| pricing_tariffs                 | config                           | json                     | NO   |
| pricing_tariffs                 | created_at                       | timestamp with time zone | NO   |
| pricing_tariffs                 | deleted_at                       | timestamp with time zone | YES  |
| pricing_tariffs                 | deleted_by                       | character varying        | YES  |
| pricing_tariffs                 | delete_reason                    | character varying        | YES  |
| pricing_tariffs                 | delete_batch_id                  | character varying        | YES  |
| pricing_zones                   | id                               | character varying        | NO   |
| pricing_zones                   | code                             | character varying        | NO   |
| pricing_zones                   | name                             | character varying        | NO   |
| pricing_zones                   | bounds                           | json                     | NO   |
| pricing_zones                   | multiplier                       | double precision         | NO   |
| pricing_zones                   | is_active                        | boolean                  | NO   |
| pricing_zones                   | created_at                       | timestamp with time zone | NO   |
| pricing_zones                   | deleted_at                       | timestamp with time zone | YES  |
| pricing_zones                   | deleted_by                       | character varying        | YES  |
| pricing_zones                   | delete_reason                    | character varying        | YES  |
| pricing_zones                   | delete_batch_id                  | character varying        | YES  |
| privacy_deletion_jobs           | id                               | character varying        | NO   |
| privacy_deletion_jobs           | customer_id                      | character varying        | YES  |
| privacy_deletion_jobs           | reference                        | character varying        | NO   |
| privacy_deletion_jobs           | status                           | character varying        | NO   |
| privacy_deletion_jobs           | source                           | character varying        | NO   |
| privacy_deletion_jobs           | plan                             | json                     | NO   |
| privacy_deletion_jobs           | result                           | json                     | YES  |
| privacy_deletion_jobs           | reviewer                         | character varying        | YES  |
| privacy_deletion_jobs           | review_note                      | character varying        | YES  |
| privacy_deletion_jobs           | due_at                           | timestamp with time zone | YES  |
| privacy_deletion_jobs           | reviewed_at                      | timestamp with time zone | YES  |
| privacy_deletion_jobs           | executed_at                      | timestamp with time zone | YES  |
| privacy_deletion_jobs           | created_at                       | timestamp with time zone | NO   |
| promotions                      | id                               | character varying        | NO   |
| promotions                      | code                             | character varying        | NO   |
| promotions                      | promotion_type                   | character varying        | NO   |
| promotions                      | merchant_id                      | character varying        | YES  |
| promotions                      | discount_percent                 | double precision         | YES  |
| promotions                      | discount_cents                   | integer                  | YES  |
| promotions                      | is_active                        | boolean                  | NO   |
| promotions                      | expires_at                       | timestamp with time zone | YES  |
| promotions                      | config                           | json                     | NO   |
| promotions                      | created_at                       | timestamp with time zone | NO   |
| promotions                      | deleted_at                       | timestamp with time zone | YES  |
| promotions                      | deleted_by                       | character varying        | YES  |
| promotions                      | delete_reason                    | character varying        | YES  |
| promotions                      | delete_batch_id                  | character varying        | YES  |
| quotes                          | id                               | character varying        | NO   |
| quotes                          | state                            | character varying        | NO   |
| quotes                          | anonymous_session_id             | character varying        | YES  |
| quotes                          | customer_id                      | character varying        | YES  |
| quotes                          | pickup                           | json                     | NO   |
| quotes                          | dropoff                          | json                     | NO   |
| quotes                          | vehicle_class                    | character varying        | NO   |
| quotes                          | package_type                     | character varying        | NO   |
| quotes                          | weight_kg                        | double precision         | YES  |
| quotes                          | dimensions                       | character varying        | YES  |
| quotes                          | declared_value_cents             | integer                  | YES  |
| quotes                          | additional_stops                 | json                     | YES  |
| quotes                          | special_instructions             | text                     | YES  |
| quotes                          | visitor_session_id               | character varying        | YES  |
| quotes                          | scheduled_at                     | timestamp with time zone | NO   |
| quotes                          | schedule_mode                    | character varying        | NO   |
| quotes                          | amount_cents                     | integer                  | NO   |
| quotes                          | currency                         | character varying        | NO   |
| quotes                          | pricing_breakdown                | json                     | NO   |
| quotes                          | distance_meters                  | integer                  | YES  |
| quotes                          | email                            | character varying        | YES  |
| quotes                          | phone                            | character varying        | YES  |
| quotes                          | consent                          | json                     | YES  |
| quotes                          | stripe_checkout_session_id       | character varying        | YES  |
| quotes                          | expires_at                       | timestamp with time zone | NO   |
| quotes                          | created_at                       | timestamp with time zone | NO   |
| quotes                          | updated_at                       | timestamp with time zone | NO   |
| quotes                          | parcels                          | json                     | YES  |
| reorder_nudges                  | id                               | character varying        | NO   |
| reorder_nudges                  | customer_id                      | character varying        | NO   |
| reorder_nudges                  | order_id                         | character varying        | NO   |
| reorder_nudges                  | status                           | character varying        | NO   |
| reorder_nudges                  | reason                           | character varying        | NO   |
| reorder_nudges                  | approved_by                      | character varying        | YES  |
| reorder_nudges                  | created_at                       | timestamp with time zone | NO   |
| reorder_nudges                  | decided_at                       | timestamp with time zone | YES  |
| route_center_templates          | id                               | character varying        | NO   |
| route_center_templates          | name                             | character varying        | NO   |
| route_center_templates          | template_type                    | character varying        | NO   |
| route_center_templates          | merchant_id                      | character varying        | YES  |
| route_center_templates          | zone                             | character varying        | YES  |
| route_center_templates          | schedule                         | json                     | NO   |
| route_center_templates          | stops                            | json                     | NO   |
| route_center_templates          | config                           | json                     | NO   |
| route_center_templates          | is_active                        | boolean                  | NO   |
| route_center_templates          | created_by                       | character varying        | YES  |
| route_center_templates          | created_at                       | timestamp with time zone | NO   |
| saved_addresses                 | id                               | character varying        | NO   |
| saved_addresses                 | merchant_id                      | character varying        | NO   |
| saved_addresses                 | label                            | character varying        | NO   |
| saved_addresses                 | address_type                     | character varying        | NO   |
| saved_addresses                 | formatted                        | character varying        | NO   |
| saved_addresses                 | place_id                         | character varying        | YES  |
| saved_addresses                 | lat                              | double precision         | YES  |
| saved_addresses                 | lng                              | double precision         | YES  |
| saved_addresses                 | is_default                       | boolean                  | NO   |
| saved_addresses                 | created_at                       | timestamp with time zone | NO   |
| saved_addresses                 | postal                           | character varying        | YES  |
| saved_addresses                 | address_id                       | character varying        | YES  |
| shopify_data_subject_requests   | id                               | character varying        | NO   |
| shopify_data_subject_requests   | shop_id                          | character varying        | YES  |
| shopify_data_subject_requests   | merchant_id                      | character varying        | YES  |
| shopify_data_subject_requests   | topic                            | character varying        | NO   |
| shopify_data_subject_requests   | shopify_webhook_id               | character varying        | NO   |
| shopify_data_subject_requests   | shopify_customer_id              | character varying        | YES  |
| shopify_data_subject_requests   | email_hash                       | character varying        | YES  |
| shopify_data_subject_requests   | phone_hash                       | character varying        | YES  |
| shopify_data_subject_requests   | orders_requested                 | json                     | YES  |
| shopify_data_subject_requests   | status                           | character varying        | NO   |
| shopify_data_subject_requests   | due_at                           | timestamp with time zone | NO   |
| shopify_data_subject_requests   | export_ciphertext                | text                     | YES  |
| shopify_data_subject_requests   | orders_touched                   | integer                  | NO   |
| shopify_data_subject_requests   | hold_reason                      | character varying        | YES  |
| shopify_data_subject_requests   | fulfilled_at                     | timestamp with time zone | YES  |
| shopify_data_subject_requests   | created_at                       | timestamp with time zone | NO   |
| shopify_ingress_dlq             | id                               | character varying        | NO   |
| shopify_ingress_dlq             | merchant_id                      | character varying        | NO   |
| shopify_ingress_dlq             | shop_id                          | character varying        | YES  |
| shopify_ingress_dlq             | shop_domain                      | character varying        | NO   |
| shopify_ingress_dlq             | topic                            | character varying        | YES  |
| shopify_ingress_dlq             | action                           | character varying        | NO   |
| shopify_ingress_dlq             | shopify_order_id                 | character varying        | YES  |
| shopify_ingress_dlq             | reason_code                      | character varying        | NO   |
| shopify_ingress_dlq             | detail                           | text                     | YES  |
| shopify_ingress_dlq             | raw_body                         | text                     | NO   |
| shopify_ingress_dlq             | status                           | character varying        | NO   |
| shopify_ingress_dlq             | attempts                         | integer                  | NO   |
| shopify_ingress_dlq             | porterchain_order_id             | character varying        | YES  |
| shopify_ingress_dlq             | resolved_at                      | timestamp with time zone | YES  |
| shopify_ingress_dlq             | resolved_by_admin_id             | character varying        | YES  |
| shopify_ingress_dlq             | created_at                       | timestamp with time zone | NO   |
| shopify_ingress_dlq             | updated_at                       | timestamp with time zone | NO   |
| shopify_rate_quotes             | id                               | character varying        | NO   |
| shopify_rate_quotes             | shop_id                          | character varying        | NO   |
| shopify_rate_quotes             | merchant_id                      | character varying        | NO   |
| shopify_rate_quotes             | request_hash                     | character varying        | NO   |
| shopify_rate_quotes             | total_cents                      | integer                  | NO   |
| shopify_rate_quotes             | currency                         | character varying        | NO   |
| shopify_rate_quotes             | breakdown                        | json                     | NO   |
| shopify_rate_quotes             | pickup_postal                    | character varying        | YES  |
| shopify_rate_quotes             | dropoff_postal                   | character varying        | YES  |
| shopify_rate_quotes             | weight_kg                        | character varying        | YES  |
| shopify_rate_quotes             | expires_at                       | timestamp with time zone | NO   |
| shopify_rate_quotes             | created_at                       | timestamp with time zone | NO   |
| shopify_shops                   | id                               | character varying        | NO   |
| shopify_shops                   | merchant_id                      | character varying        | NO   |
| shopify_shops                   | shop_domain                      | character varying        | NO   |
| shopify_shops                   | encrypted_access_token           | text                     | YES  |
| shopify_shops                   | encrypted_webhook_secret         | character varying        | YES  |
| shopify_shops                   | default_pickup_address_id        | character varying        | YES  |
| shopify_shops                   | shopify_shop_gid                 | character varying        | YES  |
| shopify_shops                   | scopes                           | character varying        | YES  |
| shopify_shops                   | installed_at                     | timestamp with time zone | YES  |
| shopify_shops                   | uninstalled_at                   | timestamp with time zone | YES  |
| shopify_shops                   | last_webhook_at                  | timestamp with time zone | YES  |
| shopify_shops                   | created_at                       | timestamp with time zone | NO   |
| shopify_shops                   | updated_at                       | timestamp with time zone | NO   |
| shopify_shops                   | ingress_paused                   | boolean                  | NO   |
| shopify_shops                   | auto_dispatch                    | boolean                  | NO   |
| shopify_shops                   | default_vehicle_class            | character varying        | YES  |
| shopify_shops                   | default_package_type             | character varying        | YES  |
| shopify_shops                   | carrier_service_gid              | character varying        | YES  |
| shopify_shops                   | fulfillment_service_gid          | character varying        | YES  |
| shopify_shops                   | location_gid                     | character varying        | YES  |
| shopify_shops                   | seen_webhook_ids                 | json                     | YES  |
| shopify_shops                   | access_token_expires_at          | timestamp with time zone | YES  |
| shopify_shops                   | encrypted_refresh_token          | text                     | YES  |
| shopify_shops                   | refresh_token_expires_at         | timestamp with time zone | YES  |
| shopify_shops                   | token_status                     | character varying        | YES  |
| staff_webauthn_credentials      | id                               | character varying        | NO   |
| staff_webauthn_credentials      | admin_user_id                    | character varying        | NO   |
| staff_webauthn_credentials      | credential_id                    | character varying        | NO   |
| staff_webauthn_credentials      | public_key                       | text                     | NO   |
| staff_webauthn_credentials      | sign_count                       | integer                  | NO   |
| staff_webauthn_credentials      | device_label                     | character varying        | YES  |
| staff_webauthn_credentials      | created_at                       | timestamp with time zone | NO   |
| staff_webauthn_credentials      | last_used_at                     | timestamp with time zone | YES  |
| standing_orders                 | id                               | character varying        | NO   |
| standing_orders                 | merchant_id                      | character varying        | NO   |
| standing_orders                 | booking_template_id              | character varying        | NO   |
| standing_orders                 | recurrence_rule                  | character varying        | NO   |
| standing_orders                 | next_run_at                      | timestamp with time zone | NO   |
| standing_orders                 | last_run_at                      | timestamp with time zone | YES  |
| standing_orders                 | last_order_id                    | character varying        | YES  |
| standing_orders                 | is_active                        | boolean                  | NO   |
| standing_orders                 | created_at                       | timestamp with time zone | NO   |
| standing_orders                 | last_error                       | text                     | YES  |
| standing_orders                 | deleted_at                       | timestamp with time zone | YES  |
| standing_orders                 | deleted_by                       | character varying        | YES  |
| standing_orders                 | delete_reason                    | character varying        | YES  |
| standing_orders                 | delete_batch_id                  | character varying        | YES  |
| stops                           | id                               | character varying        | NO   |
| stops                           | order_id                         | character varying        | NO   |
| stops                           | sequence                         | integer                  | NO   |
| stops                           | kind                             | character varying        | NO   |
| stops                           | address_id                       | character varying        | YES  |
| stops                           | window_start                     | timestamp with time zone | YES  |
| stops                           | window_end                       | timestamp with time zone | YES  |
| stops                           | status                           | character varying        | NO   |
| stops                           | created_at                       | timestamp with time zone | NO   |
| stripe_payouts                  | id                               | character varying        | NO   |
| stripe_payouts                  | stripe_payout_id                 | character varying        | NO   |
| stripe_payouts                  | status                           | character varying        | NO   |
| stripe_payouts                  | amount_cents                     | integer                  | NO   |
| stripe_payouts                  | currency                         | character varying        | NO   |
| stripe_payouts                  | arrival_date                     | timestamp with time zone | YES  |
| stripe_payouts                  | gross_cents                      | integer                  | YES  |
| stripe_payouts                  | fee_cents                        | integer                  | YES  |
| stripe_payouts                  | refund_cents                     | integer                  | YES  |
| stripe_payouts                  | dispute_cents                    | integer                  | YES  |
| stripe_payouts                  | other_cents                      | integer                  | YES  |
| stripe_payouts                  | matched_count                    | integer                  | YES  |
| stripe_payouts                  | unmatched_count                  | integer                  | YES  |
| stripe_payouts                  | difference_cents                 | integer                  | YES  |
| stripe_payouts                  | reconciled_at                    | timestamp with time zone | YES  |
| stripe_payouts                  | created_at                       | timestamp with time zone | NO   |
| stripe_webhook_events           | id                               | character varying        | NO   |
| stripe_webhook_events           | stripe_event_id                  | character varying        | NO   |
| stripe_webhook_events           | event_type                       | character varying        | NO   |
| stripe_webhook_events           | status                           | character varying        | NO   |
| stripe_webhook_events           | processed_at                     | timestamp with time zone | NO   |
| support_tickets                 | id                               | character varying        | NO   |
| support_tickets                 | status                           | character varying        | NO   |
| support_tickets                 | priority                         | character varying        | NO   |
| support_tickets                 | subject                          | character varying        | NO   |
| support_tickets                 | description                      | text                     | YES  |
| support_tickets                 | customer_id                      | character varying        | YES  |
| support_tickets                 | merchant_id                      | character varying        | YES  |
| support_tickets                 | driver_id                        | character varying        | YES  |
| support_tickets                 | order_id                         | character varying        | YES  |
| support_tickets                 | assigned_to                      | character varying        | YES  |
| support_tickets                 | created_at                       | timestamp with time zone | NO   |
| support_tickets                 | updated_at                       | timestamp with time zone | NO   |
| support_tickets                 | category                         | character varying        | NO   |
| support_tickets                 | ticket_data                      | json                     | NO   |
| support_tickets                 | deleted_at                       | timestamp with time zone | YES  |
| support_tickets                 | deleted_by                       | character varying        | YES  |
| support_tickets                 | delete_reason                    | character varying        | YES  |
| support_tickets                 | delete_batch_id                  | character varying        | YES  |
| system_config                   | key                              | character varying        | NO   |
| system_config                   | value                            | json                     | NO   |
| system_config                   | updated_at                       | timestamp with time zone | NO   |
| tax_registrations               | id                               | character varying        | NO   |
| tax_registrations               | gst_hst_number                   | character varying        | YES  |
| tax_registrations               | legal_name                       | character varying        | YES  |
| tax_registrations               | effective_from                   | date                     | NO   |
| tax_registrations               | note                             | text                     | YES  |
| tax_registrations               | created_by                       | character varying        | YES  |
| tax_registrations               | created_at                       | timestamp with time zone | NO   |
| user_emails                     | id                               | character varying        | NO   |
| user_emails                     | user_id                          | character varying        | NO   |
| user_emails                     | normalized_email                 | character varying        | NO   |
| user_emails                     | is_verified                      | boolean                  | NO   |
| user_emails                     | is_primary                       | boolean                  | NO   |
| user_emails                     | source                           | character varying        | NO   |
| user_emails                     | created_at                       | timestamp with time zone | NO   |
| user_emails                     | updated_at                       | timestamp with time zone | NO   |
| user_invitations                | id                               | character varying        | NO   |
| user_invitations                | email                            | character varying        | NO   |
| user_invitations                | user_type                        | character varying        | NO   |
| user_invitations                | role                             | character varying        | NO   |
| user_invitations                | status                           | character varying        | NO   |
| user_invitations                | clerk_invitation_id              | character varying        | YES  |
| user_invitations                | clerk_user_id                    | character varying        | YES  |
| user_invitations                | platform_user_id                 | character varying        | YES  |
| user_invitations                | merchant_id                      | character varying        | YES  |
| user_invitations                | invited_by                       | character varying        | YES  |
| user_invitations                | redirect_url                     | character varying        | YES  |
| user_invitations                | metadata                         | json                     | NO   |
| user_invitations                | created_at                       | timestamp with time zone | NO   |
| user_invitations                | accepted_at                      | timestamp with time zone | YES  |
| user_invitations                | revoked_at                       | timestamp with time zone | YES  |
| user_invitations                | porterchain_user_id              | character varying        | YES  |
| vehicles                        | id                               | character varying        | NO   |
| vehicles                        | driver_id                        | character varying        | YES  |
| vehicles                        | vehicle_class                    | character varying        | NO   |
| vehicles                        | plate_number                     | character varying        | NO   |
| vehicles                        | make_model                       | character varying        | YES  |
| vehicles                        | capacity_kg                      | double precision         | YES  |
| vehicles                        | compliance_expires_at            | timestamp with time zone | YES  |
| vehicles                        | is_active                        | boolean                  | NO   |
| vehicles                        | created_at                       | timestamp with time zone | NO   |
| vehicles                        | capabilities                     | json                     | NO   |
| vehicles                        | deleted_at                       | timestamp with time zone | YES  |
| vehicles                        | deleted_by                       | character varying        | YES  |
| vehicles                        | delete_reason                    | character varying        | YES  |
| vehicles                        | delete_batch_id                  | character varying        | YES  |
| visitor_sessions                | id                               | character varying        | NO   |
| visitor_sessions                | ip_hash                          | character varying        | YES  |
| visitor_sessions                | browser                          | character varying        | YES  |
| visitor_sessions                | utm_source                       | character varying        | YES  |
| visitor_sessions                | utm_medium                       | character varying        | YES  |
| visitor_sessions                | utm_campaign                     | character varying        | YES  |
| visitor_sessions                | referrer                         | character varying        | YES  |
| visitor_sessions                | device                           | character varying        | YES  |
| visitor_sessions                | location                         | json                     | YES  |
| visitor_sessions                | quote_generated                  | boolean                  | NO   |
| visitor_sessions                | last_quote_id                    | character varying        | YES  |
| visitor_sessions                | created_at                       | timestamp with time zone | NO   |
| visitor_sessions                | updated_at                       | timestamp with time zone | NO   |
| visitor_sessions                | customer_id                      | character varying        | YES  |
| visitor_sessions                | signals                          | json                     | YES  |
| visitor_sessions                | touch_count                      | integer                  | NO   |
| visitor_sessions                | intent_score                     | integer                  | NO   |

</details>
