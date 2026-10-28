# 06 — API specification inventory (AS-BUILT)

**Evidence:** `docs/api/openapi.json` (committed snapshot, commit `2a360bac`, 2026-10-28 09:18 EDT, produced by `apps/api/scripts/export_openapi.py` → `app.openapi()`), joined to handler source by FastAPI operationId (`function name + path + method`) via a static AST scan of `apps/api/src/porterchain_api/**`. 1017 of 1018 operations matched to a file:line. "Auth" lists the guard functions found in the handler signature/body (`get_admin_context`, `require_module(...)`, `require_approved_driver`, ...). "Module" is the SpiceDB permission string passed to `require_module` (admin: `platform` object; merchant: `organization` object — see 09).

Router-level `dependencies=[...]` and `Annotated` aliases are resolved. **The snapshot lags code**: see the last section for handlers in code but not in the snapshot, and operations in the snapshot whose handler no longer exists.

Totals: **1018 operations** on **910 paths**.

| Area                          | Operations |
| ----------------------------- | ---------: |
| admin (staff)                 |        521 |
| merchant portal               |        210 |
| driver                        |        119 |
| other /v1                     |         99 |
| public                        |         27 |
| customer                      |         25 |
| ops                           |          7 |
| merchant public API (API key) |          7 |
| webhooks                      |          3 |

## Full inventory

### admin (staff)

