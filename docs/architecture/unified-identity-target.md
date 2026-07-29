# Unified identity — target model

**Status:** SUPERSEDED  
**SSOT:** [auth-clerk-spicedb.md](./auth-clerk-spicedb.md)

This Phase-1 hybrid design (Postgres role assignments / overrides as authz SoT) is **retired**.

| Layer    | Owns                                        |
| -------- | ------------------------------------------- |
| Clerk    | Login / signup / JWT only                   |
| SpiceDB  | Access-rules graph (Check / Lookup / Write) |
| Postgres | Users, profiles, orders — **not** ACL Check |

Do not reintroduce `user_role_assignments` or `user_permission_overrides`.
