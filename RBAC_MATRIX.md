# Porterchain Enterprise RBAC Matrix


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Version:** 1.1  
**Authority:** Porterchain API (not Clerk Organizations)

---

## Principles

1. **Clerk authenticates** — signup, login, MFA, sessions only.
2. **Porterchain authorizes** — roles and permissions live in Porterchain tables and code.
3. **Never rely on Clerk Organizations** — merchant access resolves from `merchant_users.clerk_user_id`; staff from `admin_users.clerk_user_id`.
4. **API enforces** — portals may hide UI; every protected route calls `require_module()` or permission checks server-side.

---

## Enterprise roles (canonical)

| Role           | Value            | Portal          | Provisioned via  |
| -------------- | ---------------- | --------------- | ---------------- |
| Customer       | `customer`       | Website, `apps/customer/` (:3004), mobile-customer | Open signup      |
| Merchant       | `merchant`       | Merchant portal | Invitation       |
| Merchant Admin | `merchant_admin` | Merchant portal | Invitation       |
| Driver         | `driver`         | Driver portal (:3003), `apps/mobile-driver/` | Admin invitation |
| Dispatcher     | `dispatcher`     | Admin portal    | Staff invitation |
| Finance        | `finance`        | Admin portal    | Staff invitation |
| Support        | `support`        | Admin portal    | Staff invitation |
| Operations     | `operations`     | Admin portal    | Staff invitation |
| Admin          | `admin`          | Admin portal    | Staff invitation |
| Super Admin    | `super_admin`    | Admin portal    | Staff invitation |

**Source of truth:** `shared/python/porterchain_shared/auth/enterprise_roles.py`

---

## API permissions

| Permission        | Description                 |
| ----------------- | --------------------------- |
| `quote:read`      | View quotes                 |
| `quote:write`     | Create quotes               |
| `order:read`      | View orders                 |
| `order:write`     | Create/update orders        |
| `dispatch:manage` | Dispatch queue, assignments |
| `merchant:manage` | Merchant lifecycle, team    |
| `driver:manage`   | Driver approval, fleet      |
| `billing:manage`  | Invoices, settlements       |
| `crm:manage`      | Leads, CRM                  |
| `support:manage`  | Tickets, claims             |
| `admin:settings`  | System configuration        |
| `system:all`      | Super admin override        |

### Role → permission matrix

| Enterprise role    | Permissions                                                                          |
| ------------------ | ------------------------------------------------------------------------------------ |
| **customer**       | quote:read, quote:write, order:read                                                  |
| **merchant**       | quote:read, quote:write, order:read, order:write                                     |
| **merchant_admin** | merchant permissions + merchant:manage                                               |
| **driver**         | order:read                                                                           |
| **dispatcher**     | order:read, order:write, dispatch:manage                                             |
| **finance**        | order:read, billing:manage                                                           |
| **support**        | order:read, support:manage, crm:manage                                               |
| **operations**     | order:read, order:write, dispatch:manage, driver:manage, merchant:manage, crm:manage |
| **admin**          | All operational permissions + admin:settings                                         |
| **super_admin**    | system:all (all permissions)                                                         |

---

## Internal role mapping

Porterchain stores granular internal roles; they map to enterprise roles at runtime.

### Admin (`admin_users.role` → enterprise)

| Internal `admin_users.role`                                                                    | Enterprise role |
| ---------------------------------------------------------------------------------------------- | --------------- |
| `super_admin`                                                                                  | super_admin     |
| `admin`                                                                                        | admin           |
| `dispatcher`                                                                                   | dispatcher      |
| `support`, `support_lead`                                                                      | support         |
| `finance`                                                                                      | finance         |
| `fleet_manager`, `sales`, `sales_manager`, `marketing`, `compliance`, `developer`, `read_only` | operations      |

### Merchant (`merchant_users.role` → enterprise)

| Internal `merchant_users.role`                          | Enterprise role |
| ------------------------------------------------------- | --------------- |
| `merchant_owner`, `merchant_admin`                      | merchant_admin  |
| `merchant_ops`, `merchant_finance`, `merchant_readonly` | merchant        |

---

## Admin portal module matrix

Enforced in `apps/api/src/porterchain_api/admin_engine/rbac.py` via `require_module(ctx, module)`.

