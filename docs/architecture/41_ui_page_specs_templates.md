# 41 · UI page specs — Email, PDF and notification templates

Read-only from `notification_engine/templates.py`, `merchant_ops_templates.py`, `customer_experience/templates.py`, `customer_fast/templates.py`, `reporting/*`. Email sent via **ZeptoMail** (allowed paid). No Twilio SMS, no paid WhatsApp: channels are email, web push (`packages/web-push`), Expo push (APNs/FCM), in-app inbox, free WhatsApp click-to-chat (human sends).

## Email design rules

600 px single column, table layout (MJML or React Email), system font stack, logo header, primary `#0a1628` heading, button `#1f56d8` 44 px tall with text link fallback, light only (force light; dark-mode-safe images), plain-text part, `lang` en/fr (account language, bilingual footer), preheader, unsubscribe + CASL sender ID on marketing only, contrast 4.5:1, alt text, no info by colour only, tracking links signed.

## Notification rules

Push: title <= 40 chars, body <= 120, deep link to screen; in-app inbox keeps 90 days; quiet hours 21:00–08:00 Toronto except safety/OTP; user preferences page per category (email-preferences on website). Red-margin alert: **decision open** (who/how) — recommend in-app + push to admins.

## Templates (63 keys from code)

| Template key                 | Audience          | Channels                                     |
| ---------------------------- | ----------------- | -------------------------------------------- |
| `booking_confirmed`          | Customer/merchant | email + push + in-app                        |
| `booking_draft_created`      | Customer/merchant | email + push + in-app                        |
| `checkout_recovery`          | Customer/merchant | email + push + in-app                        |
| `claim_opened`               | Customer/merchant | email + push + in-app                        |
| `claim_updated`              | Customer/merchant | email + push + in-app                        |
| `consignee_tracking`         | Customer/merchant | email + push + in-app                        |
| `delivered`                  | Customer/merchant | email + push + in-app + SMS→push (no Twilio) |
| `delivery_failed`            | Customer/merchant | email + push + in-app                        |
| `delivery_update`            | Customer/merchant | email + push + in-app                        |
| `driver_accepted`            | Driver            | email + push + in-app                        |
| `driver_alert`               | Driver            | email + push + in-app                        |
| `driver_assigned`            | Driver            | email + push + in-app                        |
| `driver_rejected`            | Driver            | email + push + in-app                        |
| `driver_route_changed`       | Driver            | email + push + in-app                        |
| `exception_opened`           | Staff             | email + push + in-app                        |
| `exception_resolved`         | Staff             | email + push + in-app                        |
| `fast_send_again`            | Customer/merchant | email + push + in-app                        |
| `in_transit`                 | Customer/merchant | email + push + in-app                        |
| `invoice_credit_note_issued` | Customer/merchant | email + push + in-app                        |
| `invoice_ready`              | Customer/merchant | email + push + in-app                        |
| `job_assigned`               | Driver            | email + push + in-app                        |
| `job_handoff`                | Driver            | email + push + in-app                        |
| `job_removed`                | Driver            | email + push + in-app                        |
| `lead_new_hot`               | Staff             | email + push + in-app                        |
| `lead_nurture_intro`         | Staff             | email + push + in-app                        |
| `lead_outbound_followup`     | Staff             | email + push + in-app                        |
| `lead_outbound_quote_invite` | Staff             | email + push + in-app                        |
| `lead_sla_escalation`        | Staff             | email + push + in-app                        |
| `lead_staff_reply`           | Staff             | email + push + in-app                        |
| `merchant_approved`          | Merchant          | email + push + in-app                        |
| `merchant_churn_alert`       | Merchant          | email + push + in-app                        |
| `merchant_closed`            | Merchant          | email + push + in-app                        |
| `merchant_credit_hold`       | Merchant          | email + push + in-app                        |
| `merchant_invoice_ready`     | Merchant          | email + push + in-app                        |
| `merchant_suspended`         | Merchant          | email + push + in-app                        |
| `merchant_welcome`           | Merchant          | email + push + in-app                        |
| `near_delivery`              | Customer/merchant | email + push + in-app + SMS→push (no Twilio) |
| `newsletter_confirm`         | Customer/merchant | email + push + in-app                        |
| `notification_health_alert`  | Staff             | email + push + in-app                        |
| `ops_daily_digest`           | Customer/merchant | email + push + in-app                        |
| `order_booked`               | Customer/merchant | email + push + in-app                        |
| `order_cancelled`            | Customer/merchant | email + push + in-app                        |
| `order_created`              | Customer/merchant | email + push + in-app                        |
| `order_delayed`              | Customer/merchant | email + push + in-app                        |
| `order_rescheduled`          | Customer/merchant | email + push + in-app                        |
| `otp`                        | Customer/merchant | email + push + in-app + SMS→push (no Twilio) |
| `parcel_picked_up`           | Customer/merchant | email + push + in-app                        |
| `password_reset`             | Customer/merchant | email + push + in-app                        |
| `payment_failed`             | Customer/merchant | email + push + in-app                        |
| `payment_receipt`            | Customer/merchant | email + push + in-app                        |
| `payment_started`            | Customer/merchant | email + push + in-app                        |
| `pickup_started`             | Customer/merchant | email + push + in-app                        |
| `pod_uploaded`               | Customer/merchant | email + push + in-app                        |
| `quote_created`              | Customer/merchant | email + push + in-app                        |
| `refund_processed`           | Customer/merchant | email + push + in-app                        |
| `sla_breached`               | Staff             | email + push + in-app                        |
| `staff_activate`             | Staff             | email + push + in-app                        |
| `staff_new_login`            | Staff             | email + push + in-app                        |
| `support_reply`              | Customer/merchant | email + push + in-app                        |
| `support_ticket_created`     | Customer/merchant | email + push + in-app                        |
| `system_alert`               | Staff             | email + push + in-app                        |
| `temp_excursion`             | Customer/merchant | email + push + in-app                        |
| `tracking_update`            | Customer/merchant | email + push + in-app                        |

## PDFs (8)

| PDF                        | Source                              | Spec                                                                                                                                                                        |
| -------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Invoice / order documents  | `reporting/order_documents.py`      | Letter/A4, logo, PorterChain legal name + HST no., bill-to, lines, HST, total CAD, Interac instructions (merchant) / Stripe paid stamp (retail), EN/FR, tagged PDF (PDF/UA) |
| Credit note                | `reporting/credit_note_pdf.py`      | Links original invoice no., reason, negative lines, HST reversal                                                                                                            |
| Statement                  | `reporting/statement.py`            | Period, opening/closing balance, aging                                                                                                                                      |
| Thermal label              | `reporting/thermal_pdf.py`          | 4x6 in, barcode/QR tracking, large text                                                                                                                                     |
| Partner job sheet          | `admin_engine/partner_job_sheet.py` | Stops, BOL fields for box truck                                                                                                                                             |
| FSA rate card              | `pricing_engine/fsa_rate_card.py`   | Live rate card version, effective date                                                                                                                                      |
| Driver DPWRA pay statement | planned (A10)                       | Period, hours engaged, pay per job, tips, deductions                                                                                                                        |
| POD certificate            | planned                             | Photo, signature, GPS, time, hash                                                                                                                                           |
