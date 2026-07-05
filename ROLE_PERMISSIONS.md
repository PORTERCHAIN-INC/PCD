# Porterchain — Role Permissions


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05


This file is a **role glossary pointer**. Module and permission matrices live in **[RBAC_MATRIX.md](./RBAC_MATRIX.md)**.

---

## Identity (current)

| Surface | Auth | Authorization source |
| ------- | ---- | -------------------- |
| Website, `apps/customer/` | Clerk | `customers` + enterprise `customer` role |
| Merchant portal | Clerk | `merchant_users.role` (not Clerk org metadata) |
| Admin portal | Clerk | `admin_users.role` |
| Driver portal / mobile | Clerk → Porterchain JWT | `drivers` + driver API scopes |
| Merchant API | API key | Scoped machine auth |
| Fleetbase console | SSO JWT | Ops roles only via [SSO.md](./SSO.md) |

---

## Internal admin roles (glossary)

| Role | Description |
| ---- | ----------- |
| `super_admin` | Full system access |
| `admin` | Operations leadership |
| `dispatcher` | Dispatch + fleet assignment |
| `support` / `support_lead` | Tickets, exceptions; lead can approve refunds |
| `sales` / `sales_manager` | CRM, merchant onboarding |
| `finance` | Invoices, payouts, refunds |
| `fleet_manager` | Fleet + drivers |
| `compliance` | Merchant/driver document review |
| `developer` | API keys, webhooks, sandbox |
| `marketing` | Campaigns, read-only checkout analytics |
| `read_only` | Audit / reporting view |

Maps to enterprise roles per [RBAC_MATRIX.md](./RBAC_MATRIX.md) § Internal role mapping.

---

## Merchant organization roles

| Role | Description |
| ---- | ----------- |
| `merchant_owner` | Full merchant account |
| `merchant_admin` | Users, settings, billing |
| `merchant_ops` | Book, track, CSV, API |
| `merchant_finance` | Invoices, statements, pay |
| `merchant_readonly` | Track + reports only |

Module access: [RBAC_MATRIX.md](./RBAC_MATRIX.md) § Merchant portal module matrix.

---

## Related documents

| Document | Purpose |
| -------- | ------- |
| [RBAC_MATRIX.md](./RBAC_MATRIX.md) | Canonical permission matrices |
| [RBAC.md](./RBAC.md) | RBAC overview |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) | Clerk-only policy |
| [MODULE_BREAKDOWN.md](./MODULE_BREAKDOWN.md) | Module inventory |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
