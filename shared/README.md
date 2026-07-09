# Shared Cross-App Modules

**Type:** README
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-08

Reusable code consumed by Porterchain web apps, API, and worker. Split across **TypeScript packages** (`packages/`) and **Python modules** (`shared/python/`).

---

## TypeScript — Web (`packages/`)

Shared by Next.js portals and website:

| Package               | Path               | Purpose                                      |
| --------------------- | ------------------ | -------------------------------------------- |
| `@porterchain/ui`     | `packages/ui/`     | Web UI primitives                            |
| `@porterchain/maps`   | `packages/maps/`   | Google Maps provider, autocomplete           |
| `@porterchain/auth`   | `packages/auth/`   | Clerk helpers, RBAC types                    |
| `@porterchain/types`  | `packages/types/`  | Shared TS types                              |
| `@porterchain/events` | `packages/events/` | Event catalog / envelope types               |
| `@porterchain/queue`  | `packages/queue/`  | Queue name types                             |
| `@porterchain/config` | `packages/config/` | Prettier, tsconfig base, monorepo env loader |

---

## Web Providers (`shared/`)

| Path                | Purpose                                      |
| ------------------- | -------------------------------------------- |
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

## Mobile (`apps/mobile-*`)

Fresh Expo SDK 57 apps (React Native 0.86) — minimal shells for redesign:

| App      | Package                        | Stack                        |
| -------- | ------------------------------ | ---------------------------- |
| Driver   | `@porterchain/mobile-driver`   | Expo 57, RN 0.86, React 19.2 |
| Customer | `@porterchain/mobile-customer` | Expo 57, RN 0.86, React 19.2 |

Run: `pnpm dev:mobile-driver` or `pnpm dev:mobile-customer`

---

## Related Docs

- [REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md)
- [packages/shared/README.md](../packages/shared/README.md)