| Module             | super_admin | admin | dispatcher | finance | support | operations |
| ------------------ | :---------: | :---: | :--------: | :-----: | :-----: | :--------: |
| dashboard          |      ✓      |   ✓   |     ✓      |    ✓    |    ✓    |     ✓      |
| crm                |      ✓      |   ✓   |            |         |         |     ✓      |
| crm_read           |      ✓      |   ✓   |            |         |    ✓    |     ✓      |
| quotes             |      ✓      |   ✓   |     ✓      |         |         |     ✓      |
| quotes_read        |      ✓      |   ✓   |     ✓      |    ✓    |    ✓    |     ✓      |
| bookings           |      ✓      |   ✓   |     ✓      |         |    ✓    |            |
| merchants          |      ✓      |   ✓   |            |         |         |     ✓      |
| merchants_read     |      ✓      |   ✓   |     ✓      |    ✓    |    ✓    |     ✓      |
| drivers            |      ✓      |   ✓   |     ✓      |         |         |     ✓      |
| drivers_read       |      ✓      |   ✓   |     ✓      |         |    ✓    |     ✓      |
| dispatch           |      ✓      |   ✓   |     ✓      |         |         |     ✓      |
| dispatch_read      |      ✓      |   ✓   |     ✓      |         |    ✓    |            |
| orders             |      ✓      |   ✓   |     ✓      |         |    ✓    |            |
| orders_read        |      ✓      |   ✓   |     ✓      |    ✓    |    ✓    |     ✓      |
| pricing            |      ✓      |   ✓   |            |         |         |     ✓      |
| pricing_read       |      ✓      |   ✓   |     ✓      |         |    ✓    |     ✓      |
| finance            |      ✓      |   ✓   |            |    ✓    |    ✓    |            |
| finance_read       |      ✓      |   ✓   |            |    ✓    |    ✓    |            |
| claims             |      ✓      |   ✓   |            |    ✓    |         |     ✓      |
| claims_read        |      ✓      |   ✓   |     ✓      |         |    ✓    |            |
| support            |      ✓      |   ✓   |     ✓      |         |    ✓    |            |
| support_read       |      ✓      |   ✓   |     ✓      |    ✓    |    ✓    |     ✓      |
| reports            |      ✓      |   ✓   |     ✓      |    ✓    |    ✓    |     ✓      |
| settings           |      ✓      |   ✓   |            |         |         |            |
| notifications      |      ✓      |   ✓   |     ✓      |         |    ✓    |     ✓      |
| notifications_read |      ✓      |   ✓   |     ✓      |    ✓    |    ✓    |     ✓      |
| developers         |      ✓      |   ✓   |            |         |         |     ✓      |
| map                |      ✓      |   ✓   |     ✓      |         |    ✓    |     ✓      |
| routes             |      ✓      |   ✓   |     ✓      |         |         |     ✓      |
| routes_read        |      ✓      |   ✓   |     ✓      |         |    ✓    |     ✓      |
| routes_dispatch    |      ✓      |   ✓   |     ✓      |         |         |            |

---

## Merchant portal module matrix

Enforced in `apps/api/src/porterchain_api/merchant_engine/rbac.py`.

Internal roles: `merchant_owner`, `merchant_admin`, `merchant_ops`, `merchant_finance`, `merchant_readonly`.

| Module       | owner | admin | ops | finance | readonly |
| ------------ | :---: | :---: | :-: | :-----: | :------: |
| dashboard    |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| book         |   ✓   |   ✓   |  ✓  |         |          |
| bulk         |   ✓   |   ✓   |  ✓  |         |          |
| api_keys     |   ✓   |   ✓   |     |         |          |
| orders       |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| orders_write |   ✓   |   ✓   |  ✓  |         |          |
| tracking     |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| invoices     |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| invoices_pay |   ✓   |   ✓   |     |    ✓    |          |
| statements   |   ✓   |   ✓   |     |    ✓    |    ✓     |
| reports      |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| billing      |   ✓   |   ✓   |     |    ✓    |          |
| users        |   ✓   |   ✓   |     |         |          |
| settings     |   ✓   |   ✓   |  ✓  |    ✓    |          |
| support      |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| claims       |   ✓   |   ✓   |  ✓  |    ✓    |          |

**Enterprise view:**

| Module      |          merchant_admin           |            merchant            |
| ----------- | :-------------------------------: | :----------------------------: |
| All modules | Full (owner/admin internal roles) | ops, finance, readonly subsets |

---

## Authentication flow

```
Clerk JWT
    ↓
get_clerk_claims() + UserSyncService.sync()
    ↓
PrincipalResolver → admin_users | merchant_users | drivers | customers
    ↓
enterprise_role_for_*() → permissions + module access
    ↓
require_module() on each API route
```

### Merchant context (no Clerk org)

