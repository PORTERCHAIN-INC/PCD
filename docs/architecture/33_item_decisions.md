# 33 · Explicit decisions for tables, routers and pages with no plan entry

From file 29: 26 tables, 26 routers and 42 pages had an as-built entry but no planned decision. Default = KEEP unchanged (existing-features-kept rule); exceptions are named. Hosting column follows 28: business-facing on droplet, admin on Ubuntu.

## Tables (26)

| Table                             | Decision                                                      | Week                        |
| --------------------------------- | ------------------------------------------------------------- | --------------------------- |
| `forensic_checkpoints`            | KEEP; audit chain anchor                                      | 6                           |
| `domain_events`                   | REPLACE by `event_outbox` (L19); keep read-only 6 y then drop | 4                           |
| `stripe_webhook_events`           | KEEP (retail Stripe, L10)                                     | 3–4 (SQLModel when touched) |
| `crm_activities`                  | KEEP; Phase 2 CRM merge (A19)                                 | 3–4 (SQLModel when touched) |
| `crm_documents`                   | KEEP; Phase 2 CRM merge (A19)                                 | 3–4 (SQLModel when touched) |
| `admin_audit_logs`                | KEEP; fold into forensic chain view                           | 3–4 (SQLModel when touched) |
| `tax_registrations`               | KEEP; HST check (A07)                                         | 1                           |
| `merchant_merges`                 | KEEP                                                          | 3–4 (SQLModel when touched) |
| `access_audit_logs`               | KEEP; PIPEDA access log                                       | 3–4 (SQLModel when touched) |
| `legacy_external_refs`            | KEEP until FleetBase refs gone, then REMOVE (Phase 2)         | 3–4 (SQLModel when touched) |
| `fk_orphan_quarantine`            | KEEP (data-quality tool); empty before cutover                | 3–4 (SQLModel when touched) |
| `blog_authors`                    | KEEP                                                          | 3–4 (SQLModel when touched) |
| `blog_posts`                      | KEEP                                                          | 3–4 (SQLModel when touched) |
| `invoice_number_sequences`        | KEEP; single issuer (A03)                                     | 2                           |
| `stripe_payouts`                  | KEEP read-only; merchants on Interac (L10)                    | 3–4 (SQLModel when touched) |
| `driver_payout_runs`              | KEEP; DPWRA pay statements (A10)                              | 6                           |
| `dispatch_stop_times`             | KEEP; feeds stop_time_learning                                | 3–4 (SQLModel when touched) |
| `notification_delivery_logs`      | KEEP                                                          | 3–4 (SQLModel when touched) |
| `notification_devices`            | KEEP; push replaces SMS (L26)                                 | 6                           |
| `notification_records`            | KEEP                                                          | 3–4 (SQLModel when touched) |
| `notification_preferences`        | KEEP; CASL consent                                            | 3–4 (SQLModel when touched) |
| `notification_user_settings`      | KEEP; merge with preferences (Phase 2)                        | 3–4 (SQLModel when touched) |
| `notification_email_suppressions` | KEEP                                                          | 3–4 (SQLModel when touched) |
| `notification_template_copy`      | KEEP; add FR copy                                             | 3–4 (SQLModel when touched) |
| `notification_admin_settings`     | KEEP                                                          | 3–4 (SQLModel when touched) |
| `deleted_batches`                 | KEEP; used by deleted_items_purge                             | 3–4 (SQLModel when touched) |

## Routers (26)

| Router                   | Decision                                                            | Host                 | Week |
| ------------------------ | ------------------------------------------------------------------- | -------------------- | ---- |
| `admin_merchant_dedupe`  | KEEP; in regenerated OpenAPI                                        | Ubuntu (admin API)   | 1    |
| `auth_staff_sessions`    | REPLACE → Keycloak sessions                                         | Ubuntu (admin API)   | 5    |
| `collaboration`          | KEEP; in regenerated OpenAPI                                        | Ubuntu (admin API)   | 1    |
| `customers_admin`        | KEEP; in regenerated OpenAPI                                        | Ubuntu (admin API)   | 1    |
| `customers_admin_360`    | KEEP; in regenerated OpenAPI                                        | Ubuntu (admin API)   | 1    |
| `drivers_admin`          | KEEP; in regenerated OpenAPI                                        | Ubuntu (admin API)   | 1    |
| `drivers_admin_account`  | KEEP; in regenerated OpenAPI                                        | Ubuntu (admin API)   | 1    |
| `email_inbound`          | KEEP; feeds lead_inbound_email                                      | Ubuntu (admin API)   | 6    |
| `fsa_rate_card`          | REPLACE → rate card v2 (pricing page)                               | droplet (public API) | 2    |
| `geo`                    | KEEP; self-hosted geocoder (Pelias/Photon) instead of Google Places | droplet (public API) | 4    |
| `lead_webhooks`          | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `merchant_api`           | KEEP; API keys + rate limits                                        | droplet (public API) | 6    |
| `merchant_ops`           | KEEP; in regenerated OpenAPI                                        | Ubuntu (admin API)   | 1    |
| `merchants_integrations` | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `notifications_admin`    | KEEP                                                                | Ubuntu (admin API)   | 1    |
| `notifications_center`   | KEEP                                                                | droplet (public API) | 1    |
| `operations_maps`        | REPLACE map keys → MapLibre/PMTiles                                 | Ubuntu (admin API)   | 4    |
| `pricing_components`     | REPLACE → rate card v2 add-ons                                      | droplet (public API) | 2    |
| `public_blog`            | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `public_guide`           | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `public_guide_support`   | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `public_ingest_auth`     | KEEP; rate-limit (doc 35)                                           | droplet (public API) | 6    |
| `public_inquiries`       | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `public_marketing`       | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `public_newsletter`      | KEEP; in regenerated OpenAPI                                        | droplet (public API) | 1    |
| `zeptomail_webhook`      | KEEP (ZeptoMail allowed L26)                                        | droplet (public API) | 1    |

