# Shared cross-app modules

Reusable primitives consumed by all Porterchain applications. TypeScript packages live in `packages/`; this folder holds app-agnostic hooks and providers.

| Path         | Purpose                                               |
| ------------ | ----------------------------------------------------- |
| `config/`    | Environment variable index and integration boundaries |
| `hooks/`     | Shared React hooks (visitor session, auth helpers)    |
| `providers/` | Shared React context providers                        |

Python shared code: `shared/python/porterchain_shared/`
