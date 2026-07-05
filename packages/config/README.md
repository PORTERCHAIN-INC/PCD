# @porterchain/config


**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05


Shared tooling configuration for the Porterchain monorepo.

**Package:** `@porterchain/config` · **Path:** `packages/config/`

---

## Exports

| Export | File | Purpose |
| ------ | ---- | ------- |
| `@porterchain/config/prettier` | `prettier.config.mjs` | Shared Prettier config |
| `@porterchain/config/monorepo-env.mjs` | `monorepo-env.mjs` | Load `env/.env` + Next.js public env helpers |
| *(file)* | `tsconfig.base.json` | Base TypeScript compiler options |

---

## Monorepo Env Loader

Used by all Next.js apps in `next.config.ts`:

```typescript
import { loadMonorepoEnv, nextPublicEnv } from "@porterchain/config/monorepo-env.mjs";

loadMonorepoEnv(process.cwd(), "../env/.env"); // path relative to app cwd
export default {
  env: { ...nextPublicEnv() },
};
```

### Functions

| Function | Returns |
| -------- | ------- |
| `loadMonorepoEnv(cwd, relativeEnvPath?)` | Loads `env/.env`; does **not** override existing `process.env` |
| `nextPublicEnv()` | `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `NEXT_PUBLIC_PORTERCHAIN_API_URL`, etc. |
| `adminPublicEnv()` | `nextPublicEnv()` + admin dev bypass flags |
| `customerPublicEnv()` | `nextPublicEnv()` + `NEXT_PUBLIC_WEBSITE_URL` |

### Apps Using This

- `website/next.config.ts`
- `apps/admin/next.config.ts`
- `apps/merchant-portal/next.config.ts`
- `apps/driver-portal/next.config.ts`
- `apps/customer/next.config.ts`

---

## TypeScript Base Config

`tsconfig.base.json` — shared strict defaults extended by app and package `tsconfig.json` files:

- `strict: true`
- `moduleResolution: bundler`
- `jsx: react-jsx`
- DOM + ESNext libs

---

## Other Config Locations

| Location | Contents |
| -------- | -------- |
| `env/*.env.example` | Per-surface environment templates |
| `shared/python/porterchain_shared/config/` | Python `PlatformSettings` |
| `shared/config/README.md` | Env index and integration ownership |
| App `.env.local` / `.env` | Runtime secrets (never committed) |

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [../../shared/config/README.md](../../shared/config/README.md) | Centralized env index |
| [../../ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md) | Full variable catalog |
| [../../env/README.md](../../env/README.md) | Env folder guide |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../../masterrule.md](../../masterrule.md) | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout |

