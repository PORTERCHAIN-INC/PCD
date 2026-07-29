# ADR: Clerk identity + SpiceDB authz + Postgres data

**Status:** Accepted  
**Date:** 2026-07-29  
**Supersedes:** Hybrid RBAC in Postgres as authorization SoT (`user_role_assignments` / `MODULE_PERMISSIONS` as Check source)

## Context

PorterChain previously mixed identity, roles, and resource ACLs in PostgreSQL (`user_role_assignments`, admin/merchant module matrices, portal persona tables). That conflates business data with access rules and does not scale to network-style ReBAC (order → organization → member).

## Decision

| Layer                  | Responsibility                                                               |
| ---------------------- | ---------------------------------------------------------------------------- |
| **Clerk (Platform)**   | Authentication only: sign-up, sign-in, MFA, sessions, JWT `sub`              |
| **SpiceDB (Zanzibar)** | Authorization only: relationship graph + Check / Lookup / WriteRelationships |
| **PostgreSQL**         | Business data only: users, merchants, orders, drivers, customers, money      |

- No Clerk Organizations / JWT metadata as authz.
- No OpenFGA (SpiceDB chosen for ZedToken consistency).
- Profile tables (`admin_users`, `merchant_users`, …) remain **data** (membership / ops), not the Check engine.
- `porterchain_users` is the account row; `identity_links` bind Clerk subject → internal UUID.

## Consequences

- Request path: verify Clerk JWT → resolve internal user → **SpiceDB Check** for resource access.
- Session-context permissions/workspaces come from SpiceDB Lookup, not Postgres role packs.
- Provisioning events (invite, membership, order create) write SpiceDB relationships.
- Legacy `require_module` / assignment dual-write are retired or bridged only during cutover, then removed.
- SpiceDB outage with `SPICEDB_REQUIRED=true` → fail closed (403/503), never open.

## Schema

See [`apps/api/src/porterchain_api/authz/schema.zed`](../../apps/api/src/porterchain_api/authz/schema.zed).

Platform staff are **role relations** (`super_admin`, `sales`, …) — not a single `staff` blob.
`permission portal` is any staff (admin portal entry). `permission system_all` is **super_admin only**.
Module permissions expand from `MODULE_PERMISSIONS` in `admin_engine/rbac.py`. Keys that collide with
role relation names (`finance`, `support`) are stored as `mod_*` in `schema.zed`; `AuthzClient.check`
translates. `require_module` Checks the module permission only (no portal bypass).

## Ops

| Env   | `SPICEDB_ENABLED` | `SPICEDB_REQUIRED` | Notes                                         |
| ----- | ----------------- | ------------------ | --------------------------------------------- |
| Local | `true`            | `false`            | Soft memory fallback if `:50051` down         |
| Prod  | `true` (default)  | `true` (default)   | Fail closed; compose runs `spicedb` + migrate |

`MODULE_PERMISSIONS` (admin/merchant) is a **catalog** for schema expansions and UX module lists — not Check SoT.
Settings → Users authorize paths call `TupleWriter.sync_user_from_profiles` after persona writes.
