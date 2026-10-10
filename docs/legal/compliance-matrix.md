> **DRAFT for lawyer review — internal engineering status, October 2026.**

# Compliance Matrix — Canada / Ontario first, EU / Austria settings-ready

Status: ✅ built · 🟡 partial or needs an operational step · ❌ open · ⚙️ settings-ready (EU/AT)

| Requirement                                                                           | Status                  | Where                                                                                                           |
| ------------------------------------------------------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| **PIPEDA** access request (30 days)                                                   | ✅                      | Settings → Privacy Requests (find + JSON download) · `platform/privacy_access.py`                               |
| PIPEDA correction                                                                     | 🟡                      | Edit customer/order in admin; request logged in Settings → Compliance                                           |
| Erasure / withdrawal, keeping tax records                                             | ✅                      | Privacy Requests → preview + erase · `platform/privacy_erasure.py` (invoices kept 6 y CA / 7 y AT)              |
| Request log with 30-day clock                                                         | ✅                      | Settings → Compliance → Data-subject requests (`privacy_requests`)                                              |
| Breach record-keeping (PIPEDA s.10.3) + 72 h clock (GDPR)                             | ✅                      | Settings → Compliance → Breach log (`breach_log`)                                                               |
| Retention schedule                                                                    | ✅                      | Settings → Compliance; GPS 30 d / POD 365 d enforced by the daily worker                                        |
| Privacy Officer named                                                                 | ✅                      | Ravi Chauhan (Owner) accountable; privacy@ / sales@; default in Settings → Compliance                           |
| Privacy Policy                                                                        | 🟡 DRAFT                | `docs/legal/privacy-policy.md` (not published)                                                                  |
| Merchant DPA + subprocessor list                                                      | 🟡 DRAFT                | `docs/legal/merchant-dpa.md`, `docs/legal/subprocessors.md`; also in Settings → Compliance                      |
| Shopify GDPR webhooks (customers/redact, data_request, shop/redact)                   | ✅ (existing)           | `merchant_engine/shopify_privacy.py`                                                                            |
| **CASL** consent + unsubscribe header (RFC 8058 one-click)                            | ✅ (existing)           | `notification_engine/unsubscribe.py`                                                                            |
| CASL sender ID + visible unsubscribe in every commercial email body                   | ✅ new                  | `casl_footer()` in the email delivery path                                                                      |
| CASL consent proof kept                                                               | ✅ (existing)           | Lead consent records (`collaboration_engine/lead_consent.py`)                                                   |
| **Ontario ESA** electronic monitoring policy (25+ employees)                          | 🟡 DRAFT                | `docs/legal/electronic-monitoring-policy.md`; hand it to drivers/staff                                          |
| Driver GPS: on shift only, global/per-driver off switch, live pin deleted             | ✅                      | Settings → Driver GPS · `platform/gps_policy.py`                                                                |
| Driver GPS consent: versioned, timestamped, withdrawable                              | ✅                      | `/driver-api/v1/gps-consent`, portal "I agree"; optional require-consent                                        |
| GPS DPIA / privacy impact note                                                        | ✅                      | Settings → Compliance → DPIA                                                                                    |
| **HST 13%** destination-province, GST/HST no. on invoices, GST34 report               | ✅ (existing, verified) | `billing_engine/tax.py`, `reporting/order_documents.py`, `reporting/tax_report.py`                              |
| GST/HST registration number configured                                                | 🟡 operational          | Finance settings → supplier GST/HST number must be filled in                                                    |
| **AODA** / WCAG 2.0 AA (mandatory at 50+ employees; good practice now)                | ❌ not audited          | Next: automated axe audit of customer, tracking and merchant portal pages                                       |
| French-ready                                                                          | 🟡                      | Customer notification templates have FR; app UI is English only                                                 |
| Privacy by default                                                                    | ✅                      | GPS consent option, cookie default "Essential only", Future/AI toggles off, minimal tracking view for customers |
| Cookie consent (opt-in for non-essential)                                             | ⚙️                      | Customer app banner (en/de) turns on automatically when region requires it; CA = off (no optional cookies used) |
| GDPR Art. 15–22 (access, rectification, erasure, restriction, portability, objection) | ⚙️ / 🟡                 | Access/portability (JSON) and erasure built; restriction/objection logged and handled manually                  |
| GDPR Art. 30 records of processing                                                    | ⚙️ ✅                   | Settings → Compliance                                                                                           |
| EU data residency option                                                              | ⚙️                      | Setting only (`compliance.data_residency`); infrastructure not provisioned                                      |
| AT region profile: EUR, USt 20%, de-AT, BAO 7 y, TKG cookies                          | ⚙️                      | `platform/compliance.py` REGIONS; not wired into pricing/invoices yet                                           |
| Austrian e-invoicing (ebInterface / PEPPOL, UStG §11 fields)                          | ❌                      | Noted in the region profile; build when expanding to AT                                                         |