## Pages (42)

| Page                                            | Decision                                                             | Host    | Week                     |
| ----------------------------------------------- | -------------------------------------------------------------------- | ------- | ------------------------ |
| `admin:/blog/new`                               | KEEP                                                                 | Ubuntu  | 2 (design system reskin) |
| `admin:/finance/tax-registration`               | KEEP; stricter BN RT check (A07)                                     | Ubuntu  | 1                        |
| `admin:/system-health`                          | KEEP one copy; move to super-admin; data from Prometheus (doc 36)    | Ubuntu  | 3                        |
| `admin:/system-tests`                           | REMOVE duplicate `/admin/system-*` route; keep one under super-admin | Ubuntu  | 2                        |
| `admin:/activate-staff`                         | REPLACE → Keycloak invite flow                                       | Ubuntu  | 5                        |
| `admin:/admin/system-health`                    | KEEP one copy; move to super-admin; data from Prometheus (doc 36)    | Ubuntu  | 3                        |
| `admin:/admin/system-tests`                     | REMOVE duplicate `/admin/system-*` route; keep one under super-admin | Ubuntu  | 2                        |
| `admin:/`                                       | KEEP                                                                 | Ubuntu  | 2 (design system reskin) |
| `customer:/`                                    | KEEP                                                                 | droplet | 2 (design system reskin) |
| `customer:/welcome`                             | KEEP                                                                 | droplet | 2 (design system reskin) |
| `driver-portal:/`                               | KEEP                                                                 | droplet | 2 (design system reskin) |
| `merchant-portal:/api`                          | KEEP; API keys + rate-limit display                                  | droplet | 6                        |
| `merchant-portal:/`                             | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/[...rest]`                   | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/[city]/[industrySlug]`       | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/blog/category/[category]`    | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/box-truck-delivery`          | KEEP; read live rate card v2 (pricing page)                          | droplet | 2                        |
| `website:/[locale]/campaigns/[slug]`            | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/campaigns`                   | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/cargo-van-delivery`          | KEEP; read live rate card v2 (pricing page)                          | droplet | 2                        |
| `website:/[locale]/cookies`                     | KEEP; CASL/PIPEDA consent, add FR parity check                       | droplet | 3                        |
| `website:/[locale]/delivery-cost-calculator`    | KEEP; read live rate card v2 (pricing page)                          | droplet | 2                        |
| `website:/[locale]/email-preferences`           | KEEP; CASL/PIPEDA consent, add FR parity check                       | droplet | 3                        |
| `website:/[locale]/enterprise`                  | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/faq`                         | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/onboarding-education/[slug]` | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/page-not-found`              | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]`                             | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/pickup-truck-delivery`       | KEEP; read live rate card v2 (pricing page)                          | droplet | 2                        |
| `website:/[locale]/research`                    | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/sedan-delivery`              | KEEP; read live rate card v2 (pricing page)                          | droplet | 2                        |
| `website:/[locale]/service-areas/[slug]`        | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/service-areas`               | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/trade-van-delivery`          | KEEP; read live rate card v2 (pricing page)                          | droplet | 2                        |
| `website:/[locale]/trust/corrections`           | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/trust/editorial-policy`      | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/trust/founder`               | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/trust`                       | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/trust/research-methodology`  | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/trust/service-standards`     | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/[locale]/vehicle-partner`             | KEEP                                                                 | droplet | 2 (design system reskin) |
| `website:/proof-of-resolution`                  | KEEP                                                                 | droplet | 2 (design system reskin) |
