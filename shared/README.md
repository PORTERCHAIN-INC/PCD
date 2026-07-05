# Shared Cross-App Modules


**Type:** README
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05


Reusable code consumed by Porterchain web apps, mobile apps, API, and worker. Split across **TypeScript packages** (`shared/` + `packages/`) and **Python modules** (`shared/python/`).

---

## TypeScript — Mobile (`shared/`)

pnpm workspace packages for Expo apps:

| Package | Path | Purpose |
| ------- | ---- | ------- |
| `@porterchain/mobile-api` | `shared/api/` | HTTP client, driver/customer API facades, TanStack Query |
| `@porterchain/mobile-theme` | `shared/theme/` | Light/dark tokens, `ThemeProvider` |
| `@porterchain/mobile-ui` | `shared/mobile-ui/` | Design system components |
| `@porterchain/mobile-components` | `shared/components/` | FlashList, offline banner |
| `@porterchain/mobile-hooks` | `shared/hooks/` | Online status, app state, a11y |
| `@porterchain/mobile-storage` | `shared/storage/` | MMKV, Secure Store, offline queue |
| `@porterchain/mobile-maps` | `shared/maps/` | `EnterpriseMap`, maps provider |
| `@porterchain/mobile-notifications` | `shared/notifications/` | FCM, inbox, deep links |
| `@porterchain/mobile-offline` | `shared/offline/` | Offline sync provider |
| `@porterchain/mobile-security` | `shared/mobile-security/` | Clerk, PIN, biometric, secure API client |
| `@porterchain/mobile-performance` | `shared/mobile-performance/` | FlashList, lazy screens, metrics |

See [MOBILE_ARCHITECTURE_REPORT.md](../MOBILE_ARCHITECTURE_REPORT.md).

---

## TypeScript — Web (`packages/`)

Shared by Next.js portals and website:

| Package | Path | Purpose |
| ------- | ---- | ------- |
| `@porterchain/ui` | `packages/ui/` | Web UI primitives |
| `@porterchain/maps` | `packages/maps/` | Google Maps provider, autocomplete |
| `@porterchain/auth` | `packages/auth/` | Clerk helpers, RBAC types |
| `@porterchain/types` | `packages/types/` | Shared TS types |
| `@porterchain/events` | `packages/events/` | Event catalog / envelope types |
| `@porterchain/queue` | `packages/queue/` | Queue name types |
| `@porterchain/config` | `packages/config/` | Prettier, tsconfig base, monorepo env loader |

---

## Web Hooks & Providers (`shared/`)

| Path | Purpose |
| ---- | ------- |
| `shared/hooks/useVisitorSession.ts` | Website visitor session |
| `shared/providers/` | Shared React providers (`PlatformProviders`) |

---

## Python (`shared/python/`)

```
shared/python/porterchain_shared/
├── config/         PlatformSettings
├── auth/           RBAC, session helpers
├── queue/          Queue names, Redis publisher
├── events/         Shared event types
├── types/          Ownership, user types
└── redis_health.py Production Redis guard
```

Consumed by `apps/api`, `apps/worker`, and `services/python/`.

Settings: [shared/config/README.md](./config/README.md)

---

## Maps Module Doc

Detailed maps architecture: [shared/maps/MAP_MODULE.md](./maps/MAP_MODULE.md)

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [../packages/config/README.md](../packages/config/README.md) | TS tooling config |
| [../REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md) | Monorepo layout |
| [../TECH_STACK.md](../TECH_STACK.md) | Stack reference |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../masterrule.md](../masterrule.md) | Architecture SSOT |
| [../REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md) | Monorepo layout |

