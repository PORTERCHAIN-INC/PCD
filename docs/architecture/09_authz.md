# 09 — Authorization model (AS-BUILT)

```mermaid
flowchart LR
  subgraph IdP
    CL[Clerk JWT: merchant, driver, customer]
    ST[Staff IdP: passkey/magic link -> Redis session porterchain:staff]
    AK[Merchant API key + scopes]
  end
  CL --> DEP[auth/dependencies.py]
  ST --> ADM[admin_engine/rbac.py:243 require_module]
  AK --> SC[require_scope]
  DEP --> MRB[merchant_engine/rbac.py:166 require_module]
  ADM -->|check platform#perm, retry then 503| SDB[(SpiceDB authz/schema.zed)]
  MRB -->|check organization#perm, no retry| SDB
```

## schema.zed (authz/schema.zed)

| Definition                                                   | Relations                                                                                                                                             | Example permissions                                                                                                                  |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| user                                                         | —                                                                                                                                                     | —                                                                                                                                    |
| platform                                                     | super_admin, admin, dispatcher, support, support_lead, sales, sales_manager, finance, compliance, developer, marketing, read_only, fleet_manager (13) | system_all = super_admin; impersonation = super_admin; diagnostics = super_admin + admin + developer; settings = super_admin + admin |
| organization                                                 | owner, admin, ops, finance, readonly, member                                                                                                          | portal, manage, book, bulk, routes, api_keys, orders, invoices, claims                                                               |
| driver_profile, customer_profile, order (parent org, viewer) | —                                                                                                                                                     | —                                                                                                                                    |

## Admin UI vs authz

`apps/admin/src/lib/admin-nav.ts:378-405`: super_admin sees everything; `SUPER_ONLY={"/system"}` with developer also allowed. SpiceDB `diagnostics` also grants **admin** → UI hides what the API allows (conflict, see 11).

## Duplicates

- `routers/merchant/_deps.py:230` re-wraps `require_module` (second wrapper).
- Python `MODULE_PERMISSIONS` matrix + `schema.zed` = two sources of truth.
- Unguarded non-public routes: `/internal/health`, `/internal/services` (`gateway/router.py:11,16`).
