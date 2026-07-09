# PIPEDA & Canadian privacy (§11.1.9)

**Type:** CANONICAL  
**Checklist:** §11.1.9 · DD-35  
**Last verified:** 2026-07-09

## Applicability

Porterchain Inc. operates in Ontario, Canada. We process personal information of merchants, drivers, and end-customers (shipment recipients) under **PIPEDA** and applicable provincial law.

## Data categories

| Subject                | Examples                     | Purpose               |
| ---------------------- | ---------------------------- | --------------------- |
| Merchant contacts      | Name, email, billing address | Contract, invoicing   |
| Drivers                | License, insurance docs      | Vetting, compliance   |
| Customers / recipients | Phone, delivery address      | Fulfillment, tracking |

## Individual rights

| Right      | API / process                                                                               |
| ---------- | ------------------------------------------------------------------------------------------- |
| Access     | `GET /v1/merchant/privacy/export` · `GET /v1/customers/me/privacy/export`                   |
| Correction | Merchant settings / support ticket                                                          |
| Deletion   | `POST /v1/merchant/privacy/delete-request` · `POST /v1/customers/me/privacy/delete-request` |
| Complaint  | privacy@porterchain.com (ops queue)                                                         |

Deletion requests receive a **DSR reference** and are fulfilled within **30 days**, subject to legal retention for billing and shipment records.

## Cross-border

- Clerk (auth) and Stripe (payments) may process data in the US — DPAs in place per vendor terms
- Primary application data: Canadian Postgres (dev) / managed Postgres (prod target)

## Breach notification

Follow [RUNBOOK.md](../../RUNBOOK.md) incident section — notify Privacy Officer within 72h of confirmed breach affecting personal information.

## Related

- [SECURITY.md](../../SECURITY.md)
- [docs/compliance/SOC2.md](./SOC2.md)
- Website: `/privacy` page
