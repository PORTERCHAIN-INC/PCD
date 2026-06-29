# Porterchain — Role-Based Access Control (RBAC)

**Version:** 2.0  
**Date:** June 29, 2026  
**Enforcement:** Server-side in Porterchain API; Fleetbase permissions synchronized for console users

---

## Design principles

1. **Clerk authenticates** — identity only
2. **Porterchain authorizes** — roles and permissions in API
3. **Fleetbase mirrors ops permissions** — dispatchers/admins get synced Fleetbase IAM permissions via SSO
4. **No client-only security** — portals may hide UI; API always enforces

---

## Platform roles

Defined in `packages/types/src/auth.ts` and `porterchain_shared/auth/roles.py`:

| Platform role | User types | Description |
|---------------|------------|-------------|
| `visitor` | Anonymous | Quote only |
| `customer` | Retail | Own orders |
| `merchant` | B2B | Org shipments |
| `driver` | Driver partners | Assigned jobs |
| `dispatcher` | Ops | Dispatch + Fleetbase SSO |
| `support` | Ops | Tickets, read orders |
| `sales` | Ops | CRM, merchants |
| `fleet_manager` | Ops | Fleet + drivers |
| `admin` | Ops | Broad operations |
| `super_admin` | Ops | Full access |

---

## Canonical permissions

| Permission | Description |
|------------|-------------|
| `quote:read` | View quotes |
| `quote:write` | Create quotes |
| `order:read` | View orders |
| `order:write` | Create/update orders |
| `dispatch:manage` | Assign drivers, dispatch queue |
| `merchant:manage` | Merchant lifecycle |
| `driver:manage` | Driver approval, fleet |
| `billing:manage` | Invoices, refunds |
| `crm:manage` | Leads, CRM |
| `support:manage` | Tickets, claims |
| `admin:settings` | System configuration |
| `system:all` | Super admin |

Role → permission mapping: `ROLE_PERMISSIONS` in `porterchain_shared/auth/roles.py`.

---

## Admin portal RBAC

**Implementation:** `apps/api/src/porterchain_api/admin_engine/rbac.py`

| Module key | Roles with access |
|------------|-------------------|
| `dashboard` | All admin roles |
| `crm` | super_admin, admin, sales, sales_manager, marketing |
| `dispatch` | super_admin, admin, dispatcher, fleet_manager |
| `drivers` | super_admin, admin, dispatcher, fleet_manager, compliance |
| `merchants` | super_admin, admin, sales, sales_manager, compliance |
| `orders` | super_admin, admin, dispatcher, support, support_lead |
| `finance` | super_admin, admin, finance, support_lead |
| `settings` | super_admin, admin |
| `map` | super_admin, admin, dispatcher, fleet_manager, support |

Enforced via `require_module(ctx, "dispatch")` on each admin route.

### Admin role → user type

| Admin role (`admin_users.role`) | `UserType` | Platform roles |
|---------------------------------|------------|----------------|
| `dispatcher` | `dispatcher` | `dispatcher` |
| `support`, `support_lead` | `support` | `support` |
| `sales`, `sales_manager` | `sales` | `sales` |
| `fleet_manager` | `admin` | `fleet_manager`, `admin` |
| `super_admin`, `admin`, others | `admin` | `admin` or `super_admin` |

---

## Merchant portal RBAC

**Implementation:** `apps/api/src/porterchain_api/merchant_engine/rbac.py`

| Module | owner | admin | ops | finance | readonly |
|--------|:-----:|:-----:|:---:|:-------:|:--------:|
| book | ✓ | ✓ | ✓ | — | — |
| api_keys | ✓ | ✓ | — | — | — |
| orders_write | ✓ | ✓ | ✓ | — | — |
| invoices_pay | ✓ | ✓ | — | ✓ | — |
| users | ✓ | ✓ | — | — | — |

Clerk organization ID passed as `X-Merchant-Org-Id`; user resolved by `clerk_user_id`.

---

## Fleetbase permission sync

**Implementation:** `apps/api/src/porterchain_api/auth/fleetbase_roles.py`

When a Porterchain admin user accesses Fleetbase SSO, permissions are mapped:

| Porterchain admin role | Fleetbase permissions (sample) |
|------------------------|-------------------------------|
| `dispatcher` | `fleet-ops list order`, `fleet-ops dispatch order`, `fleet-ops list driver` |
| `admin` | `fleet-ops * order`, `fleet-ops * driver`, `iam * user` |
| `super_admin` | `*` |
| `support` | `fleet-ops list order`, `fleet-ops view order` (read-only) |

Stored on `identity_links.fleetbase_permissions` and sent to Fleetbase SSO bridge:

```
POST /int/v1/porterchain/sso/users/{uuid}/permissions
```

Fleetbase IAM stays synchronized without duplicate user accounts.

---

## Fleetbase console access matrix

| Porterchain role | Fleetbase console | Permission level |
|------------------|-------------------|------------------|
| `dispatcher` | SSO | Dispatch + fleet ops |
| `admin`, `super_admin` | SSO | Full ops |
| `fleet_manager` | SSO | Fleet + dispatch |
| `support`, `support_lead` | SSO | Read-only map/orders |
| `sales`, `finance`, `merchant`, `customer`, `driver` | **Denied** | — |

Enforced in `SsoService.exchange_fleetbase_session()` → `PermissionError`.

---

## API enforcement patterns

### Admin routes

```python
@router.get("/dispatch/queue")
def dispatch_queue(ctx: AdminContext = Depends(get_admin_context)):
    require_module(ctx, "dispatch")
    ...
```

### Merchant routes

```python
def create_shipment(ctx: MerchantContext = Depends(get_merchant_context)):
    require_module(ctx, "book")
    ...
```

### Auth introspection

```python
GET /v1/auth/me  →  roles + permissions + fleetbase_console_eligible
```

### Unified principal check

```python
from porterchain_api.auth.rbac import principal_has_permission
principal_has_permission(principal, Permission.DISPATCH_MANAGE)
```

---

## Clerk metadata conventions

Set in Clerk Dashboard → User → Public metadata:

```json
{
  "role": "dispatcher",
  "porterchain_role": "dispatcher"
}
```

For merchants, use Clerk Organizations with org roles mapped to `merchant_owner`, `merchant_ops`, etc.

---

## Identity linking

Table: `identity_links`

| Column | Purpose |
|--------|---------|
| `clerk_user_id` | Single Clerk identity |
| `user_type` | admin, merchant, driver, customer |
| `platform_user_id` | FK to admin_users / merchant_users / etc. |
| `fleetbase_user_uuid` | Linked Fleetbase user (no duplicate) |
| `fleetbase_permissions` | Synced permission list |
| `last_synced_at` | Last SSO exchange |

---

## Audit requirements

| Action | Logged |
|--------|--------|
| SSO Fleetbase session issued | Recommended (add audit log) |
| Role assignment | `admin_audit_log` |
| Driver approval + Fleetbase sync | `admin_audit_log` |
| Merchant ACTIVE toggle | Merchant events |

---

## Development bypass

| Flag | Behavior |
|------|----------|
| `CLERK_DEV_BYPASS=true` | Accept requests without Clerk JWT |
| `Authorization: Bearer dev` | Local dev token |
| `X-Admin-Role: dispatcher` | Dev admin role override |

---

## Related documents

- [AUTHENTICATION_FLOW.md](./AUTHENTICATION_FLOW.md)
- [SSO.md](./SSO.md)
- [ROLE_PERMISSIONS.md](./ROLE_PERMISSIONS.md)