| Method | Path                                                                               | Auth                                               | Module | Handler                                    |
| ------ | ---------------------------------------------------------------------------------- | -------------------------------------------------- | ------ | ------------------------------------------ |
| GET    | `/v1/admin/analytics/ops`                                                          | staff session                                      | —      | `routers/admin/finance_insights.py:106`    |
| GET    | `/v1/admin/attachments/{attachment_id}/file`                                       | staff session                                      | —      | `routers/booking_attachments/driver.py:77` |
| GET    | `/v1/admin/audit-logs`                                                             | staff session                                      | —      | `routers/admin/audit.py:21`                |
| GET    | `/v1/admin/audit-logs/domain-events`                                               | staff session                                      | —      | `routers/admin/audit.py:60`                |
| GET    | `/v1/admin/audit-logs/export`                                                      | staff session, get_report_db                       | —      | `routers/admin/audit.py:35`                |
| GET    | `/v1/admin/audit-logs/export.csv`                                                  | staff session, get_report_db                       | —      | `routers/admin/audit.py:45`                |
| GET    | `/v1/admin/blog/authors`                                                           | staff session                                      | —      | `routers/admin/blog_authors.py:27`         |
| POST   | `/v1/admin/blog/authors`                                                           | staff session                                      | —      | `routers/admin/blog_authors.py:39`         |
| DELETE | `/v1/admin/blog/authors/{author_id}`                                               | staff session                                      | —      | `routers/admin/blog_authors.py:96`         |
| PATCH  | `/v1/admin/blog/authors/{author_id}`                                               | staff session                                      | —      | `routers/admin/blog_authors.py:66`         |
| POST   | `/v1/admin/blog/media`                                                             | staff session                                      | —      | `routers/admin/blog.py:82`                 |
| GET    | `/v1/admin/blog/posts`                                                             | staff session                                      | —      | `routers/admin/blog.py:46`                 |
| POST   | `/v1/admin/blog/posts`                                                             | staff session, get_settings                        | —      | `routers/admin/blog.py:108`                |
| DELETE | `/v1/admin/blog/posts/{post_id}`                                                   | staff session, get_settings                        | —      | `routers/admin/blog.py:238`                |
| GET    | `/v1/admin/blog/posts/{post_id}`                                                   | staff session                                      | —      | `routers/admin/blog.py:66`                 |
| PATCH  | `/v1/admin/blog/posts/{post_id}`                                                   | staff session, get_settings                        | —      | `routers/admin/blog.py:156`                |
| GET    | `/v1/admin/blog/posts/{post_id}/preview-url`                                       | staff session, get_settings                        | —      | `routers/admin/blog.py:210`                |
| GET    | `/v1/admin/booking-drafts`                                                         | staff session                                      | —      | `routers/admin/booking_drafts.py:79`       |
| GET    | `/v1/admin/booking-drafts/abandoned`                                               | staff session                                      | —      | `routers/admin/booking_drafts.py:70`       |
| GET    | `/v1/admin/booking-drafts/analytics`                                               | staff session                                      | —      | `routers/admin/booking_drafts.py:61`       |
| POST   | `/v1/admin/booking-drafts/bulk`                                                    | staff session, get_settings                        | —      | `routers/admin/booking_drafts.py:255`      |
| GET    | `/v1/admin/booking-drafts/{draft_id}`                                              | staff session, get_settings                        | —      | `routers/admin/booking_drafts.py:124`      |
| POST   | `/v1/admin/booking-drafts/{draft_id}/cancel`                                       | get_optional_clerk_user_id, get_settings           | —      | `routers/booking_drafts.py:139`            |
| POST   | `/v1/admin/booking-drafts/{draft_id}/duplicate`                                    | staff session, get_settings                        | —      | `routers/admin/booking_drafts.py:212`      |
| POST   | `/v1/admin/booking-drafts/{draft_id}/expire`                                       | staff session, get_settings                        | —      | `routers/admin/booking_drafts.py:195`      |
| POST   | `/v1/admin/booking-drafts/{draft_id}/extend`                                       | staff session, get_settings                        | —      | `routers/admin/booking_drafts.py:135`      |
| POST   | `/v1/admin/booking-drafts/{draft_id}/restore`                                      | staff session, get_settings                        | —      | `routers/admin/booking_drafts.py:180`      |
| POST   | `/v1/admin/booking-drafts/{draft_id}/send-payment-link`                            | staff session, get_settings                        | —      | `routers/admin/booking_drafts.py:235`      |
| GET    | `/v1/admin/claims`                                                                 | staff session                                      | —      | `routers/admin/claims.py:72`               |
| POST   | `/v1/admin/claims`                                                                 | staff session                                      | —      | `routers/admin/claims.py:126`              |
| POST   | `/v1/admin/claims/bulk`                                                            | staff session                                      | —      | `routers/admin/claims.py:278`              |
| GET    | `/v1/admin/claims/dashboard`                                                       | staff session                                      | —      | `routers/admin/claims.py:36`               |
| GET    | `/v1/admin/claims/export.csv`                                                      | staff session, get_report_db                       | —      | `routers/admin/claims.py:54`               |
| GET    | `/v1/admin/claims/reports`                                                         | staff session, get_report_db                       | —      | `routers/admin/claims.py:45`               |
| GET    | `/v1/admin/claims/{claim_id}`                                                      | staff session                                      | —      | `routers/admin/claims.py:113`              |
| POST   | `/v1/admin/claims/{claim_id}/assign`                                               | staff session                                      | —      | `routers/admin/claims.py:163`              |
| POST   | `/v1/admin/claims/{claim_id}/auto-assign`                                          | staff session                                      | —      | `routers/admin/claims.py:179`              |
| POST   | `/v1/admin/claims/{claim_id}/compensation`                                         | staff session                                      | —      | `routers/admin/claims.py:244`              |
| POST   | `/v1/admin/claims/{claim_id}/evidence`                                             | staff session                                      | —      | `routers/admin/claims.py:194`              |
| POST   | `/v1/admin/claims/{claim_id}/insurance`                                            | staff session                                      | —      | `routers/admin/claims.py:262`              |
| POST   | `/v1/admin/claims/{claim_id}/investigation`                                        | staff session                                      | —      | `routers/admin/claims.py:228`              |
| POST   | `/v1/admin/claims/{claim_id}/notes`                                                | staff session                                      | —      | `routers/admin/claims.py:212`              |
| POST   | `/v1/admin/claims/{claim_id}/status`                                               | staff session                                      | —      | `routers/admin/claims.py:145`              |
| GET    | `/v1/admin/collaboration/activities`                                               | staff session                                      | —      | `routers/collaboration.py:39`              |
| POST   | `/v1/admin/collaboration/activities`                                               | staff session                                      | —      | `routers/collaboration.py:52`              |
| GET    | `/v1/admin/collaboration/tasks`                                                    | staff session                                      | —      | `routers/collaboration.py:69`              |
| POST   | `/v1/admin/collaboration/tasks`                                                    | staff session                                      | —      | `routers/collaboration.py:82`              |
| DELETE | `/v1/admin/collaboration/tasks/{task_id}`                                          | staff session                                      | —      | `routers/collaboration.py:99`              |
| PATCH  | `/v1/admin/collaboration/tasks/{task_id}`                                          | staff session                                      | —      | `routers/collaboration.py:89`              |
| GET    | `/v1/admin/compliance`                                                             | staff session                                      | —      | `routers/admin/compliance.py:19`           |
| GET    | `/v1/admin/compliance/audit-chain/verify`                                          | staff session                                      | —      | `routers/admin/compliance.py:83`           |
| GET    | `/v1/admin/compliance/breaches/{breach_id}/evidence`                               | staff session                                      | —      | `routers/admin/compliance.py:66`           |
| GET    | `/v1/admin/customer-care/nudges`                                                   | staff session                                      | —      | `routers/customers_admin_360.py:139`       |
| POST   | `/v1/admin/customer-care/nudges/decide`                                            | staff session, get_settings                        | —      | `routers/customers_admin_360.py:151`       |
| POST   | `/v1/admin/customer-care/nudges/draft`                                             | staff session                                      | —      | `routers/customers_admin_360.py:145`       |
| GET    | `/v1/admin/customer-care/privacy-jobs`                                             | staff session                                      | —      | `routers/customers_admin_360.py:115`       |
| POST   | `/v1/admin/customer-care/privacy-jobs/{job_id}/approve`                            | staff session                                      | —      | `routers/customers_admin_360.py:127`       |
| POST   | `/v1/admin/customer-care/privacy-jobs/{job_id}/reject`                             | staff session                                      | —      | `routers/customers_admin_360.py:133`       |
| GET    | `/v1/admin/customers`                                                              | staff session                                      | —      | `routers/customers_admin.py:45`            |
| POST   | `/v1/admin/customers`                                                              | staff session, get_settings                        | —      | `routers/customers_admin.py:64`            |
| GET    | `/v1/admin/customers/stats`                                                        | staff session                                      | —      | `routers/customers_admin.py:39`            |
| GET    | `/v1/admin/customers/{customer_id}`                                                | staff session                                      | —      | `routers/customers_admin.py:103`           |
| GET    | `/v1/admin/customers/{customer_id}/360`                                            | staff session, get_settings                        | —      | `routers/customers_admin_360.py:74`        |
| POST   | `/v1/admin/customers/{customer_id}/booking-drafts`                                 | staff session, get_settings                        | —      | `routers/customers_admin.py:200`           |
| POST   | `/v1/admin/customers/{customer_id}/booking-drafts/{draft_id}/send-payment-link`    | staff session, get_settings                        | —      | `routers/customers_admin.py:238`           |
| POST   | `/v1/admin/customers/{customer_id}/booking-link-draft`                             | staff session, get_settings                        | —      | `routers/customers_admin_360.py:107`       |
| GET    | `/v1/admin/customers/{customer_id}/care`                                           | staff session                                      | —      | `routers/customers_admin.py:183`           |
| POST   | `/v1/admin/customers/{customer_id}/credit`                                         | staff session                                      | —      | `routers/customers_admin_360.py:92`        |
| POST   | `/v1/admin/customers/{customer_id}/invite`                                         | staff session, get_settings                        | —      | `routers/customers_admin.py:112`           |
| GET    | `/v1/admin/customers/{customer_id}/invoices`                                       | staff session                                      | —      | `routers/customers_admin.py:155`           |
| POST   | `/v1/admin/customers/{customer_id}/notes`                                          | staff session                                      | —      | `routers/customers_admin_360.py:86`        |
| GET    | `/v1/admin/customers/{customer_id}/orders`                                         | staff session                                      | —      | `routers/customers_admin.py:140`           |
| GET    | `/v1/admin/customers/{customer_id}/payments`                                       | staff session                                      | —      | `routers/customers_admin.py:169`           |
| POST   | `/v1/admin/customers/{customer_id}/refund`                                         | staff session, get_settings                        | —      | `routers/customers_admin_360.py:99`        |
| GET    | `/v1/admin/customers/{customer_id}/timeline`                                       | staff session                                      | —      | `routers/customers_admin_360.py:80`        |
| GET    | `/v1/admin/dashboard`                                                              | staff session                                      | —      | `routers/admin/dashboard.py:21`            |
| GET    | `/v1/admin/dashboard/center`                                                       | staff session, get_settings                        | —      | `routers/admin/dashboard.py:30`            |
| GET    | `/v1/admin/dashboard/search`                                                       | staff session                                      | —      | `routers/admin/dashboard.py:40`            |
| GET    | `/v1/admin/data-moat/merchants/{merchant_id}`                                      | staff session                                      | —      | `routers/admin/data_moat.py:30`            |
| GET    | `/v1/admin/data-moat/network`                                                      | staff session                                      | —      | `routers/admin/data_moat.py:20`            |
| GET    | `/v1/admin/data-moat/orders/{order_id}/own-ping-eta`                               | staff session, get_settings                        | —      | `routers/admin/data_moat.py:41`            |
| GET    | `/v1/admin/deleted-items`                                                          | staff session                                      | —      | `routers/admin/deleted_items.py:59`        |
| POST   | `/v1/admin/deleted-items/auto-purge/run`                                           | staff session                                      | —      | `routers/admin/deleted_items.py:121`       |
| GET    | `/v1/admin/deleted-items/check/{entity}/{row_id}`                                  | staff session                                      | —      | `routers/admin/deleted_items.py:68`        |
| GET    | `/v1/admin/deleted-items/meta`                                                     | staff session                                      | —      | `routers/admin/deleted_items.py:42`        |
| PUT    | `/v1/admin/deleted-items/settings`                                                 | staff session                                      | —      | `routers/admin/deleted_items.py:48`        |
| POST   | `/v1/admin/deleted-items/{batch_id}/purge`                                         | staff session                                      | —      | `routers/admin/deleted_items.py:103`       |
| POST   | `/v1/admin/deleted-items/{batch_id}/restore`                                       | staff session                                      | —      | `routers/admin/deleted_items.py:91`        |
| POST   | `/v1/admin/deleted-items/{entity}/{row_id}/delete`                                 | staff session                                      | —      | `routers/admin/deleted_items.py:79`        |
| GET    | `/v1/admin/diagnostics/ai-usage`                                                   | staff session                                      | —      | `routers/diagnostics.py:151`               |
| GET    | `/v1/admin/diagnostics/architecture`                                               | staff session, get_settings                        | —      | `routers/diagnostics.py:85`                |
| GET    | `/v1/admin/diagnostics/center`                                                     | staff session, get_settings                        | —      | `routers/diagnostics.py:36`                |
| POST   | `/v1/admin/diagnostics/chaos/{scenario}`                                           | staff session, get_settings                        | —      | `routers/diagnostics.py:170`               |
| GET    | `/v1/admin/diagnostics/day-plan`                                                   | staff session                                      | —      | `routers/diagnostics.py:138`               |
| GET    | `/v1/admin/diagnostics/events`                                                     | staff session                                      | —      | `routers/diagnostics.py:127`               |
| GET    | `/v1/admin/diagnostics/execution-metrics`                                          | staff session                                      | —      | `routers/diagnostics.py:164`               |
| GET    | `/v1/admin/diagnostics/health`                                                     | staff session, get_settings                        | —      | `routers/diagnostics.py:46`                |
| GET    | `/v1/admin/diagnostics/merchant-webhook-delivery`                                  | staff session                                      | —      | `routers/diagnostics.py:145`               |
| GET    | `/v1/admin/diagnostics/modules`                                                    | staff session, get_settings                        | —      | `routers/diagnostics.py:94`                |
| GET    | `/v1/admin/diagnostics/observability`                                              | staff session, get_settings                        | —      | `routers/diagnostics.py:181`               |
| POST   | `/v1/admin/diagnostics/reports/generate`                                           | staff session, get_report_db, get_settings         | —      | `routers/diagnostics.py:191`               |
| GET    | `/v1/admin/diagnostics/tests`                                                      | staff session                                      | —      | `routers/diagnostics.py:56`                |
| POST   | `/v1/admin/diagnostics/tests/run`                                                  | staff session, get_settings                        | —      | `routers/diagnostics.py:62`                |
| POST   | `/v1/admin/diagnostics/tests/{test_id}`                                            | staff session, get_settings                        | —      | `routers/diagnostics.py:72`                |
| GET    | `/v1/admin/diagnostics/workflows`                                                  | staff session, get_settings                        | —      | `routers/diagnostics.py:104`               |
| POST   | `/v1/admin/diagnostics/workflows/{scenario_id}/simulate`                           | staff session, get_settings                        | —      | `routers/diagnostics.py:114`               |
| POST   | `/v1/admin/dispatch/orders/{order_id}/assign`                                      | staff session, get_settings                        | —      | `routers/operations.py:395`                |
| GET    | `/v1/admin/drivers`                                                                | staff session                                      | —      | `routers/drivers_admin.py:92`              |
| POST   | `/v1/admin/drivers`                                                                | staff session, get_settings                        | —      | `routers/drivers_admin.py:117`             |
| GET    | `/v1/admin/drivers/facets`                                                         | staff session                                      | —      | `routers/drivers_admin.py:107`             |
| GET    | `/v1/admin/drivers/stats`                                                          | staff session                                      | —      | `routers/drivers_admin.py:112`             |
| GET    | `/v1/admin/drivers/{driver_id}`                                                    | staff session                                      | —      | `routers/drivers_admin.py:129`             |
| PATCH  | `/v1/admin/drivers/{driver_id}`                                                    | staff session                                      | —      | `routers/drivers_admin_account.py:23`      |
| POST   | `/v1/admin/drivers/{driver_id}/action`                                             | staff session                                      | —      | `routers/drivers_admin.py:201`             |
| GET    | `/v1/admin/drivers/{driver_id}/activities`                                         | staff session                                      | —      | `routers/drivers_admin.py:306`             |
| GET    | `/v1/admin/drivers/{driver_id}/analytics`                                          | staff session                                      | —      | `routers/drivers_admin.py:296`             |
| POST   | `/v1/admin/drivers/{driver_id}/approve`                                            | staff session, get_settings                        | —      | `routers/drivers_admin.py:148`             |
| POST   | `/v1/admin/drivers/{driver_id}/deactivate`                                         | staff session, get_settings                        | —      | `routers/drivers_admin.py:165`             |
| GET    | `/v1/admin/drivers/{driver_id}/documents`                                          | staff session                                      | —      | `routers/drivers_admin.py:274`             |
| POST   | `/v1/admin/drivers/{driver_id}/documents`                                          | staff session                                      | —      | `routers/drivers_admin.py:279`             |
| POST   | `/v1/admin/drivers/{driver_id}/documents/decision`                                 | staff session                                      | —      | `routers/drivers_admin_account.py:33`      |
| GET    | `/v1/admin/drivers/{driver_id}/incidents`                                          | staff session                                      | —      | `routers/drivers_admin.py:291`             |
| POST   | `/v1/admin/drivers/{driver_id}/invite`                                             | staff session, get_settings                        | —      | `routers/drivers_admin.py:134`             |
| GET    | `/v1/admin/drivers/{driver_id}/orders`                                             | staff session                                      | —      | `routers/drivers_admin.py:219`             |
| GET    | `/v1/admin/drivers/{driver_id}/payouts`                                            | staff session                                      | —      | `routers/drivers_admin.py:236`             |
| POST   | `/v1/admin/drivers/{driver_id}/payouts`                                            | staff session                                      | —      | `routers/drivers_admin.py:241`             |
| POST   | `/v1/admin/drivers/{driver_id}/payouts/{payout_id}/mark-paid`                      | staff session                                      | —      | `routers/drivers_admin.py:262`             |
| POST   | `/v1/admin/drivers/{driver_id}/rehire`                                             | staff session                                      | —      | `routers/drivers_admin.py:191`             |
| POST   | `/v1/admin/drivers/{driver_id}/reject`                                             | staff session, get_settings                        | —      | `routers/drivers_admin.py:173`             |
| POST   | `/v1/admin/drivers/{driver_id}/suspend`                                            | staff session, get_settings                        | —      | `routers/drivers_admin.py:158`             |
| GET    | `/v1/admin/drivers/{driver_id}/tasks`                                              | staff session                                      | —      | `routers/drivers_admin.py:312`             |
| GET    | `/v1/admin/drivers/{driver_id}/timeline`                                           | staff session                                      | —      | `routers/drivers_admin.py:301`             |
| GET    | `/v1/admin/drivers/{driver_id}/vehicles`                                           | staff session                                      | —      | `routers/drivers_admin.py:231`             |
| POST   | `/v1/admin/drivers/{driver_id}/vehicles`                                           | staff session, get_settings                        | —      | `routers/drivers_admin_account.py:48`      |
| PATCH  | `/v1/admin/drivers/{driver_id}/vehicles/{vehicle_id}`                              | staff session, get_settings                        | —      | `routers/drivers_admin_account.py:87`      |
| POST   | `/v1/admin/drivers/{driver_id}/vehicles/{vehicle_id}/deactivate`                   | staff session, get_settings                        | —      | `routers/drivers_admin_account.py:73`      |
| PATCH  | `/v1/admin/drivers/{driver_id}/verification`                                       | staff session                                      | —      | `routers/drivers_admin.py:196`             |
| GET    | `/v1/admin/finance/ar-summary`                                                     | staff session                                      | —      | `routers/admin/finance_interac.py:113`     |
| GET    | `/v1/admin/finance/cash`                                                           | staff session                                      | —      | `routers/admin/finance_cash.py:44`         |
| GET    | `/v1/admin/finance/collections`                                                    | staff session                                      | —      | `routers/admin/finance.py:63`              |
| POST   | `/v1/admin/finance/credit-notes`                                                   | NONE                                               | —      | `?:0`                                      |
| GET    | `/v1/admin/finance/dashboard`                                                      | staff session                                      | —      | `routers/admin/finance.py:45`              |
| GET    | `/v1/admin/finance/duplicates`                                                     | staff session                                      | —      | `routers/admin/finance.py:182`             |
| GET    | `/v1/admin/finance/export`                                                         | staff session, get_report_db                       | —      | `routers/admin/finance.py:73`              |
| GET    | `/v1/admin/finance/exports/{kind}.csv`                                             | staff session, get_report_db                       | —      | `routers/admin/finance_insights.py:161`    |
| GET    | `/v1/admin/finance/interac`                                                        | staff session, get_settings                        | —      | `routers/admin/finance_interac.py:34`      |
| POST   | `/v1/admin/finance/interac/sync`                                                   | staff session, get_settings                        | —      | `routers/admin/finance_interac.py:97`      |
| POST   | `/v1/admin/finance/interac/{transfer_id}/approve`                                  | staff session, get_settings                        | —      | `routers/admin/finance_interac.py:53`      |
| POST   | `/v1/admin/finance/interac/{transfer_id}/reject`                                   | staff session, get_settings                        | —      | `routers/admin/finance_interac.py:75`      |
| GET    | `/v1/admin/finance/invoices`                                                       | staff session                                      | —      | `routers/admin/finance.py:82`              |
| GET    | `/v1/admin/finance/invoices/{invoice_id}`                                          | staff session                                      | —      | `routers/admin/finance.py:123`             |
| GET    | `/v1/admin/finance/invoices/{invoice_id}/pdf`                                      | staff session                                      | —      | `routers/admin/finance_invoice_pdf.py:20`  |
| POST   | `/v1/admin/finance/invoices/{invoice_id}/record-payment`                           | staff session, get_settings                        | —      | `routers/admin/finance.py:246`             |
| POST   | `/v1/admin/finance/invoices/{invoice_id}/refund`                                   | staff session, get_settings                        | —      | `routers/admin/finance.py:287`             |
| POST   | `/v1/admin/finance/invoices/{invoice_id}/remind`                                   | staff session, get_settings                        | —      | `routers/admin/finance.py:268`             |
| GET    | `/v1/admin/finance/ledger`                                                         | staff session                                      | —      | `routers/admin/finance.py:173`             |
| GET    | `/v1/admin/finance/margin`                                                         | staff session                                      | —      | `routers/admin/finance_insights.py:53`     |
| POST   | `/v1/admin/finance/merchant-ar/generate`                                           | staff session, get_settings                        | —      | `routers/admin/finance.py:218`             |
| GET    | `/v1/admin/finance/merchant-ar/preview`                                            | staff session                                      | —      | `routers/admin/finance.py:191`             |
| GET    | `/v1/admin/finance/payments`                                                       | staff session                                      | —      | `routers/admin/finance.py:136`             |
| GET    | `/v1/admin/finance/payout-runs`                                                    | staff session                                      | —      | `routers/admin/finance_cash.py:108`        |
| POST   | `/v1/admin/finance/payout-runs`                                                    | staff session                                      | —      | `routers/admin/finance_cash.py:119`        |
| GET    | `/v1/admin/finance/payout-runs/{run_id}/bank.csv`                                  | staff session                                      | —      | `routers/admin/finance_cash.py:152`        |
| POST   | `/v1/admin/finance/payout-runs/{run_id}/{action}`                                  | staff session, get_settings                        | —      | `routers/admin/finance_cash.py:131`        |
| GET    | `/v1/admin/finance/payouts`                                                        | staff session                                      | —      | `routers/admin/finance.py:163`             |
| GET    | `/v1/admin/finance/reminders`                                                      | staff session                                      | —      | `routers/admin/finance_cash.py:56`         |
| POST   | `/v1/admin/finance/reminders/approve`                                              | staff session, get_settings                        | —      | `routers/admin/finance_cash.py:80`         |
| POST   | `/v1/admin/finance/reminders/discard`                                              | staff session                                      | —      | `routers/admin/finance_cash.py:96`         |
| POST   | `/v1/admin/finance/reminders/queue`                                                | staff session                                      | —      | `routers/admin/finance_cash.py:68`         |
| GET    | `/v1/admin/finance/reports`                                                        | staff session, get_report_db                       | —      | `routers/admin/finance.py:54`              |
| GET    | `/v1/admin/finance/stripe`                                                         | staff session                                      | —      | `routers/admin/finance_insights.py:41`     |
| GET    | `/v1/admin/finance/summary`                                                        | staff session                                      | —      | `routers/admin/finance.py:307`             |
| GET    | `/v1/admin/finance/tax-registration`                                               | staff session                                      | —      | `routers/admin/finance_insights.py:66`     |
| GET    | `/v1/admin/finance/tax-report`                                                     | staff session, get_report_db                       | —      | `routers/admin/finance_insights.py:147`    |
| POST   | `/v1/admin/impersonation/start`                                                    | staff session, get_settings                        | —      | `routers/admin/impersonation.py:26`        |
| POST   | `/v1/admin/impersonation/stop`                                                     | staff session, get_settings                        | —      | `routers/admin/impersonation.py:54`        |
| GET    | `/v1/admin/impersonation/{session_id}`                                             | staff session                                      | —      | `routers/admin/impersonation.py:74`        |
| GET    | `/v1/admin/investor-metrics`                                                       | staff session                                      | —      | `routers/admin/investor_metrics.py:17`     |
| GET    | `/v1/admin/leads`                                                                  | staff session                                      | —      | `routers/admin/leads.py:50`                |
| POST   | `/v1/admin/leads`                                                                  | staff session                                      | —      | `routers/admin/leads.py:141`               |
| GET    | `/v1/admin/leads/agent`                                                            | staff session                                      | —      | `routers/admin/leads_outbound.py:39`       |
| POST   | `/v1/admin/leads/bulk`                                                             | staff session                                      | —      | `routers/admin/leads_inbox.py:140`         |
| GET    | `/v1/admin/leads/calendar`                                                         | staff session                                      | —      | `routers/admin/leads_360.py:50`            |
| GET    | `/v1/admin/leads/export.csv`                                                       | staff session, get_report_db                       | —      | `routers/admin/leads_inbox.py:88`          |
| GET    | `/v1/admin/leads/metrics`                                                          | staff session                                      | —      | `routers/admin/leads.py:116`               |
| GET    | `/v1/admin/leads/pipeline`                                                         | staff session                                      | —      | `routers/admin/leads.py:129`               |
| GET    | `/v1/admin/leads/privacy/ropa`                                                     | staff session                                      | —      | `routers/admin/leads.py:284`               |
| POST   | `/v1/admin/leads/referral`                                                         | staff session                                      | —      | `routers/admin/leads.py:205`               |
| GET    | `/v1/admin/leads/referral-credits`                                                 | staff session                                      | —      | `routers/admin/leads.py:231`               |
| GET    | `/v1/admin/leads/reply-channels`                                                   | staff session, get_settings                        | —      | `routers/admin/leads_inbox.py:78`          |
| POST   | `/v1/admin/leads/rescore`                                                          | staff session                                      | —      | `routers/admin/leads_desk.py:133`          |
| GET    | `/v1/admin/leads/speed`                                                            | staff session                                      | —      | `routers/admin/leads_desk.py:48`           |
| GET    | `/v1/admin/leads/suppressions`                                                     | staff session                                      | —      | `routers/admin/leads.py:247`               |
| DELETE | `/v1/admin/leads/suppressions/{suppression_id}`                                    | staff session                                      | —      | `routers/admin/leads.py:295`               |
| GET    | `/v1/admin/leads/today`                                                            | staff session                                      | —      | `routers/admin/leads_outbound.py:27`       |
| GET    | `/v1/admin/leads/weekly-summary`                                                   | staff session                                      | —      | `routers/admin/leads_desk.py:58`           |
| DELETE | `/v1/admin/leads/{lead_id}`                                                        | staff session                                      | —      | `routers/admin/leads.py:570`               |
| GET    | `/v1/admin/leads/{lead_id}`                                                        | staff session                                      | —      | `routers/admin/leads_360.py:71`            |
| PATCH  | `/v1/admin/leads/{lead_id}`                                                        | staff session                                      | —      | `routers/admin/leads.py:463`               |
| GET    | `/v1/admin/leads/{lead_id}/360`                                                    | staff session                                      | —      | `routers/admin/leads_360.py:84`            |
| GET    | `/v1/admin/leads/{lead_id}/assist`                                                 | staff session, get_settings                        | —      | `routers/admin/leads_360.py:26`            |
| POST   | `/v1/admin/leads/{lead_id}/assist/decide`                                          | staff session                                      | —      | `routers/admin/leads.py:322`               |
| POST   | `/v1/admin/leads/{lead_id}/call-disposition`                                       | staff session                                      | —      | `routers/admin/leads_outbound.py:65`       |
| GET    | `/v1/admin/leads/{lead_id}/conversations`                                          | staff session                                      | —      | `routers/admin/leads.py:378`               |
| POST   | `/v1/admin/leads/{lead_id}/conversations/{conversation_id}/messages`               | staff session                                      | —      | `routers/admin/leads.py:423`               |
| POST   | `/v1/admin/leads/{lead_id}/convert`                                                | staff session, get_settings                        | —      | `routers/admin/leads.py:484`               |
| GET    | `/v1/admin/leads/{lead_id}/dial-scripts`                                           | staff session                                      | —      | `routers/admin/leads_outbound.py:115`      |
| GET    | `/v1/admin/leads/{lead_id}/draft`                                                  | staff session, get_settings                        | —      | `routers/admin/leads_desk.py:106`          |
| GET    | `/v1/admin/leads/{lead_id}/identities`                                             | staff session                                      | —      | `routers/admin/leads.py:356`               |
| POST   | `/v1/admin/leads/{lead_id}/log-call`                                               | staff session                                      | —      | `routers/admin/leads_inbox.py:209`         |
| POST   | `/v1/admin/leads/{lead_id}/lost`                                                   | staff session                                      | —      | `routers/admin/leads_desk.py:144`          |
| POST   | `/v1/admin/leads/{lead_id}/merge`                                                  | staff session                                      | —      | `routers/admin/leads_360.py:127`           |
| GET    | `/v1/admin/leads/{lead_id}/nba`                                                    | staff session                                      | —      | `routers/admin/leads_outbound.py:199`      |
| POST   | `/v1/admin/leads/{lead_id}/privacy/delete-request`                                 | staff session                                      | —      | `routers/admin/leads.py:525`               |
| POST   | `/v1/admin/leads/{lead_id}/privacy/erase`                                          | staff session                                      | —      | `routers/admin/leads.py:546`               |
| GET    | `/v1/admin/leads/{lead_id}/privacy/export`                                         | staff session, get_report_db                       | —      | `routers/admin/leads.py:509`               |
| GET    | `/v1/admin/leads/{lead_id}/quote`                                                  | staff session, get_settings                        | —      | `routers/admin/leads_desk.py:67`           |
| POST   | `/v1/admin/leads/{lead_id}/reply`                                                  | staff session, get_settings                        | —      | `routers/admin/leads_inbox.py:173`         |
| GET    | `/v1/admin/leads/{lead_id}/reply-channels`                                         | staff session, get_settings                        | —      | `routers/admin/leads_inbox.py:161`         |
| GET    | `/v1/admin/leads/{lead_id}/score`                                                  | staff session                                      | —      | `routers/admin/leads_desk.py:86`           |
| POST   | `/v1/admin/leads/{lead_id}/send-email`                                             | staff session, get_settings                        | —      | `routers/admin/leads_outbound.py:139`      |
| GET    | `/v1/admin/leads/{lead_id}/visitor-intelligence`                                   | staff session                                      | —      | `routers/admin/visitor_intelligence.py:46` |
| POST   | `/v1/admin/leads/{lead_id}/welcome`                                                | staff session, get_settings                        | —      | `routers/admin/leads_outbound.py:175`      |
| GET    | `/v1/admin/marketing/lead-attribution`                                             | staff session                                      | —      | `routers/admin/marketing_leads.py:20`      |
| GET    | `/v1/admin/merchant-duplicates`                                                    | staff session                                      | —      | `routers/admin_merchant_dedupe.py:20`      |
| POST   | `/v1/admin/merchant-duplicates/merge`                                              | staff session                                      | —      | `routers/admin_merchant_dedupe.py:35`      |
| POST   | `/v1/admin/merchant-duplicates/merges/{merge_id}/undo`                             | staff session                                      | —      | `routers/admin_merchant_dedupe.py:40`      |
| GET    | `/v1/admin/merchant-duplicates/preview`                                            | staff session                                      | —      | `routers/admin_merchant_dedupe.py:25`      |
| POST   | `/v1/admin/merchant-duplicates/{merchant_id}/keep-separate`                        | staff session                                      | —      | `routers/admin_merchant_dedupe.py:30`      |
| GET    | `/v1/admin/merchant-ops/board`                                                     | staff session                                      | —      | `routers/merchant_ops.py:103`              |
| POST   | `/v1/admin/merchant-ops/bulk`                                                      | staff session                                      | —      | `routers/merchant_ops.py:127`              |
| GET    | `/v1/admin/merchant-ops/owners`                                                    | staff session                                      | —      | `routers/merchant_ops.py:120`              |
| GET    | `/v1/admin/merchant-ops/{merchant_id}`                                             | staff session, get_settings                        | —      | `routers/merchant_ops.py:140`              |
| POST   | `/v1/admin/merchant-ops/{merchant_id}/api-keys/{key_id}/rotate`                    | staff session, require_integrations_elevated       | —      | `routers/merchant_ops.py:193`              |
| GET    | `/v1/admin/merchant-ops/{merchant_id}/change-history`                              | staff session, merchant (Clerk)                    | —      | `routers/merchant_ops.py:149`              |
| GET    | `/v1/admin/merchant-ops/{merchant_id}/connections`                                 | staff session, get_settings, merchant (Clerk)      | —      | `routers/merchant_ops.py:182`              |
| POST   | `/v1/admin/merchant-ops/{merchant_id}/credit`                                      | staff session, merchant (Clerk)                    | —      | `routers/merchant_ops.py:160`              |
| GET    | `/v1/admin/merchant-ops/{merchant_id}/documents`                                   | staff session, merchant (Clerk)                    | —      | `routers/merchant_ops.py:239`              |
| POST   | `/v1/admin/merchant-ops/{merchant_id}/documents`                                   | staff session                                      | —      | `routers/merchant_ops.py:249`              |
| DELETE | `/v1/admin/merchant-ops/{merchant_id}/documents/{doc_id}`                          | staff session                                      | —      | `routers/merchant_ops.py:285`              |
| GET    | `/v1/admin/merchant-ops/{merchant_id}/documents/{doc_id}/download`                 | staff session                                      | —      | `routers/merchant_ops.py:265`              |
| PUT    | `/v1/admin/merchant-ops/{merchant_id}/owner`                                       | staff session                                      | —      | `routers/merchant_ops.py:172`              |
| POST   | `/v1/admin/merchant-ops/{merchant_id}/quote-preview`                               | staff session                                      | —      | `routers/merchant_ops.py:232`              |
| PUT    | `/v1/admin/merchant-ops/{merchant_id}/segment`                                     | staff session                                      | —      | `routers/merchant_ops.py:177`              |
| POST   | `/v1/admin/merchant-ops/{merchant_id}/shopify/{shop_id}/backfill`                  | staff session, get_settings                        | —      | `routers/merchant_ops.py:221`              |
| GET    | `/v1/admin/merchant-ops/{merchant_id}/support`                                     | staff session, merchant (Clerk)                    | —      | `routers/merchant_ops.py:297`              |
| POST   | `/v1/admin/merchant-ops/{merchant_id}/webhooks/replay-failed`                      | staff session, get_settings                        | —      | `routers/merchant_ops.py:205`              |
| GET    | `/v1/admin/merchants`                                                              | staff session                                      | —      | `routers/merchants.py:108`                 |
| POST   | `/v1/admin/merchants`                                                              | staff session, get_settings                        | —      | `routers/merchants.py:140`                 |
| GET    | `/v1/admin/merchants/facets`                                                       | staff session                                      | —      | `routers/merchants.py:123`                 |
| GET    | `/v1/admin/merchants/stats`                                                        | staff session                                      | —      | `routers/merchants.py:128`                 |
| GET    | `/v1/admin/merchants/unprovisioned-signups`                                        | staff session, get_settings                        | —      | `routers/merchants.py:133`                 |
| GET    | `/v1/admin/merchants/{merchant_id}`                                                | staff session, require_detail                      | —      | `routers/merchants.py:160`                 |
| PATCH  | `/v1/admin/merchants/{merchant_id}`                                                | staff session                                      | —      | `routers/merchants.py:225`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/activate-users`                                 | staff session                                      | —      | `routers/merchants.py:521`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/activities`                                     | staff session                                      | —      | `routers/merchants.py:647`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/addresses`                                      | staff session                                      | —      | `routers/merchants.py:374`                 |
| DELETE | `/v1/admin/merchants/{merchant_id}/addresses/{address_id}`                         | staff session                                      | —      | `routers/merchants.py:399`                 |
| PATCH  | `/v1/admin/merchants/{merchant_id}/addresses/{address_id}`                         | staff session                                      | —      | `routers/merchants.py:381`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/addresses/{address_id}/default`                 | staff session                                      | —      | `routers/merchants.py:392`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/analytics`                                      | staff session                                      | —      | `routers/merchants.py:556`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/api`                                            | staff session                                      | —      | `routers/merchants.py:541`                 |
| DELETE | `/v1/admin/merchants/{merchant_id}/api-keys/{key_id}`                              | staff session                                      | —      | `routers/merchants_integrations.py:100`    |
| PATCH  | `/v1/admin/merchants/{merchant_id}/api-keys/{key_id}/rate-limit`                   | staff session                                      | —      | `routers/merchants.py:344`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/approve`                                        | staff session                                      | —      | `routers/merchants.py:165`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/ar/generate`                                    | staff session                                      | —      | `routers/merchants.py:551`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/ar/preview`                                     | staff session                                      | —      | `routers/merchants.py:546`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/billing-contacts`                               | staff session                                      | —      | `routers/merchants.py:431`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/billing-contacts`                               | staff session                                      | —      | `routers/merchants.py:436`                 |
| DELETE | `/v1/admin/merchants/{merchant_id}/billing-contacts/{contact_id}`                  | staff session                                      | —      | `routers/merchants.py:457`                 |
| PATCH  | `/v1/admin/merchants/{merchant_id}/billing-contacts/{contact_id}`                  | staff session                                      | —      | `routers/merchants.py:443`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/close`                                          | staff session                                      | —      | `routers/merchants.py:185`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/complete-onboarding`                            | staff session, get_settings                        | —      | `routers/merchants.py:528`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/contacts`                                       | staff session                                      | —      | `routers/merchants.py:566`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/contacts`                                       | staff session                                      | —      | `routers/merchants.py:572`                 |
| DELETE | `/v1/admin/merchants/{merchant_id}/contacts/{contact_id}`                          | staff session                                      | —      | `routers/merchants.py:597`                 |
| PATCH  | `/v1/admin/merchants/{merchant_id}/contacts/{contact_id}`                          | staff session                                      | —      | `routers/merchants.py:581`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/contracts`                                      | staff session                                      | —      | `routers/merchants.py:604`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/contracts`                                      | staff session                                      | —      | `routers/merchants.py:609`                 |
| PATCH  | `/v1/admin/merchants/{merchant_id}/contracts/{contract_id}`                        | staff session                                      | —      | `routers/merchants.py:619`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/convert-to-customer`                            | staff session                                      | —      | `routers/merchants.py:192`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/credit-notes`                                   | staff session                                      | —      | `routers/merchants.py:298`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/fsa-rate-card`                                  | staff session                                      | —      | `routers/fsa_rate_card.py:69`              |
| PUT    | `/v1/admin/merchants/{merchant_id}/fsa-rate-card/cells/{dest_fsa}`                 | staff session                                      | —      | `routers/fsa_rate_card.py:96`              |
| POST   | `/v1/admin/merchants/{merchant_id}/fsa-rate-card/regenerate`                       | staff session                                      | —      | `routers/fsa_rate_card.py:80`              |
| POST   | `/v1/admin/merchants/{merchant_id}/integrations/freeze`                            | staff session                                      | —      | `routers/merchants_integrations.py:142`    |
| GET    | `/v1/admin/merchants/{merchant_id}/invoices`                                       | staff session                                      | —      | `routers/merchants.py:642`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/locations`                                      | staff session                                      | —      | `routers/merchants.py:369`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/onboarding`                                     | Clerk JWT, get_settings                            | —      | `routers/auth.py:100`                      |
| GET    | `/v1/admin/merchants/{merchant_id}/orders`                                         | staff session                                      | —      | `routers/merchants.py:255`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/owner-seat`                                     | staff session, get_settings                        | —      | `routers/merchants.py:474`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/pricing`                                        | staff session                                      | —      | `routers/merchants.py:232`                 |
| PUT    | `/v1/admin/merchants/{merchant_id}/pricing`                                        | staff session                                      | —      | `routers/merchants.py:239`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/pricing/apply-kaylulu`                          | staff session                                      | —      | `routers/merchants_integrations.py:67`     |
| POST   | `/v1/admin/merchants/{merchant_id}/pricing/clone-from/{source_merchant_id}`        | staff session                                      | —      | `routers/merchants_integrations.py:77`     |
| GET    | `/v1/admin/merchants/{merchant_id}/privacy`                                        | staff session                                      | —      | `routers/merchants.py:208`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/privacy/execute`                                | staff session                                      | —      | `routers/merchants.py:215`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/recipients`                                     | staff session                                      | —      | `routers/merchants.py:406`                 |
| DELETE | `/v1/admin/merchants/{merchant_id}/recipients/{recipient_id}`                      | staff session                                      | —      | `routers/merchants.py:424`                 |
| PATCH  | `/v1/admin/merchants/{merchant_id}/recipients/{recipient_id}`                      | staff session                                      | —      | `routers/merchants.py:413`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/reopen`                                         | staff session                                      | —      | `routers/merchants.py:180`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/shopify/ingress-dlq`                            | staff session                                      | —      | `routers/merchants_integrations.py:254`    |
| POST   | `/v1/admin/merchants/{merchant_id}/shopify/ingress-dlq/{dlq_id}/replay`            | staff session, get_settings                        | —      | `routers/merchants_integrations.py:276`    |
| GET    | `/v1/admin/merchants/{merchant_id}/shopify/install-url`                            | staff session, get_settings                        | —      | `routers/merchants_integrations.py:184`    |
| POST   | `/v1/admin/merchants/{merchant_id}/shopify/{shop_id}/auto-dispatch`                | staff session                                      | —      | `routers/merchants_integrations.py:231`    |
| POST   | `/v1/admin/merchants/{merchant_id}/shopify/{shop_id}/booking-policy`               | staff session                                      | —      | `routers/merchants_integrations.py:322`    |
| POST   | `/v1/admin/merchants/{merchant_id}/shopify/{shop_id}/force-disconnect`             | staff session                                      | —      | `routers/merchants_integrations.py:162`    |
| POST   | `/v1/admin/merchants/{merchant_id}/shopify/{shop_id}/ingress-pause`                | staff session, get_settings                        | —      | `routers/merchants_integrations.py:206`    |
| POST   | `/v1/admin/merchants/{merchant_id}/shopify/{shop_id}/reregister-hooks`             | staff session, get_settings                        | —      | `routers/merchants_integrations.py:298`    |
| GET    | `/v1/admin/merchants/{merchant_id}/standing-orders`                                | staff session                                      | —      | `routers/merchants.py:267`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/standing-orders/{standing_order_id}/deactivate` | staff session                                      | —      | `routers/merchants.py:272`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/statement`                                      | staff session                                      | —      | `routers/merchants.py:287`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/subsidiaries`                                   | staff session                                      | —      | `routers/merchants.py:250`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/suspend`                                        | staff session                                      | —      | `routers/merchants.py:170`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/tasks`                                          | staff session                                      | —      | `routers/merchants.py:652`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/team`                                           | staff session                                      | —      | `routers/merchants.py:464`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/team/seats`                                     | staff session, get_settings                        | —      | `routers/merchants.py:487`                 |
| DELETE | `/v1/admin/merchants/{merchant_id}/team/{user_id}`                                 | staff session                                      | —      | `routers/merchants.py:514`                 |
| PATCH  | `/v1/admin/merchants/{merchant_id}/team/{user_id}`                                 | staff session                                      | —      | `routers/merchants.py:503`                 |
| GET    | `/v1/admin/merchants/{merchant_id}/timeline`                                       | staff session                                      | —      | `routers/merchants.py:561`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/unsuspend`                                      | staff session                                      | —      | `routers/merchants.py:175`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/webhooks/deliveries/{delivery_id}/retry`        | staff session, get_settings                        | —      | `routers/merchants.py:325`                 |
| DELETE | `/v1/admin/merchants/{merchant_id}/webhooks/{webhook_id}`                          | staff session                                      | —      | `routers/merchants_integrations.py:107`    |
| GET    | `/v1/admin/merchants/{merchant_id}/webhooks/{webhook_id}/deliveries`               | staff session                                      | —      | `routers/merchants.py:309`                 |
| POST   | `/v1/admin/merchants/{merchant_id}/webhooks/{webhook_id}/enable`                   | staff session                                      | —      | `routers/merchants_integrations.py:114`    |
| POST   | `/v1/admin/merchants/{merchant_id}/webhooks/{webhook_id}/test`                     | staff session, get_settings                        | —      | `routers/merchants_integrations.py:121`    |
| GET    | `/v1/admin/monopoly-metrics`                                                       | staff session                                      | —      | `routers/admin/monopoly_metrics.py:17`     |
| POST   | `/v1/admin/notifications/broadcast`                                                | staff session                                      | —      | `routers/notifications_admin.py:114`       |
| GET    | `/v1/admin/notifications/center/dead-letters`                                      | staff session                                      | —      | `routers/notifications_center.py:77`       |
| POST   | `/v1/admin/notifications/center/dead-letters/replay-all`                           | staff session                                      | —      | `routers/notifications_center.py:91`       |
| POST   | `/v1/admin/notifications/center/dead-letters/{notification_id}/replay`             | staff session                                      | —      | `routers/notifications_center.py:83`       |
| GET    | `/v1/admin/notifications/center/digest`                                            | staff session                                      | —      | `routers/notifications_center.py:212`      |
| PUT    | `/v1/admin/notifications/center/digest`                                            | staff session                                      | —      | `routers/notifications_center.py:223`      |
| GET    | `/v1/admin/notifications/center/log`                                               | staff session                                      | —      | `routers/notifications_center.py:52`       |
| GET    | `/v1/admin/notifications/center/log/{notification_id}`                             | staff session                                      | —      | `routers/notifications_center.py:68`       |
| GET    | `/v1/admin/notifications/center/matrix`                                            | staff session                                      | —      | `routers/notifications_center.py:190`      |
| PUT    | `/v1/admin/notifications/center/matrix`                                            | staff session                                      | —      | `routers/notifications_center.py:202`      |
| GET    | `/v1/admin/notifications/center/metrics`                                           | staff session                                      | —      | `routers/notifications_center.py:46`       |
| GET    | `/v1/admin/notifications/center/suppressions`                                      | staff session                                      | —      | `routers/notifications_center.py:97`       |
| POST   | `/v1/admin/notifications/center/suppressions/release`                              | staff session                                      | —      | `routers/notifications_center.py:109`      |
| GET    | `/v1/admin/notifications/center/templates`                                         | staff session                                      | —      | `routers/notifications_center.py:117`      |
| PUT    | `/v1/admin/notifications/center/templates/{template}/copy`                         | staff session                                      | —      | `routers/notifications_center.py:152`      |
| GET    | `/v1/admin/notifications/center/templates/{template}/history`                      | staff session                                      | —      | `routers/notifications_center.py:166`      |
| GET    | `/v1/admin/notifications/center/templates/{template}/preview`                      | staff session                                      | —      | `routers/notifications_center.py:129`      |
| POST   | `/v1/admin/notifications/center/templates/{template}/preview`                      | staff session                                      | —      | `routers/notifications_center.py:138`      |
| POST   | `/v1/admin/notifications/center/templates/{template}/test`                         | staff session                                      | —      | `routers/notifications_center.py:178`      |
| GET    | `/v1/admin/notifications/dashboard`                                                | staff session                                      | —      | `routers/notifications_admin.py:28`        |
| GET    | `/v1/admin/notifications/devices`                                                  | staff session                                      | —      | `routers/notifications_admin.py:72`        |
| GET    | `/v1/admin/notifications/entity-alerts`                                            | staff session                                      | —      | `routers/notifications_admin.py:88`        |
| GET    | `/v1/admin/notifications/failed`                                                   | staff session                                      | —      | `routers/notifications_admin.py:60`        |
| GET    | `/v1/admin/notifications/history`                                                  | staff session                                      | —      | `routers/notifications_admin.py:47`        |
| GET    | `/v1/admin/notifications/push-health`                                              | staff session                                      | —      | `routers/notifications_admin.py:78`        |
| GET    | `/v1/admin/notifications/queue`                                                    | staff session                                      | —      | `routers/operations.py:93`                 |
| POST   | `/v1/admin/notifications/retry/{notification_id}`                                  | staff session                                      | —      | `routers/notifications_admin.py:106`       |
| POST   | `/v1/admin/notifications/send-test`                                                | staff session                                      | —      | `routers/notifications_center.py:178`      |
| GET    | `/v1/admin/notifications/templates`                                                | staff session                                      | —      | `routers/notifications_admin.py:66`        |
| GET    | `/v1/admin/notifications/{notification_id}/delivery-logs`                          | staff session                                      | —      | `routers/notifications_admin.py:146`       |
| GET    | `/v1/admin/operations/activity`                                                    | staff session                                      | —      | `routers/operations.py:269`                |
| GET    | `/v1/admin/operations/ai`                                                          | staff session                                      | —      | `routers/operations.py:278`                |
| GET    | `/v1/admin/operations/assignable-drivers`                                          | staff session                                      | —      | `routers/operations.py:102`                |
| GET    | `/v1/admin/operations/board`                                                       | staff session                                      | —      | `routers/operations.py:71`                 |
| POST   | `/v1/admin/operations/board/move`                                                  | staff session                                      | —      | `routers/operations.py:76`                 |
| GET    | `/v1/admin/operations/copilot`                                                     | staff session                                      | —      | `routers/operations.py:283`                |
| POST   | `/v1/admin/operations/copilot/accept`                                              | staff session                                      | —      | `routers/operations.py:325`                |
| GET    | `/v1/admin/operations/copilot/audit`                                               | staff session                                      | —      | `routers/operations.py:316`                |
| POST   | `/v1/admin/operations/copilot/dismiss`                                             | staff session                                      | —      | `routers/operations.py:356`                |
| POST   | `/v1/admin/operations/copilot/llm`                                                 | staff session                                      | —      | `routers/operations.py:289`                |
| POST   | `/v1/admin/operations/copilot/modify`                                              | staff session                                      | —      | `routers/operations.py:340`                |
| GET    | `/v1/admin/operations/dispatch/exceptions`                                         | staff session                                      | —      | `routers/admin/dispatch.py:47`             |
| POST   | `/v1/admin/operations/dispatch/exceptions/apply`                                   | staff session                                      | —      | `routers/admin/dispatch.py:59`             |
| GET    | `/v1/admin/operations/dispatch/fleet-capacity`                                     | staff session                                      | —      | `routers/admin/dispatch.py:102`            |
| PUT    | `/v1/admin/operations/dispatch/fleet-capacity`                                     | staff session                                      | —      | `routers/admin/dispatch.py:107`            |
| GET    | `/v1/admin/operations/dispatch/live-eta`                                           | staff session                                      | —      | `routers/admin/dispatch.py:75`             |
| GET    | `/v1/admin/operations/dispatch/metrics`                                            | staff session                                      | —      | `routers/admin/dispatch.py:41`             |
| POST   | `/v1/admin/operations/dispatch/offers/sweep`                                       | staff session                                      | —      | `routers/admin/dispatch.py:97`             |
| POST   | `/v1/admin/operations/dispatch/orders/{order_id}/delivery-leg`                     | staff session                                      | —      | `routers/admin/dispatch_plan.py:142`       |
| GET    | `/v1/admin/operations/dispatch/orders/{order_id}/hub-split`                        | staff session                                      | —      | `routers/admin/dispatch_plan.py:125`       |
| POST   | `/v1/admin/operations/dispatch/orders/{order_id}/hub-split`                        | staff session                                      | —      | `routers/admin/dispatch_plan.py:130`       |
| GET    | `/v1/admin/operations/dispatch/orders/{order_id}/legs`                             | staff session                                      | —      | `routers/admin/dispatch_plan.py:114`       |
| POST   | `/v1/admin/operations/dispatch/orders/{order_id}/legs/plan`                        | staff session                                      | —      | `routers/admin/dispatch_plan.py:119`       |
| POST   | `/v1/admin/operations/dispatch/orders/{order_id}/offer`                            | staff session                                      | —      | `routers/admin/dispatch.py:91`             |
| GET    | `/v1/admin/operations/dispatch/orders/{order_id}/offers`                           | staff session                                      | —      | `routers/admin/dispatch.py:86`             |
| GET    | `/v1/admin/operations/dispatch/orders/{order_id}/recommend`                        | staff session                                      | —      | `routers/admin/dispatch.py:80`             |
| GET    | `/v1/admin/operations/dispatch/partner-legs`                                       | staff session                                      | —      | `routers/admin/dispatch_plan.py:153`       |
| POST   | `/v1/admin/operations/dispatch/partner-legs/{leg_id}/draft`                        | staff session                                      | —      | `routers/admin/dispatch_plan.py:165`       |
| GET    | `/v1/admin/operations/dispatch/partner-legs/{leg_id}/job-sheet.pdf`                | staff session                                      | —      | `routers/admin/dispatch_plan.py:158`       |
| POST   | `/v1/admin/operations/dispatch/partner-legs/{leg_id}/status`                       | staff session                                      | —      | `routers/admin/dispatch_plan.py:171`       |
| GET    | `/v1/admin/operations/dispatch/partners`                                           | staff session                                      | —      | `routers/admin/dispatch_plan.py:99`        |
| POST   | `/v1/admin/operations/dispatch/partners`                                           | staff session                                      | —      | `routers/admin/dispatch_plan.py:104`       |
| PUT    | `/v1/admin/operations/dispatch/partners/{partner_id}`                              | staff session                                      | —      | `routers/admin/dispatch_plan.py:109`       |
| POST   | `/v1/admin/operations/dispatch/plans`                                              | staff session                                      | —      | `routers/admin/dispatch_plan.py:53`        |
| GET    | `/v1/admin/operations/dispatch/plans/latest`                                       | staff session                                      | —      | `routers/admin/dispatch_plan.py:44`        |
| GET    | `/v1/admin/operations/dispatch/plans/{plan_id}`                                    | staff session                                      | —      | `routers/admin/dispatch_plan.py:67`        |
| POST   | `/v1/admin/operations/dispatch/plans/{plan_id}/commit`                             | staff session                                      | —      | `routers/admin/dispatch_plan.py:78`        |
| POST   | `/v1/admin/operations/dispatch/plans/{plan_id}/explain`                            | staff session                                      | —      | `routers/admin/dispatch_plan.py:92`        |
| POST   | `/v1/admin/operations/dispatch/plans/{plan_id}/replan`                             | staff session                                      | —      | `routers/admin/dispatch_plan.py:72`        |
| POST   | `/v1/admin/operations/dispatch/plans/{plan_id}/undo`                               | staff session                                      | —      | `routers/admin/dispatch_plan.py:86`        |
| GET    | `/v1/admin/operations/dispatch/retention`                                          | staff session                                      | —      | `routers/admin/dispatch_plan.py:179`       |
| PUT    | `/v1/admin/operations/dispatch/retention`                                          | staff session                                      | —      | `routers/admin/dispatch_plan.py:184`       |
| POST   | `/v1/admin/operations/dispatch/retention/run`                                      | staff session                                      | —      | `routers/admin/dispatch_plan.py:189`       |
| GET    | `/v1/admin/operations/drivers/{driver_id}/track`                                   | staff session                                      | —      | `routers/operations_maps.py:13`            |
| GET    | `/v1/admin/operations/exceptions`                                                  | staff session                                      | —      | `routers/operations.py:137`                |
| POST   | `/v1/admin/operations/exceptions/{exception_id}/acknowledge`                       | staff session                                      | —      | `routers/operations.py:146`                |
| POST   | `/v1/admin/operations/exceptions/{exception_id}/resolve`                           | staff session                                      | —      | `routers/operations.py:151`                |
| POST   | `/v1/admin/operations/exceptions/{exception_id}/retry`                             | staff session                                      | —      | `routers/operations.py:158`                |
| GET    | `/v1/admin/operations/live-map`                                                    | staff session                                      | —      | `routers/operations.py:113`                |
| GET    | `/v1/admin/operations/manifests`                                                   | staff session                                      | —      | `routers/operations.py:175`                |
| GET    | `/v1/admin/operations/manifests/{manifest_id}`                                     | staff session                                      | —      | `routers/operations.py:188`                |
| POST   | `/v1/admin/operations/optimize/commit`                                             | staff session                                      | —      | `routers/operations.py:236`                |
| GET    | `/v1/admin/operations/optimize/engines`                                            | staff session                                      | —      | `routers/operations.py:202`                |
| GET    | `/v1/admin/operations/optimize/pool`                                               | staff session                                      | —      | `routers/operations.py:196`                |
| POST   | `/v1/admin/operations/optimize/run`                                                | staff session                                      | —      | `routers/operations.py:207`                |
| GET    | `/v1/admin/operations/optimize/runs/{run_id}`                                      | staff session                                      | —      | `routers/operations.py:227`                |
| GET    | `/v1/admin/operations/orders`                                                      | staff session                                      | —      | `routers/operations.py:83`                 |
| GET    | `/v1/admin/operations/orders/{order_id}/driver-suggestions`                        | staff session                                      | —      | `routers/operations.py:107`                |
| GET    | `/v1/admin/operations/orders/{order_id}/playback`                                  | staff session                                      | —      | `routers/operations.py:125`                |
| GET    | `/v1/admin/operations/orders/{order_id}/route-geometry`                            | staff session                                      | —      | `routers/operations.py:119`                |
| GET    | `/v1/admin/operations/queue`                                                       | staff session                                      | —      | `routers/operations.py:93`                 |
| GET    | `/v1/admin/operations/queues`                                                      | staff session                                      | —      | `routers/operations.py:379`                |
| GET    | `/v1/admin/operations/scheduled-batches`                                           | staff session                                      | —      | `routers/operations.py:164`                |
| GET    | `/v1/admin/operations/search`                                                      | staff session                                      | —      | `routers/operations.py:363`                |
| GET    | `/v1/admin/operations/service-area`                                                | staff session                                      | —      | `routers/operations_maps.py:21`            |
| GET    | `/v1/admin/operations/sla`                                                         | staff session                                      | —      | `routers/operations.py:264`                |
| GET    | `/v1/admin/operations/stats`                                                       | staff session                                      | —      | `routers/operations.py:66`                 |
| GET    | `/v1/admin/operations/sync/health`                                                 | staff session                                      | —      | `routers/operations.py:374`                |
| POST   | `/v1/admin/operations/sync/process`                                                | staff session                                      | —      | `routers/operations.py:385`                |
| POST   | `/v1/admin/operations/sync/requeue/{job_id}`                                       | staff session                                      | —      | `routers/operations.py:390`                |
| GET    | `/v1/admin/operations/utilization`                                                 | staff session                                      | —      | `routers/operations.py:131`                |
| GET    | `/v1/admin/orders`                                                                 | staff session                                      | —      | `routers/admin/orders.py:81`               |
| POST   | `/v1/admin/orders`                                                                 | staff session, get_settings                        | —      | `routers/admin/orders.py:126`              |
| POST   | `/v1/admin/orders/bulk`                                                            | staff session, get_settings                        | —      | `routers/admin/orders.py:137`              |
| GET    | `/v1/admin/orders/dashboard`                                                       | staff session                                      | —      | `routers/admin/orders.py:71`               |
| POST   | `/v1/admin/orders/labels/bulk`                                                     | staff session                                      | —      | `routers/admin/orders.py:147`              |
| GET    | `/v1/admin/orders/pickup-manifest.pdf`                                             | staff session                                      | —      | `routers/admin/orders.py:153`              |
| GET    | `/v1/admin/orders/reports`                                                         | staff session, get_report_db                       | —      | `routers/admin/orders.py:76`               |
| GET    | `/v1/admin/orders/{order_id}`                                                      | staff session, get_settings, require_detail_       | —      | `routers/admin/orders.py:161`              |
| GET    | `/v1/admin/orders/{order_id}/assist`                                               | staff session, get_settings                        | —      | `routers/admin/orders.py:300`              |
| POST   | `/v1/admin/orders/{order_id}/assist/decide`                                        | staff session, get_settings                        | —      | `routers/admin/orders.py:308`              |
| GET    | `/v1/admin/orders/{order_id}/attachments`                                          | staff session                                      | —      | `routers/booking_attachments/driver.py:71` |
| GET    | `/v1/admin/orders/{order_id}/audit-export`                                         | staff session, get_report_db, require_audit_export | —      | `routers/admin/orders.py:205`              |
| GET    | `/v1/admin/orders/{order_id}/compliance-dossier.pdf`                               | staff session                                      | —      | `routers/admin/orders.py:225`              |
| GET    | `/v1/admin/orders/{order_id}/driver-ops`                                           | staff session                                      | —      | `routers/admin/driver_ops.py:34`           |
| POST   | `/v1/admin/orders/{order_id}/driver-ops`                                           | staff session, get_settings                        | —      | `routers/admin/driver_ops.py:39`           |
| POST   | `/v1/admin/orders/{order_id}/extra-stops`                                          | staff session, get_settings                        | —      | `routers/admin/driver_ops.py:82`           |
| POST   | `/v1/admin/orders/{order_id}/extra-stops/{leg}/resend`                             | staff session                                      | —      | `routers/admin/driver_ops.py:104`          |
| POST   | `/v1/admin/orders/{order_id}/invoice`                                              | staff session                                      | —      | `routers/admin/orders.py:260`              |
| GET    | `/v1/admin/orders/{order_id}/invoice.pdf`                                          | staff session                                      | —      | `routers/admin/orders.py:293`              |
| GET    | `/v1/admin/orders/{order_id}/label.pdf`                                            | staff session                                      | —      | `routers/admin/orders.py:272`              |
| GET    | `/v1/admin/orders/{order_id}/labels.pdf`                                           | staff session                                      | —      | `routers/admin/orders.py:279`              |
| GET    | `/v1/admin/orders/{order_id}/manifest.pdf`                                         | staff session                                      | —      | `routers/admin/orders.py:286`              |
| PATCH  | `/v1/admin/orders/{order_id}/parcels`                                              | staff session, get_settings                        | —      | `routers/admin/orders.py:170`              |
| POST   | `/v1/admin/orders/{order_id}/parcels/{parcel_id}/status`                           | staff session                                      | —      | `routers/admin/driver_ops.py:50`           |
| POST   | `/v1/admin/orders/{order_id}/playbooks/{playbook_id}`                              | staff session, get_settings                        | —      | `routers/admin/orders.py:320`              |
| GET    | `/v1/admin/orders/{order_id}/pod.zip`                                              | staff session, get_settings                        | —      | `routers/admin/orders.py:232`              |
| GET    | `/v1/admin/orders/{order_id}/pod/{slug}`                                           | staff session, get_settings                        | —      | `routers/admin/orders.py:241`              |
| POST   | `/v1/admin/orders/{order_id}/proof`                                                | staff session, get_settings                        | —      | `routers/admin/driver_ops.py:71`           |
| POST   | `/v1/admin/orders/{order_id}/resend-receipt`                                       | staff session                                      | —      | `routers/admin/orders.py:266`              |
| POST   | `/v1/admin/orders/{order_id}/shopify/release`                                      | staff session                                      | —      | `routers/admin/orders.py:335`              |
| POST   | `/v1/admin/orders/{order_id}/shopify/repush-fulfillment`                           | staff session, get_settings                        | —      | `routers/admin/orders.py:349`              |
| POST   | `/v1/admin/orders/{order_id}/temperature`                                          | staff session, get_settings                        | —      | `routers/admin/orders.py:211`              |
| GET    | `/v1/admin/orders/{order_id}/timeline`                                             | staff session                                      | —      | `routers/admin/orders.py:200`              |
| GET    | `/v1/admin/orders/{order_id}/tracking`                                             | staff session, get_settings, require_tracking      | —      | `routers/admin/orders.py:193`              |
| GET    | `/v1/admin/platform-metrics`                                                       | staff session                                      | —      | `routers/admin/platform_metrics.py:17`     |
| GET    | `/v1/admin/privacy/access-export`                                                  | staff session, get_report_db                       | —      | `routers/admin/finance_insights.py:130`    |
| POST   | `/v1/admin/privacy/erase`                                                          | staff session                                      | —      | `routers/admin/compliance.py:28`           |
| GET    | `/v1/admin/route-templates`                                                        | staff session                                      | —      | `routers/admin/route_templates.py:26`      |
| POST   | `/v1/admin/route-templates`                                                        | staff session                                      | —      | `routers/admin/route_templates.py:53`      |
| DELETE | `/v1/admin/route-templates/{template_id}`                                          | staff session                                      | —      | `routers/admin/route_templates.py:114`     |
| GET    | `/v1/admin/route-templates/{template_id}`                                          | staff session                                      | —      | `routers/admin/route_templates.py:40`      |
| PATCH  | `/v1/admin/route-templates/{template_id}`                                          | staff session                                      | —      | `routers/admin/route_templates.py:81`      |
| GET    | `/v1/admin/security/my-ip`                                                         | staff session                                      | —      | `routers/admin/compliance.py:58`           |
| GET    | `/v1/admin/settings/audit`                                                         | staff session                                      | —      | `routers/admin/settings.py:144`            |
| POST   | `/v1/admin/settings/audit/{audit_id}/restore`                                      | staff session, get_settings                        | —      | `routers/admin/settings.py:153`            |
| GET    | `/v1/admin/settings/bindings`                                                      | staff session                                      | —      | `routers/admin/settings.py:197`            |
| GET    | `/v1/admin/settings/center`                                                        | staff session, get_settings                        | —      | `routers/admin/settings.py:118`            |
| GET    | `/v1/admin/settings/config`                                                        | staff session                                      | —      | `routers/admin/settings.py:236`            |
| PUT    | `/v1/admin/settings/config/{key}`                                                  | staff session, get_settings                        | —      | `routers/admin/settings.py:250`            |
| GET    | `/v1/admin/settings/dashboard`                                                     | staff session, get_settings                        | —      | `routers/admin/settings.py:90`             |
| GET    | `/v1/admin/settings/export`                                                        | staff session, get_report_db                       | —      | `routers/admin/settings.py:189`            |
| GET    | `/v1/admin/settings/future`                                                        | staff session                                      | —      | `routers/admin/finance_insights.py:119`    |
| GET    | `/v1/admin/settings/health`                                                        | staff session, get_settings                        | —      | `routers/admin/settings.py:127`            |
| POST   | `/v1/admin/settings/import`                                                        | staff session, get_settings                        | —      | `routers/admin/settings.py:204`            |
| GET    | `/v1/admin/settings/lead-ingest`                                                   | staff session, get_settings                        | —      | `routers/admin/settings.py:276`            |
| PUT    | `/v1/admin/settings/lead-ingest`                                                   | staff session, get_settings                        | —      | `routers/admin/settings.py:287`            |
| POST   | `/v1/admin/settings/project-mode`                                                  | staff session, get_settings                        | —      | `routers/admin/settings.py:99`             |
| GET    | `/v1/admin/settings/search`                                                        | staff session                                      | —      | `routers/admin/settings.py:172`            |
| GET    | `/v1/admin/settings/sections`                                                      | staff session                                      | —      | `routers/admin/settings.py:137`            |
| GET    | `/v1/admin/settings/staff`                                                         | staff session                                      | —      | `routers/admin/settings_directory.py:38`   |
| POST   | `/v1/admin/settings/staff/enroll`                                                  | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:202`  |
| POST   | `/v1/admin/settings/staff/{user_id}/enroll-reissue`                                | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:230`  |
| POST   | `/v1/admin/settings/staff/{user_id}/recover-device`                                | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:245`  |
| PATCH  | `/v1/admin/settings/staff/{user_id}/role`                                          | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:270`  |
| GET    | `/v1/admin/settings/users/{user_type}`                                             | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:46`   |
| POST   | `/v1/admin/settings/users/{user_type}`                                             | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:76`   |
| POST   | `/v1/admin/settings/users/{user_type}/authorize`                                   | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:150`  |
| PATCH  | `/v1/admin/settings/users/{user_type}/clerk`                                       | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:102`  |
| POST   | `/v1/admin/settings/users/{user_type}/delete`                                      | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:126`  |
| POST   | `/v1/admin/settings/users/{user_type}/invite`                                      | staff session, get_settings                        | —      | `routers/admin/settings_directory.py:177`  |
| GET    | `/v1/admin/settings/validate`                                                      | staff session, get_settings                        | —      | `routers/admin/settings.py:180`            |
| GET    | `/v1/admin/settings/vehicles/overview`                                             | staff session                                      | —      | `routers/admin/settings.py:228`            |
| GET    | `/v1/admin/support/automation`                                                     | staff session                                      | —      | `routers/admin/support.py:266`             |
| POST   | `/v1/admin/support/automation`                                                     | staff session                                      | —      | `routers/admin/support.py:275`             |
| POST   | `/v1/admin/support/bulk`                                                           | staff session                                      | —      | `routers/admin/support.py:209`             |
| GET    | `/v1/admin/support/dashboard`                                                      | staff session                                      | —      | `routers/admin/support.py:33`              |
| GET    | `/v1/admin/support/knowledge-base`                                                 | staff session                                      | —      | `routers/admin/support.py:228`             |
| POST   | `/v1/admin/support/knowledge-base/articles`                                        | staff session                                      | —      | `routers/admin/support.py:237`             |
| GET    | `/v1/admin/support/macros`                                                         | staff session                                      | —      | `routers/admin/support.py:247`             |
| POST   | `/v1/admin/support/macros`                                                         | staff session                                      | —      | `routers/admin/support.py:256`             |
| GET    | `/v1/admin/support/reports`                                                        | staff session, get_report_db                       | —      | `routers/admin/support.py:42`              |
| GET    | `/v1/admin/support/settings/sla`                                                   | staff session                                      | —      | `routers/admin/support.py:285`             |
| POST   | `/v1/admin/support/settings/sla`                                                   | staff session                                      | —      | `routers/admin/support.py:294`             |
| GET    | `/v1/admin/support/tickets`                                                        | staff session                                      | —      | `routers/admin/support.py:51`              |
| POST   | `/v1/admin/support/tickets`                                                        | staff session                                      | —      | `routers/admin/support.py:103`             |
| GET    | `/v1/admin/support/tickets/{ticket_id}`                                            | staff session                                      | —      | `routers/admin/support.py:90`              |
| POST   | `/v1/admin/support/tickets/{ticket_id}/assign`                                     | staff session                                      | —      | `routers/admin/support.py:132`             |
| POST   | `/v1/admin/support/tickets/{ticket_id}/auto-assign`                                | staff session                                      | —      | `routers/admin/support.py:148`             |
| POST   | `/v1/admin/support/tickets/{ticket_id}/notes`                                      | staff session                                      | —      | `routers/admin/support.py:163`             |
| POST   | `/v1/admin/support/tickets/{ticket_id}/sla/pause`                                  | staff session                                      | —      | `routers/admin/support.py:179`             |
| POST   | `/v1/admin/support/tickets/{ticket_id}/sla/resume`                                 | staff session                                      | —      | `routers/admin/support.py:194`             |
| POST   | `/v1/admin/support/tickets/{ticket_id}/status`                                     | staff session                                      | —      | `routers/admin/support.py:114`             |
| GET    | `/v1/admin/visitor-intelligence/{session_id}`                                      | staff session                                      | —      | `routers/admin/visitor_intelligence.py:30` |

### merchant portal

| Method | Path                                                                | Auth                                          | Module | Handler                                       |
| ------ | ------------------------------------------------------------------- | --------------------------------------------- | ------ | --------------------------------------------- |
| GET    | `/v1/merchant/addresses`                                            | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:114`        |
| POST   | `/v1/merchant/addresses`                                            | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:122`        |
| DELETE | `/v1/merchant/addresses/{address_id}`                               | merchant (Clerk)                              | —      | `routers/merchant/settings.py:217`            |
| PATCH  | `/v1/merchant/addresses/{address_id}`                               | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:132`        |
| POST   | `/v1/merchant/addresses/{address_id}/default`                       | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:143`        |
| GET    | `/v1/merchant/api-keys`                                             | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:63`         |
| POST   | `/v1/merchant/api-keys`                                             | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:68`         |
| DELETE | `/v1/merchant/api-keys/{key_id}`                                    | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:76`         |
| GET    | `/v1/merchant/attachments/locations`                                | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:71`  |
| POST   | `/v1/merchant/attachments/locations`                                | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:77`  |
| POST   | `/v1/merchant/attachments/suggest`                                  | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:28`  |
| DELETE | `/v1/merchant/attachments/{attachment_id}`                          | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:125` |
| PATCH  | `/v1/merchant/attachments/{attachment_id}`                          | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:108` |
| GET    | `/v1/merchant/attachments/{attachment_id}/file`                     | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:142` |
| GET    | `/v1/merchant/audit-logs`                                           | merchant (Clerk)                              | —      | `routers/merchant/settings.py:35`             |
| GET    | `/v1/merchant/billing/contract`                                     | merchant (Clerk)                              | —      | `routers/merchant/billing.py:184`             |
| GET    | `/v1/merchant/billing/credit-notes`                                 | merchant (Clerk)                              | —      | `routers/merchant/billing.py:139`             |
| GET    | `/v1/merchant/billing/export/history.csv`                           | merchant (Clerk), get_report_db               | —      | `routers/merchant/billing.py:232`             |
| GET    | `/v1/merchant/billing/export/invoices.csv`                          | merchant (Clerk), get_report_db               | —      | `routers/merchant/billing.py:204`             |
| GET    | `/v1/merchant/billing/export/statement.csv`                         | merchant (Clerk), get_report_db               | —      | `routers/merchant/billing.py:218`             |
| GET    | `/v1/merchant/billing/history`                                      | merchant (Clerk)                              | —      | `routers/merchant/billing.py:166`             |
| GET    | `/v1/merchant/billing/invoices`                                     | merchant (Clerk)                              | —      | `routers/merchant/billing.py:65`              |
| GET    | `/v1/merchant/billing/invoices/{invoice_id}`                        | merchant (Clerk)                              | —      | `routers/merchant/billing.py:75`              |
| GET    | `/v1/merchant/billing/invoices/{invoice_id}/pdf`                    | merchant (Clerk)                              | —      | `routers/merchant/billing.py:91`              |
| POST   | `/v1/merchant/billing/invoices/{invoice_id}/remind`                 | merchant (Clerk)                              | —      | `routers/merchant/billing.py:113`             |
| GET    | `/v1/merchant/billing/overview`                                     | merchant (Clerk)                              | —      | `routers/merchant/billing.py:33`              |
| GET    | `/v1/merchant/billing/payments`                                     | merchant (Clerk)                              | —      | `routers/merchant/billing.py:130`             |
| GET    | `/v1/merchant/billing/statement`                                    | merchant (Clerk)                              | —      | `routers/merchant/billing.py:47`              |
| GET    | `/v1/merchant/billing/statement.pdf`                                | merchant (Clerk)                              | —      | `routers/merchant/billing_statement.py:17`    |
| GET    | `/v1/merchant/billing/statement/detail`                             | merchant (Clerk)                              | —      | `routers/merchant/billing.py:56`              |
| GET    | `/v1/merchant/billing/tax-summary`                                  | merchant (Clerk)                              | —      | `routers/merchant/billing.py:175`             |
| POST   | `/v1/merchant/booking/confirm`                                      | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:112`   |
| GET    | `/v1/merchant/booking/draft`                                        | merchant (Clerk)                              | —      | `routers/merchant/dashboard_booking.py:174`   |
| POST   | `/v1/merchant/booking/draft`                                        | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:187`   |
| POST   | `/v1/merchant/booking/draft/{draft_id}/confirm`                     | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:204`   |
| POST   | `/v1/merchant/booking/multi`                                        | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:147`   |
| POST   | `/v1/merchant/booking/preview`                                      | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:96`    |
| GET    | `/v1/merchant/booking/recipients`                                   | merchant (Clerk)                              | —      | `routers/merchant/dashboard_booking.py:285`   |
| GET    | `/v1/merchant/booking/saved-addresses`                              | merchant (Clerk)                              | —      | `routers/merchant/dashboard_booking.py:272`   |
| GET    | `/v1/merchant/booking/templates`                                    | merchant (Clerk)                              | —      | `routers/merchant/dashboard_booking.py:223`   |
| POST   | `/v1/merchant/booking/templates`                                    | merchant (Clerk)                              | —      | `routers/merchant/dashboard_booking.py:236`   |
| DELETE | `/v1/merchant/booking/templates/{template_id}`                      | merchant (Clerk)                              | —      | `routers/merchant/dashboard_booking.py:257`   |
| POST   | `/v1/merchant/bookings`                                             | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:63`    |
| POST   | `/v1/merchant/bulk/upload`                                          | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:307`   |
| POST   | `/v1/merchant/bulk/{job_id}/confirm`                                | merchant (Clerk), get_settings                | —      | `routers/merchant/dashboard_booking.py:333`   |
| GET    | `/v1/merchant/claims`                                               | merchant (Clerk)                              | —      | `routers/merchant/support_claims.py:67`       |
| POST   | `/v1/merchant/claims`                                               | merchant (Clerk)                              | —      | `routers/merchant/support_claims.py:90`       |
| GET    | `/v1/merchant/claims/{claim_id}`                                    | merchant (Clerk)                              | —      | `routers/merchant/support_claims.py:77`       |
| GET    | `/v1/merchant/contacts`                                             | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:191`        |
| POST   | `/v1/merchant/contacts`                                             | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:199`        |
| DELETE | `/v1/merchant/contacts/{contact_id}`                                | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:222`        |
| PATCH  | `/v1/merchant/contacts/{contact_id}`                                | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:209`        |
| GET    | `/v1/merchant/contract-documents`                                   | merchant (Clerk)                              | —      | `routers/merchant/settings.py:231`            |
| GET    | `/v1/merchant/contract-documents/{doc_id}/download`                 | merchant (Clerk)                              | —      | `routers/merchant/settings.py:243`            |
| GET    | `/v1/merchant/dashboard`                                            | merchant (Clerk)                              | —      | `routers/merchant/dashboard_booking.py:54`    |
| PATCH  | `/v1/merchant/integrations/api-keys/{key_id}/rate-limit`            | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:231`        |
| POST   | `/v1/merchant/integrations/console`                                 | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:313`        |
| GET    | `/v1/merchant/integrations/csv-templates`                           | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:298`        |
| GET    | `/v1/merchant/integrations/csv-templates/{template_id}.csv`         | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:303`        |
| GET    | `/v1/merchant/integrations/depth`                                   | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:268`        |
| GET    | `/v1/merchant/integrations/documentation`                           | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:111`        |
| GET    | `/v1/merchant/integrations/erp`                                     | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:238`        |
| GET    | `/v1/merchant/integrations/events`                                  | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:116`        |
| POST   | `/v1/merchant/integrations/netsuite/connect`                        | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:249`        |
| GET    | `/v1/merchant/integrations/netsuite/setup`                          | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:243`        |
| POST   | `/v1/merchant/integrations/netsuite/sync`                           | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:254`        |
| GET    | `/v1/merchant/integrations/oauth`                                   | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:274`        |
| GET    | `/v1/merchant/integrations/oauth/clients`                           | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:279`        |
| POST   | `/v1/merchant/integrations/oauth/clients`                           | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:284`        |
| GET    | `/v1/merchant/integrations/overview`                                | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:106`        |
| GET    | `/v1/merchant/integrations/rate-limits`                             | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:126`        |
| GET    | `/v1/merchant/integrations/sandbox`                                 | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:131`        |
| PATCH  | `/v1/merchant/integrations/sandbox`                                 | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:136`        |
| POST   | `/v1/merchant/integrations/sandbox/purge`                           | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:141`        |
| POST   | `/v1/merchant/integrations/sandbox/simulate`                        | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:150`        |
| GET    | `/v1/merchant/integrations/usage`                                   | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:121`        |
| POST   | `/v1/merchant/integrations/webhooks/deliveries/{delivery_id}/retry` | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:191`        |
| GET    | `/v1/merchant/integrations/webhooks/logs`                           | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:169`        |
| DELETE | `/v1/merchant/integrations/webhooks/{webhook_id}`                   | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:216`        |
| PATCH  | `/v1/merchant/integrations/webhooks/{webhook_id}`                   | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:198`        |
| GET    | `/v1/merchant/integrations/webhooks/{webhook_id}/history`           | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:179`        |
| POST   | `/v1/merchant/integrations/webhooks/{webhook_id}/rotate-secret`     | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:221`        |
| POST   | `/v1/merchant/integrations/webhooks/{webhook_id}/test`              | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:184`        |
| GET    | `/v1/merchant/integrations/zapier/templates`                        | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:262`        |
| GET    | `/v1/merchant/me`                                                   | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:75`         |
| GET    | `/v1/merchant/memberships`                                          | get_merchant_seats                            | —      | `routers/merchant/profile_team.py:83`         |
| GET    | `/v1/merchant/orders`                                               | staff session                                 | —      | `routers/admin/orders.py:81`                  |
| POST   | `/v1/merchant/orders/bulk`                                          | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:176`     |
| GET    | `/v1/merchant/orders/dashboard`                                     | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:96`      |
| POST   | `/v1/merchant/orders/labels/bulk`                                   | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:169`     |
| GET    | `/v1/merchant/orders/pickup-list.pdf`                               | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:155`     |
| GET    | `/v1/merchant/orders/pickup-manifest.pdf`                           | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:162`     |
| GET    | `/v1/merchant/orders/{order_id}`                                    | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:185`     |
| GET    | `/v1/merchant/orders/{order_id}/360`                                | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:193`     |
| GET    | `/v1/merchant/orders/{order_id}/attachments`                        | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:34`  |
| POST   | `/v1/merchant/orders/{order_id}/attachments`                        | merchant (Clerk)                              | —      | `routers/booking_attachments/merchant.py:40`  |
| POST   | `/v1/merchant/orders/{order_id}/cancel`                             | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:281`     |
| GET    | `/v1/merchant/orders/{order_id}/compliance-dossier.pdf`             | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:298`     |
| PATCH  | `/v1/merchant/orders/{order_id}/delivery-options`                   | merchant (Clerk)                              | —      | `routers/merchant/settings.py:293`            |
| POST   | `/v1/merchant/orders/{order_id}/duplicate`                          | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:291`     |
| GET    | `/v1/merchant/orders/{order_id}/external-ids`                       | merchant (Clerk), require_owned               | —      | `routers/merchant/package_external_ids.py:45` |
| POST   | `/v1/merchant/orders/{order_id}/external-ids`                       | merchant (Clerk), require_owned               | —      | `routers/merchant/package_external_ids.py:59` |
| DELETE | `/v1/merchant/orders/{order_id}/external-ids/{identifier_id}`       | merchant (Clerk), require_owned               | —      | `routers/merchant/package_external_ids.py:74` |
| GET    | `/v1/merchant/orders/{order_id}/labels.pdf`                         | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:338`     |
| PATCH  | `/v1/merchant/orders/{order_id}/parcels`                            | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:200`     |
| GET    | `/v1/merchant/orders/{order_id}/pod.zip`                            | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:305`     |
| GET    | `/v1/merchant/orders/{order_id}/pod/{slug}`                         | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:316`     |
| GET    | `/v1/merchant/orders/{order_id}/print-preview.pdf`                  | merchant (Clerk)                              | —      | `routers/merchant/orders_tracking.py:331`     |
| GET    | `/v1/merchant/orders/{order_id}/returns`                            | merchant (Clerk)                              | —      | `routers/merchant/order_returns.py:34`        |
| POST   | `/v1/merchant/orders/{order_id}/returns`                            | merchant (Clerk), get_settings                | —      | `routers/merchant/order_returns.py:23`        |
| GET    | `/v1/merchant/orders/{order_id}/tracking`                           | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:222`     |
| POST   | `/v1/merchant/orders/{order_id}/tracking-email`                     | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:258`     |
| GET    | `/v1/merchant/pricing/fsa-rate-card`                                | merchant (Clerk)                              | —      | `routers/fsa_rate_card.py:59`                 |
| GET    | `/v1/merchant/pricing/rate-card`                                    | merchant (Clerk)                              | —      | `routers/merchant/billing.py:193`             |
| GET    | `/v1/merchant/pricing/route-pricing`                                | merchant (Clerk)                              | —      | `routers/merchant/route_pricing.py:17`        |
| POST   | `/v1/merchant/pricing/route-pricing`                                | merchant (Clerk)                              | —      | `routers/merchant/route_pricing.py:28`        |
| GET    | `/v1/merchant/privacy`                                              | merchant (Clerk)                              | —      | `routers/merchant/privacy.py:23`              |
| POST   | `/v1/merchant/privacy/delete-request`                               | merchant (Clerk)                              | —      | `routers/merchant/privacy.py:41`              |
| GET    | `/v1/merchant/privacy/export`                                       | merchant (Clerk), get_report_db               | —      | `routers/merchant/privacy.py:32`              |
| GET    | `/v1/merchant/profile`                                              | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:96`         |
| PATCH  | `/v1/merchant/profile`                                              | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:104`        |
| GET    | `/v1/merchant/recipients`                                           | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:153`        |
| POST   | `/v1/merchant/recipients`                                           | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:161`        |
| DELETE | `/v1/merchant/recipients/{recipient_id}`                            | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:182`        |
| PATCH  | `/v1/merchant/recipients/{recipient_id}`                            | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:171`        |
| GET    | `/v1/merchant/referrals`                                            | merchant (Clerk), get_settings                | —      | `routers/merchant/referrals.py:33`            |
| POST   | `/v1/merchant/referrals`                                            | merchant (Clerk)                              | —      | `routers/merchant/referrals.py:50`            |
| GET    | `/v1/merchant/reports/claims`                                       | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:104`             |
| GET    | `/v1/merchant/reports/delivery-performance`                         | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:50`              |
| GET    | `/v1/merchant/reports/destinations`                                 | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:95`              |
| GET    | `/v1/merchant/reports/drivers`                                      | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:77`              |
| GET    | `/v1/merchant/reports/executive`                                    | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:41`              |
| GET    | `/v1/merchant/reports/export/{report_type}.csv`                     | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:194`             |
| GET    | `/v1/merchant/reports/export/{report_type}.xlsx`                    | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:209`             |
| GET    | `/v1/merchant/reports/invoices`                                     | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:68`              |
| GET    | `/v1/merchant/reports/order-volume`                                 | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:59`              |
| GET    | `/v1/merchant/reports/overview`                                     | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:32`              |
| GET    | `/v1/merchant/reports/saved`                                        | merchant (Clerk)                              | —      | `routers/merchant/reports.py:133`             |
| POST   | `/v1/merchant/reports/saved`                                        | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:141`             |
| DELETE | `/v1/merchant/reports/saved/{report_id}`                            | merchant (Clerk)                              | —      | `routers/merchant/reports.py:158`             |
| GET    | `/v1/merchant/reports/scheduled`                                    | merchant (Clerk)                              | —      | `routers/merchant/reports.py:169`             |
| POST   | `/v1/merchant/reports/scheduled`                                    | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:177`             |
| GET    | `/v1/merchant/reports/sla-history`                                  | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:113`             |
| GET    | `/v1/merchant/reports/summary`                                      | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:23`              |
| GET    | `/v1/merchant/reports/switching-costs`                              | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:123`             |
| GET    | `/v1/merchant/reports/vehicles`                                     | merchant (Clerk), get_report_db               | —      | `routers/merchant/reports.py:86`              |
| GET    | `/v1/merchant/route-import-profiles`                                | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:225`       |
| GET    | `/v1/merchant/route-imports`                                        | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:123`       |
| POST   | `/v1/merchant/route-imports`                                        | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:69`        |
| POST   | `/v1/merchant/route-imports/upload`                                 | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:89`        |
| GET    | `/v1/merchant/route-imports/{job_id}`                               | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:148`       |
| POST   | `/v1/merchant/route-imports/{job_id}/confirm`                       | merchant (Clerk), get_settings                | —      | `routers/merchant/route_imports.py:285`       |
| PATCH  | `/v1/merchant/route-imports/{job_id}/mapping`                       | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:163`       |
| POST   | `/v1/merchant/route-imports/{job_id}/mapping-profile`               | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:240`       |
| POST   | `/v1/merchant/route-imports/{job_id}/mapping-profile/apply`         | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:263`       |
| POST   | `/v1/merchant/route-imports/{job_id}/optimize`                      | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:208`       |
| PATCH  | `/v1/merchant/route-imports/{job_id}/stops/{index}`                 | merchant (Clerk)                              | —      | `routers/merchant/route_imports.py:182`       |
| GET    | `/v1/merchant/session`                                              | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:66`         |
| GET    | `/v1/merchant/settings/billing-contacts`                            | merchant (Clerk)                              | —      | `routers/merchant/settings.py:76`             |
| POST   | `/v1/merchant/settings/billing-contacts`                            | merchant (Clerk)                              | —      | `routers/merchant/settings.py:84`             |
| DELETE | `/v1/merchant/settings/billing-contacts/{contact_id}`               | merchant (Clerk)                              | —      | `routers/merchant/settings.py:110`            |
| PATCH  | `/v1/merchant/settings/billing-contacts/{contact_id}`               | merchant (Clerk)                              | —      | `routers/merchant/settings.py:94`             |
| PATCH  | `/v1/merchant/settings/branding`                                    | merchant (Clerk)                              | —      | `routers/merchant/settings.py:58`             |
| GET    | `/v1/merchant/settings/contract`                                    | merchant (Clerk)                              | —      | `routers/merchant/settings.py:208`            |
| GET    | `/v1/merchant/settings/customer-experience`                         | merchant (Clerk)                              | —      | `routers/merchant/customer_experience.py:22`  |
| PUT    | `/v1/merchant/settings/customer-experience`                         | merchant (Clerk)                              | —      | `routers/merchant/customer_experience.py:28`  |
| GET    | `/v1/merchant/settings/delivery-defaults`                           | merchant (Clerk)                              | —      | `routers/merchant/settings.py:270`            |
| PUT    | `/v1/merchant/settings/delivery-defaults`                           | merchant (Clerk)                              | —      | `routers/merchant/settings.py:281`            |
| GET    | `/v1/merchant/settings/documents`                                   | merchant (Clerk)                              | —      | `routers/merchant/settings.py:159`            |
| POST   | `/v1/merchant/settings/documents`                                   | merchant (Clerk)                              | —      | `routers/merchant/settings.py:167`            |
| DELETE | `/v1/merchant/settings/documents/{doc_id}`                          | merchant (Clerk)                              | —      | `routers/merchant/settings.py:177`            |
| PATCH  | `/v1/merchant/settings/notifications`                               | merchant (Clerk)                              | —      | `routers/merchant/settings.py:48`             |
| GET    | `/v1/merchant/settings/overview`                                    | merchant (Clerk)                              | —      | `routers/merchant/settings.py:26`             |
| GET    | `/v1/merchant/settings/tax`                                         | merchant (Clerk)                              | —      | `routers/merchant/settings.py:187`            |
| PATCH  | `/v1/merchant/settings/tax`                                         | merchant (Clerk)                              | —      | `routers/merchant/settings.py:195`            |
| GET    | `/v1/merchant/settings/warehouses`                                  | merchant (Clerk)                              | —      | `routers/merchant/settings.py:120`            |
| POST   | `/v1/merchant/settings/warehouses`                                  | merchant (Clerk)                              | —      | `routers/merchant/settings.py:128`            |
| DELETE | `/v1/merchant/settings/warehouses/{warehouse_id}`                   | merchant (Clerk)                              | —      | `routers/merchant/settings.py:149`            |
| PATCH  | `/v1/merchant/settings/warehouses/{warehouse_id}`                   | merchant (Clerk)                              | —      | `routers/merchant/settings.py:138`            |
| GET    | `/v1/merchant/shopify`                                              | merchant (Clerk), get_settings                | —      | `routers/merchant/shopify.py:29`              |
| POST   | `/v1/merchant/shopify`                                              | merchant (Clerk), get_settings                | —      | `routers/merchant/shopify.py:76`              |
| POST   | `/v1/merchant/shopify/go-live`                                      | merchant (Clerk), get_settings                | —      | `routers/merchant/shopify.py:101`             |
| GET    | `/v1/merchant/shopify/install-url`                                  | merchant (Clerk), get_settings                | —      | `routers/merchant/shopify.py:41`              |
| POST   | `/v1/merchant/shopify/link`                                         | merchant (Clerk), get_settings                | —      | `routers/merchant/shopify.py:56`              |
| GET    | `/v1/merchant/shopify/orders`                                       | merchant (Clerk)                              | —      | `routers/merchant/settings.py:310`            |
| GET    | `/v1/merchant/shopify/privacy/requests`                             | merchant (Clerk)                              | —      | `routers/merchant/privacy.py:53`              |
| GET    | `/v1/merchant/shopify/privacy/requests/{request_id}/export`         | merchant (Clerk), get_report_db, get_settings | —      | `routers/merchant/privacy.py:62`              |
| DELETE | `/v1/merchant/shopify/{shop_id}`                                    | merchant (Clerk)                              | —      | `routers/merchant/shopify.py:139`             |
| PUT    | `/v1/merchant/shopify/{shop_id}/pickup`                             | merchant (Clerk)                              | —      | `routers/merchant/shopify.py:124`             |
| GET    | `/v1/merchant/standing-orders`                                      | merchant (Clerk)                              | —      | `routers/merchant/standing_orders.py:26`      |
| POST   | `/v1/merchant/standing-orders`                                      | merchant (Clerk)                              | —      | `routers/merchant/standing_orders.py:45`      |
| DELETE | `/v1/merchant/standing-orders/{standing_order_id}`                  | merchant (Clerk)                              | —      | `routers/merchant/standing_orders.py:76`      |
| GET    | `/v1/merchant/support/knowledge-base`                               | merchant (Clerk)                              | —      | `routers/merchant/support_claims.py:58`       |
| GET    | `/v1/merchant/support/tickets`                                      | merchant (Clerk)                              | —      | `routers/merchant/support_claims.py:22`       |
| POST   | `/v1/merchant/support/tickets`                                      | merchant (Clerk)                              | —      | `routers/merchant/support_claims.py:45`       |
| GET    | `/v1/merchant/support/tickets/{ticket_id}`                          | merchant (Clerk)                              | —      | `routers/merchant/support_claims.py:32`       |
| GET    | `/v1/merchant/team`                                                 | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:271`        |
| GET    | `/v1/merchant/team/activity`                                        | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:239`        |
| GET    | `/v1/merchant/team/overview`                                        | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:231`        |
| GET    | `/v1/merchant/team/roles`                                           | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:248`        |
| POST   | `/v1/merchant/team/seats`                                           | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:279`        |
| GET    | `/v1/merchant/team/two-factor`                                      | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:255`        |
| PATCH  | `/v1/merchant/team/two-factor`                                      | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:262`        |
| DELETE | `/v1/merchant/team/{user_id}`                                       | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:290`        |
| PATCH  | `/v1/merchant/team/{user_id}`                                       | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:299`        |
| PATCH  | `/v1/merchant/team/{user_id}/role`                                  | merchant (Clerk)                              | —      | `routers/merchant/profile_team.py:310`        |
| GET    | `/v1/merchant/track/{tracking_number}`                              | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:238`     |
| GET    | `/v1/merchant/tracking/dashboard`                                   | merchant (Clerk), get_settings                | —      | `routers/merchant/orders_tracking.py:231`     |
| GET    | `/v1/merchant/webhooks`                                             | merchant (Clerk)                              | —      | `routers/merchant/integrations.py:81`         |
| POST   | `/v1/merchant/webhooks`                                             | merchant (Clerk), get_settings                | —      | `routers/merchant/integrations.py:86`         |

### driver

| Method | Path                                                                    | Auth                                                      | Module | Handler                                    |
| ------ | ----------------------------------------------------------------------- | --------------------------------------------------------- | ------ | ------------------------------------------ |
| GET    | `/driver-api/v1/attachments/{attachment_id}/file`                       | driver (Clerk)                                            | —      | `routers/booking_attachments/driver.py:33` |
| POST   | `/driver-api/v1/attachments/{attachment_id}/link`                       | driver (Clerk)                                            | —      | `routers/booking_attachments/driver.py:41` |
| POST   | `/driver-api/v1/attachments/{attachment_id}/shown`                      | driver (Clerk)                                            | —      | `routers/booking_attachments/driver.py:58` |
| GET    | `/driver-api/v1/auth/dev-drivers`                                       | get_settings                                              | —      | `routers/driver/auth_dev.py:36`            |
| POST   | `/driver-api/v1/auth/dev-login`                                         | get_settings                                              | —      | `routers/driver/auth_dev.py:22`            |
| POST   | `/driver-api/v1/availability`                                           | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/dashboard.py:147`          |
| GET    | `/driver-api/v1/availability/schedule`                                  | driver (Clerk)                                            | —      | `routers/driver/timesheets.py:23`          |
| PUT    | `/driver-api/v1/availability/schedule`                                  | driver (Clerk)                                            | —      | `routers/driver/timesheets.py:29`          |
| GET    | `/driver-api/v1/bonuses`                                                | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:119`          |
| POST   | `/driver-api/v1/bonuses/{bonus_id}/claim`                               | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:124`          |
| GET    | `/driver-api/v1/communications`                                         | driver (Clerk)                                            | —      | `routers/driver/communications.py:58`      |
| GET    | `/driver-api/v1/communications/notifications`                           | driver (Clerk)                                            | —      | `routers/driver/communications.py:65`      |
| GET    | `/driver-api/v1/communications/notifications/history`                   | driver (Clerk)                                            | —      | `routers/driver/communications.py:105`     |
| POST   | `/driver-api/v1/communications/notifications/mark-all-read`             | driver (Clerk)                                            | —      | `routers/driver/communications.py:96`      |
| POST   | `/driver-api/v1/communications/notifications/{notification_id}/archive` | driver (Clerk)                                            | —      | `routers/driver/communications.py:84`      |
| POST   | `/driver-api/v1/communications/notifications/{notification_id}/read`    | driver (Clerk)                                            | —      | `routers/driver/communications.py:72`      |
| GET    | `/driver-api/v1/communications/offline`                                 | driver (Clerk)                                            | —      | `routers/driver/communications.py:113`     |
| POST   | `/driver-api/v1/communications/offline/retry`                           | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/communications.py:120`     |
| POST   | `/driver-api/v1/communications/offline/{action_id}/discard`             | driver (Clerk)                                            | —      | `routers/driver/communications.py:153`     |
| POST   | `/driver-api/v1/communications/offline/{action_id}/retry`               | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/communications.py:135`     |
| GET    | `/driver-api/v1/dashboard`                                              | staff session                                             | —      | `routers/notifications_admin.py:28`        |
| GET    | `/driver-api/v1/dispatch/orders/{order_id}/checklist`                   | driver (Clerk), driver (approved), require_assigned_order | —      | `routers/driver/dispatch_route.py:93`      |
| GET    | `/driver-api/v1/dispatch/orders/{order_id}/contact`                     | driver (Clerk), driver (approved), require_assigned_order | —      | `routers/driver/dispatch_route.py:135`     |
| GET    | `/driver-api/v1/dispatch/route`                                         | driver (Clerk), driver (approved)                         | —      | `routers/driver/dispatch_route.py:48`      |
| POST   | `/driver-api/v1/dispatch/stops/checkin`                                 | driver (Clerk), driver (approved)                         | —      | `routers/driver/dispatch_route.py:57`      |
| GET    | `/driver-api/v1/documents`                                              | driver (Clerk)                                            | —      | `routers/driver/shift.py:28`               |
| POST   | `/driver-api/v1/documents`                                              | driver (Clerk)                                            | —      | `routers/driver/shift.py:37`               |
| GET    | `/driver-api/v1/earnings`                                               | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:49`           |
| GET    | `/driver-api/v1/earnings/statements`                                    | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:66`           |
| GET    | `/driver-api/v1/earnings/statements/{statement_id}`                     | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:73`           |
| GET    | `/driver-api/v1/earnings/statements/{statement_id}/download`            | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:84`           |
| GET    | `/driver-api/v1/earnings/today`                                         | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:56`           |
| POST   | `/driver-api/v1/emergency`                                              | driver (Clerk)                                            | —      | `routers/driver/support.py:123`            |
| POST   | `/driver-api/v1/gps-consent`                                            | driver (Clerk)                                            | —      | `routers/driver/gps.py:28`                 |
| GET    | `/driver-api/v1/gps-status`                                             | driver (Clerk)                                            | —      | `routers/driver/gps.py:20`                 |
| GET    | `/driver-api/v1/incidents`                                              | driver (Clerk)                                            | —      | `routers/driver/support.py:102`            |
| POST   | `/driver-api/v1/incidents`                                              | driver (Clerk)                                            | —      | `routers/driver/support.py:107`            |
| GET    | `/driver-api/v1/insurance`                                              | driver (Clerk)                                            | —      | `routers/driver/shift.py:23`               |
| GET    | `/driver-api/v1/jobs`                                                   | driver (Clerk), get_settings                              | —      | `routers/driver/jobs.py:62`                |
| GET    | `/driver-api/v1/jobs/history`                                           | driver (Clerk), get_settings                              | —      | `routers/driver/jobs.py:158`               |
| POST   | `/driver-api/v1/jobs/optimize`                                          | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:71`                |
| GET    | `/driver-api/v1/jobs/optimize/runs/{run_id}`                            | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:87`                |
| POST   | `/driver-api/v1/jobs/optimize/runs/{run_id}/accept`                     | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:119`               |
| POST   | `/driver-api/v1/jobs/optimize/undo`                                     | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:147`               |
| GET    | `/driver-api/v1/jobs/{order_id}`                                        | driver (Clerk), get_settings                              | —      | `routers/driver/jobs.py:167`               |
| POST   | `/driver-api/v1/location`                                               | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:30`                |
| GET    | `/driver-api/v1/me`                                                     | driver (Clerk)                                            | —      | `routers/driver/profile.py:21`             |
| GET    | `/driver-api/v1/me/profile`                                             | driver (Clerk)                                            | —      | `routers/driver/me_profile.py:18`          |
| PATCH  | `/driver-api/v1/me/profile`                                             | driver (Clerk)                                            | —      | `routers/driver/me_profile.py:23`          |
| POST   | `/driver-api/v1/me/profile/sync-identity`                               | _bearer, get_settings                                     | —      | `routers/driver/me_profile.py:39`          |
| GET    | `/driver-api/v1/monitoring-policy`                                      | driver (Clerk)                                            | —      | `routers/driver/gps.py:45`                 |
| POST   | `/driver-api/v1/monitoring-policy/ack`                                  | driver (Clerk)                                            | —      | `routers/driver/gps.py:53`                 |
| GET    | `/driver-api/v1/navigation/route`                                       | driver (Clerk), get_settings                              | —      | `routers/driver/navigation_pod.py:62`      |
| GET    | `/driver-api/v1/navigation/session`                                     | driver (Clerk), get_settings                              | —      | `routers/driver/navigation_pod.py:41`      |
| GET    | `/driver-api/v1/offers`                                                 | driver (Clerk), driver (approved)                         | —      | `routers/driver/assignment.py:71`          |
| POST   | `/driver-api/v1/offers/{offer_id}/accept`                               | driver (Clerk)                                            | —      | `routers/driver/assignment.py:89`          |
| POST   | `/driver-api/v1/offers/{offer_id}/decline`                              | driver (Clerk)                                            | —      | `routers/driver/assignment.py:97`          |
| GET    | `/driver-api/v1/offline/pending`                                        | driver (Clerk)                                            | —      | `routers/driver/navigation_pod.py:236`     |
| POST   | `/driver-api/v1/offline/queue`                                          | driver (Clerk)                                            | —      | `routers/driver/navigation_pod.py:221`     |
| POST   | `/driver-api/v1/offline/sync`                                           | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/navigation_pod.py:241`     |
| GET    | `/driver-api/v1/onboarding`                                             | driver (Clerk), get_settings                              | —      | `routers/driver/profile.py:33`             |
| POST   | `/driver-api/v1/orders/{order_id}/accept`                               | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/assignment.py:23`          |
| GET    | `/driver-api/v1/orders/{order_id}/attachments`                          | driver (Clerk)                                            | —      | `routers/booking_attachments/driver.py:28` |
| GET    | `/driver-api/v1/orders/{order_id}/navigation`                           | driver (Clerk), get_settings                              | —      | `routers/driver/navigation_pod.py:78`      |
| POST   | `/driver-api/v1/orders/{order_id}/otp`                                  | driver (Clerk), driver (approved)                         | —      | `routers/driver/navigation_pod.py:205`     |
| POST   | `/driver-api/v1/orders/{order_id}/packages/scan`                        | driver (Clerk), driver (approved), require_assigned_order | —      | `routers/driver/jobs.py:272`               |
| POST   | `/driver-api/v1/orders/{order_id}/packages/{package_id}/missing`        | driver (Clerk), driver (approved), require_assigned_order | —      | `routers/driver/jobs.py:323`               |
| GET    | `/driver-api/v1/orders/{order_id}/pickup-checklist`                     | driver (Clerk), driver (approved), require_assigned_order | —      | `routers/driver/jobs.py:303`               |
| POST   | `/driver-api/v1/orders/{order_id}/reject`                               | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/assignment.py:41`          |
| GET    | `/driver-api/v1/performance`                                            | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:137`          |
| POST   | `/driver-api/v1/privacy/request`                                        | driver (Clerk)                                            | —      | `routers/driver/shift.py:109`              |
| GET    | `/driver-api/v1/profile`                                                | driver (Clerk)                                            | —      | `routers/driver/profile.py:45`             |
| POST   | `/driver-api/v1/profile/vehicle-photos`                                 | driver (Clerk)                                            | —      | `routers/driver/shift.py:55`               |
| POST   | `/driver-api/v1/push/register`                                          | driver (Clerk)                                            | —      | `routers/driver/communications.py:25`      |
| POST   | `/driver-api/v1/push/unregister`                                        | driver (Clerk)                                            | —      | `routers/driver/communications.py:44`      |
| GET    | `/driver-api/v1/ratings`                                                | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:142`          |
| GET    | `/driver-api/v1/routes/assigned`                                        | driver (Clerk)                                            | —      | `routers/driver/jobs.py:180`               |
| GET    | `/driver-api/v1/routes/{route_id}/earnings`                             | driver (Clerk)                                            | —      | `routers/driver/jobs.py:212`               |
| POST   | `/driver-api/v1/routes/{route_id}/start`                                | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:190`               |
| GET    | `/driver-api/v1/routes/{route_id}/stops`                                | driver (Clerk), get_settings                              | —      | `routers/driver/jobs.py:201`               |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/arrive`               | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:220`               |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/deliver`              | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:240`               |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/exception`            | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/jobs.py:353`               |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-barcode`          | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/navigation_pod.py:159`     |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-complete`         | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/navigation_pod.py:180`     |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-id-check`         | driver (Clerk), driver (approved)                         | —      | `routers/driver/navigation_pod.py:134`     |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-photo`            | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/navigation_pod.py:92`      |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-signature`        | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/navigation_pod.py:113`     |
| POST   | `/driver-api/v1/routes/{route_id}/stops/{stop_id}/start`                | driver (Clerk), driver (approved)                         | —      | `routers/driver/delivery_leg.py:19`        |
| GET    | `/driver-api/v1/scan/history`                                           | driver (Clerk), driver (approved)                         | —      | `routers/driver/scan.py:43`                |
| POST   | `/driver-api/v1/scan/lookup`                                            | driver (Clerk), driver (approved)                         | —      | `routers/driver/scan.py:29`                |
| GET    | `/driver-api/v1/settings`                                               | driver (Clerk)                                            | —      | `routers/driver/shift.py:88`               |
| PUT    | `/driver-api/v1/settings`                                               | driver (Clerk)                                            | —      | `routers/driver/shift.py:95`               |
| GET    | `/driver-api/v1/shift`                                                  | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:174`          |
| POST   | `/driver-api/v1/shift/break`                                            | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/dashboard.py:218`          |
| POST   | `/driver-api/v1/shift/end`                                              | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/dashboard.py:204`          |
| POST   | `/driver-api/v1/shift/resume`                                           | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/dashboard.py:235`          |
| POST   | `/driver-api/v1/shift/start`                                            | driver (Clerk), get_settings, driver (approved)           | —      | `routers/driver/dashboard.py:181`          |
| GET    | `/driver-api/v1/support`                                                | driver (Clerk)                                            | —      | `routers/driver/support.py:22`             |
| POST   | `/driver-api/v1/support`                                                | driver (Clerk)                                            | —      | `routers/driver/support.py:82`             |
| GET    | `/driver-api/v1/support/claims`                                         | driver (Clerk)                                            | —      | `routers/driver/support.py:39`             |
| POST   | `/driver-api/v1/support/claims`                                         | driver (Clerk)                                            | —      | `routers/driver/support.py:44`             |
| GET    | `/driver-api/v1/support/emergency-contact`                              | driver (Clerk)                                            | —      | `routers/driver/support.py:62`             |
| PUT    | `/driver-api/v1/support/emergency-contact`                              | driver (Clerk)                                            | —      | `routers/driver/support.py:67`             |
| GET    | `/driver-api/v1/support/hub`                                            | driver (Clerk)                                            | —      | `routers/driver/support.py:27`             |
| GET    | `/driver-api/v1/support/knowledge-base`                                 | merchant (Clerk)                                          | —      | `routers/merchant/support_claims.py:58`    |
| GET    | `/driver-api/v1/timesheets`                                             | driver (Clerk)                                            | —      | `routers/driver/timesheets.py:14`          |
| GET    | `/driver-api/v1/training`                                               | driver (Clerk)                                            | —      | `routers/driver/shift.py:67`               |
| POST   | `/driver-api/v1/training/{module_id}/complete`                          | driver (Clerk)                                            | —      | `routers/driver/shift.py:72`               |
| GET    | `/driver-api/v1/vehicle`                                                | driver (Clerk)                                            | —      | `routers/driver/shift.py:18`               |
| GET    | `/driver-api/v1/verification/abstract`                                  | driver (Clerk), get_settings                              | —      | `routers/driver/verification.py:141`       |
| POST   | `/driver-api/v1/verification/abstract/submit`                           | driver (Clerk), get_settings                              | —      | `routers/driver/verification.py:148`       |
| GET    | `/driver-api/v1/verification/background`                                | driver (Clerk), get_settings                              | —      | `routers/driver/verification.py:87`        |
| POST   | `/driver-api/v1/verification/background/mock-complete`                  | driver (Clerk), get_settings, require_local_mock          | —      | `routers/driver/verification.py:109`       |
| POST   | `/driver-api/v1/verification/background/start`                          | driver (Clerk), get_settings                              | —      | `routers/driver/verification.py:95`        |
| GET    | `/driver-api/v1/verification/identity`                                  | driver (Clerk), get_settings                              | —      | `routers/driver/verification.py:38`        |
| POST   | `/driver-api/v1/verification/identity/mock-complete`                    | driver (Clerk), get_settings, require_local_mock          | —      | `routers/driver/verification.py:65`        |
| POST   | `/driver-api/v1/verification/identity/session`                          | driver (Clerk), get_settings                              | —      | `routers/driver/verification.py:45`        |
| GET    | `/driver-api/v1/wallet`                                                 | driver (Clerk)                                            | —      | `routers/driver/dashboard.py:99`           |

### other /v1

| Method | Path                                                         | Auth                                     | Module | Handler                                    |
| ------ | ------------------------------------------------------------ | ---------------------------------------- | ------ | ------------------------------------------ |
| GET    | `/v1/attachment-links/{token}`                               | NONE                                     | —      | `routers/booking_attachments/driver.py:52` |
| GET    | `/v1/auth/customer/onboarding`                               | Clerk JWT, get_settings                  | —      | `routers/auth.py:136`                      |
| POST   | `/v1/auth/impersonation/end`                                 | NONE                                     | —      | `routers/auth_staff.py:221`                |
| GET    | `/v1/auth/impersonation/me`                                  | NONE                                     | —      | `routers/auth_staff.py:208`                |
| GET    | `/v1/auth/me`                                                | authenticated                            | —      | `routers/auth.py:83`                       |
| GET    | `/v1/auth/merchant/onboarding`                               | Clerk JWT, get_settings                  | —      | `routers/auth.py:100`                      |
| PATCH  | `/v1/auth/merchant/onboarding/profile`                       | Clerk JWT, get_settings                  | —      | `routers/auth.py:125`                      |
| PATCH  | `/v1/auth/merchant/onboarding/vertical`                      | Clerk JWT, get_settings                  | —      | `routers/auth.py:110`                      |
| GET    | `/v1/auth/session-context`                                   | authenticated                            | —      | `routers/auth.py:92`                       |
| GET    | `/v1/auth/staff/enrollment/{token}`                          | NONE                                     | —      | `routers/auth_staff.py:34`                 |
| POST   | `/v1/auth/staff/enrollment/{token}/activate`                 | get_settings                             | —      | `routers/auth_staff.py:41`                 |
| POST   | `/v1/auth/staff/local-session`                               | get_settings                             | —      | `routers/auth_staff.py:65`                 |
| POST   | `/v1/auth/staff/login`                                       | get_settings                             | —      | `routers/auth_staff.py:153`                |
| POST   | `/v1/auth/staff/login-request`                               | get_settings                             | —      | `routers/auth_staff.py:91`                 |
| POST   | `/v1/auth/staff/logout`                                      | get_settings                             | —      | `routers/auth_staff.py:192`                |
| POST   | `/v1/auth/staff/passkey/login/options`                       | get_settings                             | —      | `routers/auth_staff.py:140`                |
| POST   | `/v1/auth/staff/passkey/register/options`                    | staff session, get_settings              | —      | `routers/auth_staff.py:110`                |
| POST   | `/v1/auth/staff/passkey/register/verify`                     | staff session, get_settings              | —      | `routers/auth_staff.py:124`                |
| GET    | `/v1/auth/staff/passkeys`                                    | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:120`       |
| DELETE | `/v1/auth/staff/passkeys/{credential_id}`                    | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:133`       |
| GET    | `/v1/auth/staff/security-status`                             | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:47`        |
| GET    | `/v1/auth/staff/sessions`                                    | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:32`        |
| POST   | `/v1/auth/staff/sessions/revoke-others`                      | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:103`       |
| DELETE | `/v1/auth/staff/sessions/{session_id}`                       | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:77`        |
| POST   | `/v1/auth/staff/step-up`                                     | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:164`       |
| POST   | `/v1/auth/staff/step-up/options`                             | staff session, get_settings              | —      | `routers/auth_staff_sessions.py:150`       |
| GET    | `/v1/booking-catalog`                                        | NONE                                     | —      | `routers/quotes.py:77`                     |
| POST   | `/v1/booking-drafts`                                         | get_settings                             | —      | `routers/booking_drafts.py:65`             |
| GET    | `/v1/booking-drafts/active`                                  | get_optional_clerk_user_id, get_settings | —      | `routers/booking_drafts.py:81`             |
| GET    | `/v1/booking-drafts/{draft_id}`                              | get_optional_clerk_user_id, get_settings | —      | `routers/booking_drafts.py:98`             |
| PATCH  | `/v1/booking-drafts/{draft_id}`                              | get_optional_clerk_user_id, get_settings | —      | `routers/booking_drafts.py:117`            |
| POST   | `/v1/booking-drafts/{draft_id}/cancel`                       | get_optional_clerk_user_id, get_settings | —      | `routers/booking_drafts.py:139`            |
| POST   | `/v1/bookings`                                               | Clerk JWT, get_settings                  | —      | `routers/quotes.py:182`                    |
| GET    | `/v1/bookings/confirmation`                                  | NONE                                     | —      | `routers/quotes.py:63`                     |
| POST   | `/v1/bookings/mock-complete`                                 | get_settings                             | —      | `routers/quotes.py:227`                    |
| POST   | `/v1/bookings/sync-checkout`                                 | get_settings                             | —      | `routers/quotes.py:245`                    |
| GET    | `/v1/delivery-manage/{tracking_number}`                      | get_settings                             | —      | `routers/customer_experience.py:60`        |
| GET    | `/v1/delivery-manage/{tracking_number}/actions`              | get_settings                             | —      | `routers/customer_fast.py:98`              |
| POST   | `/v1/delivery-manage/{tracking_number}/cancel`               | get_settings                             | —      | `routers/customer_fast.py:108`             |
| POST   | `/v1/delivery-manage/{tracking_number}/instructions`         | get_settings                             | —      | `routers/customer_experience.py:81`        |
| GET    | `/v1/delivery-manage/{tracking_number}/pod`                  | get_settings                             | —      | `routers/customer_experience.py:92`        |
| POST   | `/v1/delivery-manage/{tracking_number}/problem`              | get_settings                             | —      | `routers/customer_fast.py:299`             |
| POST   | `/v1/delivery-manage/{tracking_number}/rating`               | get_settings                             | —      | `routers/customer_fast.py:118`             |
| POST   | `/v1/delivery-manage/{tracking_number}/schedule`             | get_settings                             | —      | `routers/customer_experience.py:70`        |
| POST   | `/v1/email-preferences`                                      | get_settings                             | —      | `routers/customer_fast.py:149`             |
| POST   | `/v1/email-preferences/delete-request`                       | get_settings                             | —      | `routers/customer_fast.py:170`             |
| POST   | `/v1/email-preferences/read`                                 | get_settings                             | —      | `routers/customer_fast.py:139`             |
| POST   | `/v1/email-preferences/unsubscribe`                          | get_settings                             | —      | `routers/customer_fast.py:160`             |
| POST   | `/v1/express/checkout`                                       | get_settings                             | —      | `routers/customer_fast.py:77`              |
| GET    | `/v1/express/confirmation`                                   | get_settings                             | —      | `routers/customer_fast.py:88`              |
| POST   | `/v1/express/send-again`                                     | get_settings                             | —      | `routers/customer_fast.py:129`             |
| GET    | `/v1/geo/autocomplete`                                       | NONE                                     | —      | `routers/geo.py:265`                       |
| GET    | `/v1/geo/place`                                              | NONE                                     | —      | `routers/geo.py:300`                       |
| POST   | `/v1/integrations/shopify/carrier-service/rates`             | get_settings                             | —      | `routers/shopify.py:165`                   |
| POST   | `/v1/integrations/shopify/fs/fulfillment_order_notification` | get_settings                             | —      | `routers/shopify.py:133`                   |
| POST   | `/v1/integrations/shopify/fulfillment-order-notification`    | get_settings                             | —      | `routers/shopify.py:133`                   |
| GET    | `/v1/integrations/shopify/onboarding`                        | get_settings                             | —      | `routers/shopify.py:260`                   |
| POST   | `/v1/integrations/shopify/onboarding/go-live`                | get_settings                             | —      | `routers/shopify.py:276`                   |
| GET    | `/v1/integrations/shopify/route-pricing`                     | get_settings                             | —      | `routers/shopify_route_pricing.py:34`      |
| POST   | `/v1/integrations/shopify/route-pricing`                     | get_settings                             | —      | `routers/shopify_route_pricing.py:45`      |
| POST   | `/v1/integrations/shopify/session`                           | get_settings                             | —      | `routers/shopify.py:68`                    |
| POST   | `/v1/integrations/shopify/webhooks`                          | get_settings                             | —      | `routers/shopify.py:92`                    |
| POST   | `/v1/notifications/devices/register`                         | get_notification_user                    | —      | `routers/notifications.py:64`              |
| DELETE | `/v1/notifications/devices/{device_id}`                      | get_notification_user                    | —      | `routers/notifications.py:90`              |
| GET    | `/v1/notifications/inbox`                                    | get_notification_user                    | —      | `routers/notifications.py:103`             |
| GET    | `/v1/notifications/inbox/history`                            | get_notification_user                    | —      | `routers/notifications.py:125`             |
| POST   | `/v1/notifications/inbox/mark-all-read`                      | get_notification_user                    | —      | `routers/notifications.py:160`             |
| POST   | `/v1/notifications/inbox/{notification_id}/archive`          | get_notification_user                    | —      | `routers/notifications.py:147`             |
| POST   | `/v1/notifications/inbox/{notification_id}/read`             | get_notification_user                    | —      | `routers/notifications.py:134`             |
| GET    | `/v1/notifications/me/preferences`                           | get_notification_user                    | —      | `routers/notifications.py:216`             |
| PUT    | `/v1/notifications/me/preferences`                           | get_notification_user                    | —      | `routers/notifications.py:228`             |
| GET    | `/v1/notifications/preferences`                              | get_notification_user                    | —      | `routers/notifications.py:170`             |
| PATCH  | `/v1/notifications/preferences`                              | get_notification_user                    | —      | `routers/notifications.py:190`             |
| GET    | `/v1/notifications/settings`                                 | get_notification_user                    | —      | `routers/notifications.py:243`             |
| PATCH  | `/v1/notifications/settings`                                 | get_notification_user                    | —      | `routers/notifications.py:253`             |
| GET    | `/v1/oauth/.well-known/oauth-authorization-server`           | get_settings                             | —      | `routers/oauth.py:36`                      |
| GET    | `/v1/oauth/authorize`                                        | merchant (Clerk), get_settings           | —      | `routers/oauth.py:41`                      |
| POST   | `/v1/oauth/authorize`                                        | merchant (Clerk), get_settings           | —      | `routers/oauth.py:73`                      |
| POST   | `/v1/oauth/token`                                            | get_settings                             | —      | `routers/oauth.py:95`                      |
| GET    | `/v1/orders/{tracking_number}`                               | get_optional_clerk_user_id               | —      | `routers/orders.py:15`                     |
| GET    | `/v1/orders/{tracking_number}/experience`                    | get_optional_clerk_user_id, get_settings | —      | `routers/customer_experience.py:48`        |
| GET    | `/v1/orders/{tracking_number}/tracking`                      | get_optional_clerk_user_id, get_settings | —      | `routers/orders.py:27`                     |
| POST   | `/v1/payments/retry`                                         | Clerk JWT, get_settings                  | —      | `routers/payments.py:15`                   |
| POST   | `/v1/pricing/components/distance`                            | staff session                            | —      | `routers/pricing_components.py:76`         |
| POST   | `/v1/pricing/components/fsa`                                 | staff session                            | —      | `routers/pricing_components.py:157`        |
| GET    | `/v1/pricing/components/fsa/coverage-gap`                    | staff session                            | —      | `routers/pricing_components.py:191`        |
| GET    | `/v1/pricing/components/fsa/rates`                           | staff session                            | —      | `routers/pricing_components.py:181`        |
| POST   | `/v1/pricing/components/fsa/rates`                           | staff session                            | —      | `routers/pricing_components.py:201`        |
| POST   | `/v1/pricing/components/fsa/rates/bulk`                      | staff session                            | —      | `routers/pricing_components.py:211`        |
| DELETE | `/v1/pricing/components/fsa/rates/{rate_id}`                 | staff session                            | —      | `routers/pricing_components.py:230`        |
| PATCH  | `/v1/pricing/components/fsa/rates/{rate_id}`                 | staff session                            | —      | `routers/pricing_components.py:220`        |
| POST   | `/v1/pricing/components/location`                            | staff session                            | —      | `routers/pricing_components.py:105`        |
| POST   | `/v1/pricing/components/size-weight`                         | staff session                            | —      | `routers/pricing_components.py:122`        |
| POST   | `/v1/pricing/components/stops`                               | staff session                            | —      | `routers/pricing_components.py:90`         |
| POST   | `/v1/pricing/simulate`                                       | staff session                            | —      | `routers/pricing_admin.py:73`              |
| POST   | `/v1/quotes`                                                 | get_settings                             | —      | `routers/quotes.py:134`                    |
| POST   | `/v1/quotes/preview`                                         | get_settings                             | —      | `routers/quotes.py:150`                    |
| GET    | `/v1/quotes/{quote_id}`                                      | NONE                                     | —      | `routers/quotes.py:164`                    |
| POST   | `/v1/security/audit-events`                                  | get_settings                             | —      | `routers/security.py:41`                   |

