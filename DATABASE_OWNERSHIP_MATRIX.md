# Database Ownership Matrix

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Authority:** [masterrule.md](./masterrule.md) §9  
**Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md)

Porterchain → **PostgreSQL 16** | Fleetbase → **MySQL 8** | Redis → cache / queue (not SoT)

---

## Summary

| Store               | Owner                    | Engine            | Business authority              |
| ------------------- | ------------------------ | ----------------- | ------------------------------- |
| Porterchain domain  | Porterchain API          | **PostgreSQL 16** | Commercial, CRM, billing, admin |
| Fleetbase execution | Fleetbase Core (Laravel) | **MySQL 8**       | Dispatch, GPS, routes, POD      |
| Async jobs / cache  | Porterchain worker + API | **Redis 7**       | Ephemeral — not source of truth |

**Synchronization:** Fleetbase Adapter via HTTP; sync state in PostgreSQL (`fleetbase_sync_*`). **No direct MySQL connection** from Porterchain API.

---

## Porterchain PostgreSQL tables

| Table                         | Owner       | Purpose                    | Business critical | Operational | Sync required                 |
| ----------------------------- | ----------- | -------------------------- | ----------------- | ----------- | ----------------------------- |
| `customers`                   | Porterchain | Retail / customer identity | Yes               | No          | No                            |
| `visitor_sessions`            | Porterchain | Anonymous session merge    | Yes               | No          | No                            |
| `quotes`                      | Porterchain | Pricing quotes             | Yes               | No          | No                            |
| `bookings`                    | Porterchain | Confirmed bookings         | Yes               | No          | Outbound → Fleetbase (order)  |
| `booking_drafts`              | Porterchain | Server-side draft state    | Yes               | No          | No                            |
| `booking_draft_audits`        | Porterchain | Draft transition audit     | Yes               | No          | No                            |
| `orders`                      | Porterchain | Commercial order mirror    | Yes               | Yes         | Bidirectional via adapter     |
| `order_events`                | Porterchain | Order timeline             | Yes               | Yes         | Inbound from Fleetbase status |
| `order_exceptions`            | Porterchain | Ops exceptions             | Yes               | Yes         | Partial                       |
| `payments`                    | Porterchain | Stripe payment records     | Yes               | No          | No                            |
| `invoices`                    | Porterchain | Billing documents          | Yes               | No          | No                            |
| `billing_ledger_entries`      | Porterchain | Billing engine ledger      | Yes               | No          | No                            |
| `abandoned_checkouts`         | Porterchain | Checkout recovery          | Yes               | No          | No                            |
| `leads`                       | Porterchain | Website lead capture       | Yes               | No          | No                            |
| `domain_events`               | Porterchain | Event bus persistence      | Yes               | Yes         | No                            |
| `merchants`                   | Porterchain | Merchant accounts          | Yes               | No          | No                            |
| `merchant_users`              | Porterchain | Merchant portal users      | Yes               | No          | No                            |
| `merchant_api_keys`           | Porterchain | API gateway keys           | Yes               | No          | No                            |
| `merchant_webhooks`           | Porterchain | Outbound webhook config    | Yes               | No          | No                            |
| `merchant_webhook_deliveries` | Porterchain | Webhook delivery log       | No                | Yes         | No                            |
| `merchant_api_usage_logs`     | Porterchain | API usage metering         | No                | Yes         | No                            |
| `merchant_audit_logs`         | Porterchain | Merchant audit trail       | Yes               | No          | No                            |
| `merchant_booking_templates`  | Porterchain | Merchant booking presets   | Yes               | No          | No                            |
| `saved_addresses`             | Porterchain | Merchant address book      | Yes               | No          | No                            |
| `merchant_recipients`         | Porterchain | Delivery recipients        | Yes               | No          | No                            |
| `bulk_import_jobs`            | Porterchain | Bulk import tracking       | No                | Yes         | No                            |
| `merchant_contracts`          | Porterchain | Commercial contracts       | Yes               | No          | No                            |
| `crm_companies`               | Porterchain | CRM companies              | Yes               | No          | No                            |
| `crm_contacts`                | Porterchain | CRM contacts               | Yes               | No          | No                            |
| `crm_leads`                   | Porterchain | Sales leads                | Yes               | No          | No                            |
| `crm_deals`                   | Porterchain | Pipeline deals             | Yes               | No          | No                            |
| `crm_quotations`              | Porterchain | Sales quotations           | Yes               | No          | No                            |
| `crm_contracts`               | Porterchain | CRM contracts              | Yes               | No          | No                            |
| `crm_activities`              | Porterchain | CRM activity log           | Yes               | No          | No                            |
| `crm_sales_tasks`             | Porterchain | CRM tasks                  | Yes               | No          | No                            |
| `crm_invoices`                | Porterchain | CRM invoice records        | Yes               | No          | No                            |
| `crm_documents`               | Porterchain | CRM document refs          | Yes               | No          | No                            |
| `crm_tasks`                   | Porterchain | Admin CRM tasks            | Yes               | No          | No                            |
| `crm_notes`                   | Porterchain | Admin CRM notes            | Yes               | No          | No                            |
| `admin_users`                 | Porterchain | Admin staff                | Yes               | No          | No                            |
| `porterchain_users`           | Porterchain | Canonical Clerk identity   | Yes               | No          | No                            |
| `user_invitations`            | Porterchain | Staff invitations          | Yes               | No          | No                            |
| `identity_links`              | Porterchain | Cross-portal identity      | Yes               | No          | No                            |
| `drivers`                     | Porterchain | Driver profile mirror      | Yes               | Yes         | Outbound → Fleetbase          |
| `vehicles`                    | Porterchain | Vehicle mirror             | Yes               | Yes         | Outbound → Fleetbase          |
| `driver_payouts`              | Porterchain | Driver payouts             | Yes               | No          | No                            |
| `driver_wallet_transactions`  | Porterchain | Driver wallet              | Yes               | No          | No                            |
| `driver_bonuses`              | Porterchain | Driver incentives          | Yes               | No          | No                            |
| `driver_location_pings`       | Porterchain | Location cache             | No                | Yes         | Inbound from Fleetbase/mobile |
| `driver_incidents`            | Porterchain | Driver incidents           | Yes               | Yes         | Partial                       |
| `driver_offline_actions`      | Porterchain | Offline sync queue         | No                | Yes         | No                            |
| `driver_stop_meta`            | Porterchain | Stop metadata              | No                | Yes         | Partial                       |
| `driver_shifts`               | Porterchain | Shift records              | Yes               | Yes         | Partial                       |
| `driver_shift_activities`     | Porterchain | Shift activity log         | No                | Yes         | No                            |
| `claims`                      | Porterchain | Insurance / damage claims  | Yes               | Yes         | Partial → Fleetbase           |
| `support_tickets`             | Porterchain | Support cases              | Yes               | No          | No                            |
| `pricing_tariffs`             | Porterchain | Pricing config             | Yes               | No          | No                            |
| `pricing_zones`               | Porterchain | Zone definitions           | Yes               | No          | No                            |
| `promotions`                  | Porterchain | Promotional rules          | Yes               | No          | No                            |
| `route_center_plans`          | Porterchain | Route planning             | Yes               | Yes         | Outbound → Fleetbase dispatch |
| `route_center_templates`      | Porterchain | Route templates            | Yes               | Yes         | Partial                       |
| `notification_records`        | Porterchain | Notification history       | Yes               | No          | No                            |
| `notification_delivery_logs`  | Porterchain | Delivery attempts          | No                | Yes         | No                            |
| `notification_devices`        | Porterchain | FCM device tokens          | Yes               | No          | No                            |
| `notification_preferences`    | Porterchain | User prefs                 | Yes               | No          | No                            |
| `fleetbase_sync_jobs`         | Porterchain | Adapter retry queue        | Yes               | Yes         | Bridge state                  |
| `fleetbase_sync_audit`        | Porterchain | Adapter audit trail        | Yes               | Yes         | Bridge state                  |
| `admin_audit_logs`            | Porterchain | Admin audit                | Yes               | No          | No                            |
| `system_config`               | Porterchain | Platform config KV         | Yes               | No          | No                            |
| `alembic_version`             | Alembic     | Migration version          | Yes               | Yes         | No                            |