```
Clerk user_id
    ↓
merchant_users WHERE clerk_user_id = ?
    ↓
merchants WHERE id = merchant_users.merchant_id
    ↓
role = merchant_users.role (never from headers)
```

Optional `X-Merchant-Id` header selects membership when a user belongs to multiple merchants.

---

## API endpoints

| Endpoint                             | Description                                       |
| ------------------------------------ | ------------------------------------------------- |
| `GET /v1/auth/me`                    | Current principal + enterprise_role + permissions |
| `GET /v1/auth/rbac`                  | Full matrix + caller's effective access           |
| `GET /v1/auth/admin/access`          | Staff gate (admin_users)                          |
| `GET /v1/auth/merchant/access`       | Merchant gate (merchant_users)                    |
| `GET /v1/admin/settings/rbac`        | Admin settings RBAC matrix                        |
| `GET /v1/admin/settings/permissions` | Enterprise role → permissions map                 |
| `GET /v1/merchant/team/roles`        | Merchant portal role/module catalog               |

---

## Code locations

| Layer                          | Path                                                        |
| ------------------------------ | ----------------------------------------------------------- |
| Enterprise roles + permissions | `shared/python/porterchain_shared/auth/enterprise_roles.py` |
| Role resolution + matrix       | `apps/api/src/porterchain_api/auth/enterprise_rbac.py`      |
| Platform permission bridge     | `apps/api/src/porterchain_api/auth/rbac.py`                 |
| Principal resolution           | `apps/api/src/porterchain_api/auth/principal_resolver.py`   |
| Merchant auth                  | `apps/api/src/porterchain_api/auth/merchant.py`             |
| Admin modules                  | `apps/api/src/porterchain_api/admin_engine/rbac.py`         |
| Merchant modules               | `apps/api/src/porterchain_api/merchant_engine/rbac.py`      |
| TypeScript types               | `packages/types/src/auth.ts`                                |
| TypeScript RBAC helpers        | `packages/auth/src/rbac.ts`                                 |
| User registry sync             | `apps/api/src/porterchain_api/auth/user_sync_service.py`    |

---

## Invitation policy

| User type                                               | Signup  | Invitation required                     |
| ------------------------------------------------------- | ------- | --------------------------------------- |
| Customer                                                | Open    | No                                      |
| Merchant / Merchant Admin                               | Blocked | Yes (Clerk invite + merchant_users row) |
| Driver                                                  | Blocked | Yes                                     |
| Staff (dispatcher, finance, support, operations, admin) | Blocked | Yes (Clerk invite + admin_users row)    |

---

## Data scope rules

| Role         | Data scope                                       |
| ------------ | ------------------------------------------------ |
| `customer`   | `customer_id = self`                             |
| `merchant_*` | `merchant_id = org` (from `merchant_users` row)  |
| `driver`     | `driver_id = self`                               |
| `sales`      | Leads + merchants in territory (optional filter) |
| `support`    | Order lookup by reference; tier-1 PII masking    |
| `finance`    | All billing entities; no dispatch write          |

---

## Driver and customer capabilities

| Surface  | Allowed actions (summary) |
| -------- | ------------------------- |
| Driver   | Assigned jobs, location, POD, own wallet/documents |
| Customer | Own orders, tracking, invoices, rebook, profile (Clerk) |

Enforced in `driver_engine/` and customer routes — not module-based like admin/merchant portals.

---

## Merchant API key scopes (machine auth)

| Scope             | Allows            |
| ----------------- | ----------------- |
| `shipments:read`  | GET shipments     |
| `shipments:write` | Create shipments  |
| `tracking:read`   | Tracking events   |
| `webhooks:manage` | Register webhooks |
| `invoices:read`   | Billing read      |

Implementation: `apps/api/src/porterchain_api/auth/merchant_api.py`

---

## Audit requirements

| Action                     | Logged              |
| -------------------------- | ------------------- |
| Role assignment            | `admin_audit_log`   |
| Refund approval            | `admin_audit_log`   |
| Merchant ACTIVE toggle     | Merchant events     |
| API key create/revoke      | Merchant audit      |
| SSO Fleetbase session      | Recommended         |

---

## Related docs

| Document | Purpose |
| -------- | ------- |
| [RBAC.md](./RBAC.md) | Overview + Fleetbase sync summary |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) | Clerk-only identity |
| [SSO.md](./SSO.md) | Fleetbase console SSO |
| [SECURITY.md](./SECURITY.md) | Secrets, API hardening |
| [INVITATION_WORKFLOW.md](./INVITATION_WORKFLOW.md) | Invitation provisioning |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