### public

| Method | Path                                   | Auth                                | Module | Handler                           |
| ------ | -------------------------------------- | ----------------------------------- | ------ | --------------------------------- |
| GET    | `/v1/public/blog/authors`              | NONE                                | —      | `routers/public_blog.py:44`       |
| GET    | `/v1/public/blog/authors/{author_id}`  | NONE                                | —      | `routers/public_blog.py:53`       |
| GET    | `/v1/public/blog/media/{filename}`     | NONE                                | —      | `routers/public_blog.py:122`      |
| GET    | `/v1/public/blog/posts`                | NONE                                | —      | `routers/public_blog.py:63`       |
| GET    | `/v1/public/blog/posts/{slug}`         | NONE                                | —      | `routers/public_blog.py:110`      |
| GET    | `/v1/public/blog/posts/{slug}/preview` | get_settings                        | —      | `routers/public_blog.py:90`       |
| POST   | `/v1/public/calculator-leads`          | get_settings                        | —      | `routers/public_marketing.py:62`  |
| POST   | `/v1/public/estimate`                  | get_settings                        | —      | `routers/public_marketing.py:35`  |
| POST   | `/v1/public/guide/appointments`        | get_settings                        | —      | `routers/public_guide.py:235`     |
| POST   | `/v1/public/guide/leads`               | get_settings                        | —      | `routers/public_guide.py:59`      |
| GET    | `/v1/public/guide/slots`               | get_settings                        | —      | `routers/public_guide.py:221`     |
| POST   | `/v1/public/guide/transcript`          | get_settings                        | —      | `routers/public_guide.py:174`     |
| POST   | `/v1/public/inquiries`                 | get_settings                        | —      | `routers/public_inquiries.py:121` |
| POST   | `/v1/public/leads/engagement`          | get_settings                        | —      | `routers/public_inquiries.py:304` |
| POST   | `/v1/public/leads/unsubscribe`         | get_settings                        | —      | `routers/public_inquiries.py:264` |
| POST   | `/v1/public/leads/webhooks/google`     | get_settings                        | —      | `routers/lead_webhooks.py:117`    |
| POST   | `/v1/public/leads/webhooks/linkedin`   | get_settings, require_social_secret | —      | `routers/lead_webhooks.py:179`    |
| GET    | `/v1/public/leads/webhooks/meta`       | signature, get_settings             | —      | `routers/lead_webhooks.py:72`     |
| POST   | `/v1/public/leads/webhooks/meta`       | get_settings, signature             | —      | `routers/lead_webhooks.py:90`     |
| POST   | `/v1/public/leads/webhooks/x`          | get_settings, require_social_secret | —      | `routers/lead_webhooks.py:192`    |
| POST   | `/v1/public/leads/webhooks/youtube`    | get_settings, require_social_secret | —      | `routers/lead_webhooks.py:205`    |
| POST   | `/v1/public/mail/inbound`              | get_settings                        | —      | `routers/email_inbound.py:21`     |
| POST   | `/v1/public/mail/zeptomail`            | NONE                                | —      | `routers/zeptomail_webhook.py:23` |
| GET    | `/v1/public/marketing-config`          | NONE                                | —      | `routers/public_marketing.py:29`  |
| POST   | `/v1/public/newsletter/confirm`        | NONE                                | —      | `routers/public_newsletter.py:65` |
| POST   | `/v1/public/newsletter/subscribe`      | get_settings                        | —      | `routers/public_newsletter.py:24` |
| GET    | `/v1/public/region`                    | NONE                                | —      | `routers/admin/compliance.py:50`  |

