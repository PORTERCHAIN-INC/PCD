# Fleetbase (upstream vendor)

**Canonical runtime location:** `apps/fleetbase/`  
**Version:** v0.7.40 (OSS, AGPL-3.0)

This directory is the **logical vendor reference** for Fleetbase in the Porterchain monorepo. The upstream Fleetbase source remains at `apps/fleetbase/` and is **not moved or modified** by Porterchain.

## Why two paths?

| Path                | Purpose                                                                   |
| ------------------- | ------------------------------------------------------------------------- |
| `vendor/fleetbase/` | Documentation anchor — marks Fleetbase as an external upstream dependency |
| `apps/fleetbase/`   | Actual clone used by Docker Compose and local development                 |

## Rules

1. **Never modify** Fleetbase core packages (`api/vendor/`, `console/node_modules/`, Composer/npm extension packages).
2. **Never add** Porterchain business logic inside `apps/fleetbase/`.
3. **All integration** goes through `services/fleetbase-adapter/`.
4. **Extensions only** — Porterchain-specific Fleetbase routes (SSO bridge, order sync) belong in a separate Fleetbase extension package, not in upstream OSS files.

## Do not modify

| Directory                  | Reason                                     |
| -------------------------- | ------------------------------------------ |
| `apps/fleetbase/api/`      | Laravel shell — logic in Composer packages |
| `apps/fleetbase/console/`  | Ember console — logic in npm packages      |
| `apps/fleetbase/packages/` | Upstream git submodules                    |
| `apps/fleetbase/docker/`   | Upstream Docker build                      |
| `apps/fleetbase/infra/`    | Upstream Helm chart                        |

## Safe Porterchain touchpoints

| Location                                                   | Allowed change                        |
| ---------------------------------------------------------- | ------------------------------------- |
| `infrastructure/docker/fleetbase.porterchain.override.yml` | Port mappings, env overrides          |
| `env/fleetbase.env.example`                                | Porterchain env template              |
| Fleetbase extension (future)                               | `porterchain-bridge` Composer package |

## Operations

```bash
pnpm docker:fleetbase:up
pnpm docker:fleetbase:verify
```

See [FLEETBASE_INSTALL.md](../../FLEETBASE_INSTALL.md) and [FLEETBASE_ANALYSIS.md](../../FLEETBASE_ANALYSIS.md).
