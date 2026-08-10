# Authorization matrix — superseded

**Status:** RETIRED  
**SSOT:** [docs/architecture/auth-clerk-spicedb.md](./docs/architecture/auth-clerk-spicedb.md)

Postgres `user_role_assignments`, enterprise RBAC matrices, and this document are **not** the authorization Check source.

| Layer    | Owns                                                            |
| -------- | --------------------------------------------------------------- |
| Clerk    | Identity (login/signup/JWT)                                     |
| SpiceDB  | Relationships + Check / Lookup / Write                          |
| Postgres | Business data + persona profiles (feed tuples, never Check SoT) |

Schema: `apps/api/src/porterchain_api/authz/schema.zed`