### customer

| Method | Path                                                        | Auth                                                                     | Module | Handler                                       |
| ------ | ----------------------------------------------------------- | ------------------------------------------------------------------------ | ------ | --------------------------------------------- |
| GET    | `/v1/customers/me/address-suggestions`                      | Clerk JWT, get_settings                                                  | —      | `routers/customer_fast.py:249`                |
| GET    | `/v1/customers/me/addresses`                                | Clerk JWT, get_settings                                                  | —      | `routers/customer_fast.py:238`                |
| POST   | `/v1/customers/me/addresses`                                | Clerk JWT, get_settings                                                  | —      | `routers/customer_fast.py:261`                |
| DELETE | `/v1/customers/me/addresses/{address_id}`                   | Clerk JWT, get_settings                                                  | —      | `routers/customer_fast.py:273`                |
| POST   | `/v1/customers/me/attachments/suggest`                      | Clerk JWT                                                                | —      | `routers/booking_attachments/customer.py:29`  |
| DELETE | `/v1/customers/me/attachments/{attachment_id}`              | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/booking_attachments/customer.py:105` |
| PATCH  | `/v1/customers/me/attachments/{attachment_id}`              | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/booking_attachments/customer.py:84`  |
| GET    | `/v1/customers/me/attachments/{attachment_id}/file`         | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/booking_attachments/customer.py:125` |
| GET    | `/v1/customers/me/dashboard`                                | Clerk JWT, get_settings, customer (Clerk), require_customer_portal_ready | —      | `routers/customers.py:49`                     |
| GET    | `/v1/customers/me/deliveries`                               | Clerk JWT, get_settings                                                  | —      | `routers/customer_fast.py:227`                |
| GET    | `/v1/customers/me/invoices`                                 | Clerk JWT, get_settings                                                  | —      | `routers/customers.py:69`                     |
| GET    | `/v1/customers/me/invoices/{invoice_id}`                    | Clerk JWT, get_settings                                                  | —      | `routers/customers.py:81`                     |
| GET    | `/v1/customers/me/invoices/{invoice_id}/pdf`                | Clerk JWT, get_settings                                                  | —      | `routers/customers.py:96`                     |
| GET    | `/v1/customers/me/orders/{order_id}/attachments`            | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/booking_attachments/customer.py:38`  |
| POST   | `/v1/customers/me/orders/{order_id}/attachments`            | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/booking_attachments/customer.py:49`  |
| GET    | `/v1/customers/me/orders/{tracking_number}/driver-position` | Clerk JWT, get_settings                                                  | —      | `routers/customers.py:220`                    |
| POST   | `/v1/customers/me/orders/{tracking_number}/problem`         | Clerk JWT, get_settings                                                  | —      | `routers/customer_fast.py:286`                |
| GET    | `/v1/customers/me/preferences-link`                         | Clerk JWT, get_settings                                                  | —      | `routers/customer_fast.py:312`                |
| POST   | `/v1/customers/me/privacy/delete-request`                   | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/customers.py:210`                    |
| GET    | `/v1/customers/me/privacy/export`                           | Clerk JWT, get_report_db, get_settings, customer (Clerk)                 | —      | `routers/customers.py:200`                    |
| POST   | `/v1/customers/me/rebook/{order_id}`                        | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/customers.py:185`                    |
| GET    | `/v1/customers/me/support`                                  | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/customers.py:134`                    |
| POST   | `/v1/customers/me/support`                                  | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/customers.py:155`                    |
| GET    | `/v1/customers/me/track-link/{tracking_number}`             | Clerk JWT, get_settings, customer (Clerk)                                | —      | `routers/customer_fast.py:179`                |
| GET    | `/v1/customers/{customer_id}/orders`                        | Clerk JWT                                                                | —      | `routers/orders.py:47`                        |

### ops

| Method | Path                 | Auth | Module | Handler                |
| ------ | -------------------- | ---- | ------ | ---------------------- |
| GET    | `/health`            | NONE | —      | `main.py:294`          |
| GET    | `/health/live`       | NONE | —      | `main.py:302`          |
| GET    | `/health/ready`      | NONE | —      | `main.py:308`          |
| GET    | `/health/status`     | NONE | —      | `main.py:314`          |
| GET    | `/internal/health`   | NONE | —      | `gateway/router.py:11` |
| GET    | `/internal/services` | NONE | —      | `gateway/router.py:16` |
| GET    | `/metrics`           | NONE | —      | `main.py:320`          |

### merchant public API (API key)

| Method | Path                                        | Auth                                          | Module | Handler                       |
| ------ | ------------------------------------------- | --------------------------------------------- | ------ | ----------------------------- |
| POST   | `/v1/merchant-api/bookings`                 | merchant API key, get_settings, API key scope | —      | `routers/merchant_api.py:46`  |
| GET    | `/v1/merchant-api/orders`                   | merchant API key, API key scope               | —      | `routers/merchant_api.py:99`  |
| GET    | `/v1/merchant-api/orders/{order_id}`        | merchant API key, API key scope               | —      | `routers/merchant_api.py:117` |
| POST   | `/v1/merchant-api/orders/{order_id}/cancel` | merchant API key, get_settings, API key scope | —      | `routers/merchant_api.py:160` |
| POST   | `/v1/merchant-api/quotes`                   | merchant API key, get_settings, API key scope | —      | `routers/merchant_api.py:195` |
| GET    | `/v1/merchant-api/rate-card`                | merchant API key, API key scope               | —      | `routers/merchant_api.py:183` |
| GET    | `/v1/merchant-api/track/{tracking_number}`  | merchant API key, get_settings, API key scope | —      | `routers/merchant_api.py:134` |

### webhooks

| Method | Path               | Auth         | Module | Handler                  |
| ------ | ------------------ | ------------ | ------ | ------------------------ |
| POST   | `/webhooks/checkr` | get_settings | —      | `routers/webhooks.py:58` |
| POST   | `/webhooks/clerk`  | get_settings | —      | `routers/webhooks.py:40` |
| POST   | `/webhooks/stripe` | get_settings | —      | `routers/webhooks.py:19` |

## Drift: handlers in code but not in the OpenAPI snapshot (20)

Found by AST scan of `@router.<method>` decorators whose function name has no operationId in `docs/api/openapi.json`. Regenerate the snapshot with `apps/api/scripts/export_openapi.py` (not run here: offline `app.openapi()` was blocked by the Shell safety check).

| Handler                            | Method | File:line                                   |
| ---------------------------------- | ------ | ------------------------------------------- |
| `queue`                            | GET    | `routers/notifications_admin.py:34`         |
| `shopify_legacy_browser_entry`     | GET    | `routers/shopify.py:221`                    |
| `shopify_legacy_browser_entry`     | GET    | `routers/shopify.py:221`                    |
| `send_test`                        | POST   | `routers/notifications_admin.py:128`        |
| `unsubscribe_confirm_page`         | GET    | `routers/notifications.py:286`              |
| `unsubscribe_one_click`            | POST   | `routers/notifications.py:304`              |
| `dashboard`                        | GET    | `routers/driver/dashboard.py:25`            |
| `merchant_onboarding`              | GET    | `routers/merchants.py:469`                  |
| `cancel_booking_draft`             | POST   | `routers/admin/booking_drafts.py:157`       |
| `download_my_credit_note_pdf`      | GET    | `routers/customers.py:115`                  |
| `finance_invoice_adjustments`      | GET    | `routers/admin/finance_credit_notes.py:58`  |
| `finance_create_credit_note`       | POST   | `routers/admin/finance_credit_notes.py:71`  |
| `finance_approve_credit_note`      | POST   | `routers/admin/finance_credit_notes.py:89`  |
| `finance_reject_credit_note`       | POST   | `routers/admin/finance_credit_notes.py:106` |
| `finance_retry_credit_note_refund` | POST   | `routers/admin/finance_credit_notes.py:124` |
| `finance_credit_note_pdf`          | GET    | `routers/admin/finance_credit_notes.py:141` |
| `list_orders`                      | GET    | `routers/merchant/orders_tracking.py:101`   |
| `change_tax_registration`          | POST   | `routers/admin/finance_insights.py:86`      |
| `download_credit_note_pdf`         | GET    | `routers/merchant/billing.py:148`           |
| `support_knowledge_base`           | GET    | `routers/driver/support.py:34`              |

## Drift: in snapshot, handler gone

| Method | Path                             | operationId                                                                                                                              |
| ------ | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/v1/admin/finance/credit-notes` | `finance_credit_note…` — removed by commit `56865de9` (2026-10-28 13:12 EDT), replaced by `routers/admin/finance_credit_notes.py:58-141` |