**Total Porterchain PostgreSQL tables:** 68 (+ `alembic_version`)

---

## Fleetbase MySQL (read-only from Porterchain — do not modify)

Fleetbase owns ~90 `fleetbase_*` tables. Porterchain **never** connects to this database directly; all access is via Fleetbase Adapter → Fleetbase HTTP API.

| Domain         | Representative tables                                                               | Owner     | Sync required              |
| -------------- | ----------------------------------------------------------------------------------- | --------- | -------------------------- |
| Platform / IAM | `fleetbase_users`, `fleetbase_companies`, `fleetbase_roles`                         | Fleetbase | Admin SSO mapping only     |
| FleetOps       | `fleetbase_orders`, `fleetbase_payloads`, `fleetbase_drivers`, `fleetbase_vehicles` | Fleetbase | **Yes** — order lifecycle  |
| Dispatch       | `fleetbase_service_quotes`, `fleetbase_routes`, `fleetbase_waypoints`               | Fleetbase | **Yes** — route execution  |
| Tracking       | GPS traces, POD records                                                             | Fleetbase | **Yes** — inbound webhooks |
| Developer API  | `fleetbase_api_credentials`, `fleetbase_webhooks`                                   | Fleetbase | No (Fleetbase-internal)    |

See [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) for the Fleetbase boundary and [docs/archive/FLEETBASE_DATABASE.md](./docs/archive/FLEETBASE_DATABASE.md) for the historical schema reference.

---

## Redis structures (not relational tables)

| Key / pattern                | Owner        | Purpose                           | Business critical | Sync required        |
| ---------------------------- | ------------ | --------------------------------- | ----------------- | -------------------- |
| `porterchain:queue:emails`   | Worker       | Email jobs                        | No                | No                   |
| `porterchain:queue:sms`      | Worker       | SMS jobs                          | No                | No                   |
| `porterchain:queue:push`     | Worker       | Push notifications                | No                | No                   |
| `porterchain:queue:dispatch` | Worker       | Dispatch jobs                     | Yes               | Indirect → Fleetbase |
| `porterchain:queue:billing`  | Worker       | Billing jobs                      | Yes               | No                   |
| `porterchain:queue:reports`  | Worker       | Report generation                 | No                | No                   |
| `porterchain:queue:webhooks` | Worker       | Outbound webhooks                 | Yes               | No                   |
| Event bus channels           | API / worker | Pub/sub (implementation-specific) | Yes               | No                   |
| Session / cache keys         | API          | Ephemeral cache                   | No                | No                   |

---

## Classification legend

| Column                | Meaning                                                                    |
| --------------------- | -------------------------------------------------------------------------- |
| **Business critical** | Loss or corruption affects revenue, compliance, or customer-facing truth   |
| **Operational**       | Real-time ops, dispatch, telemetry, or retry queues                        |
| **Sync required**     | Must stay consistent with Fleetbase MySQL via adapter (not direct DB link) |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
