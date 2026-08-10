# Clerk apps setup

**Type:** POINTER  
**Last verified:** 2026-08-06

PorterChain runs **`CLERK_MODE=platform_driver`**:

| Clerk app            | Env triad                                                                             | Consumers                     |
| -------------------- | ------------------------------------------------------------------------------------- | ----------------------------- |
| PorterChain Platform | `CLERK_*` / `CLERK_ADMIN_*` / `CLERK_CUSTOMER_*` / `CLERK_MERCHANT_*` (Platform keys) | website · customer · merchant |
| Porterchain Driver   | `CLERK_DRIVER_*`                                                                      | driver portal · mobile-driver |

Admin portal uses **PorterChain staff IdP** (Redis session) — no Clerk publishable key.

`CLERK_MODE=unified` and `CLERK_MODE=enterprise` are **retired** (`pnpm clerk:sync` / validate scripts exit if requested).

- **Secret names:** [docs/SECRETS_MAP.md](../../docs/SECRETS_MAP.md)
- **Consolidation history (superseded layout notes):** [SSO.md](../../SSO.md)
- **Production cutover:** [SSO.md](../../SSO.md)
- **Doppler/GitHub matrix:** [docs/architecture/clerk-doppler-secret-matrix.md](../../docs/architecture/clerk-doppler-secret-matrix.md)
