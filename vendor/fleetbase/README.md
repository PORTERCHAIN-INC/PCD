# Fleetbase (upstream vendor)


**Type:** README
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Canonical runtime location:** `apps/fleetbase/`  
**Version:** v0.7.40 (OSS, AGPL-3.0)

This directory is the **logical vendor reference** for Fleetbase in the Porterchain monorepo. The upstream Fleetbase source lives at `apps/fleetbase/` and is **not modified** by Porterchain.

---

## Why two paths?

| Path | Purpose |
| ---- | ------- |
| `vendor/fleetbase/` | Documentation anchor — external upstream dependency |
| `apps/fleetbase/` | Actual clone used by Docker Compose |

---

## Rules

1. **Never modify** Fleetbase core packages (`api/vendor/`, `console/node_modules/`, extension packages in Docker image).
2. **Never add** Porterchain business logic inside `apps/fleetbase/`.
3. **All integration** goes through `services/fleetbase-adapter/` and `apps/api/.../fleetbase_engine/`.
4. **Extensions only** — Porterchain-specific routes (SSO, tailored sync) belong in a separate `porterchain-bridge` Composer package.

---

## Do not modify

| Directory | Reason |
| --------- | ------ |
| `apps/fleetbase/api/` | Laravel shell |
| `apps/fleetbase/console/` | Ember console |
| `apps/fleetbase/packages/` | Upstream submodules |
| `apps/fleetbase/docker/` | Upstream Docker build |

---

## Safe Porterchain touchpoints

| Location | Allowed change |
| -------- | -------------- |
| `infrastructure/docker/fleetbase.porterchain.override.yml` | Port mappings, env overrides |
| `env/fleetbase.env.example` | Porterchain env template |
| `porterchain-bridge` extension (future) | SSO + custom routes |

---

## Operations

```bash
pnpm docker:fleetbase:install   # first time
pnpm docker:fleetbase:up
pnpm docker:fleetbase:verify
```

---

## Related

| Document | Purpose |
| -------- | ------- |
| [FLEETBASE_INSTALL.md](../../FLEETBASE_INSTALL.md) | Install runbook |
| [FLEETBASE_INTEGRATION.md](../../FLEETBASE_INTEGRATION.md) | Bridge architecture |
| [FLEETBASE_INTEGRATION.md](../../FLEETBASE_INTEGRATION.md) | Porterchain integration overview |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../../masterrule.md](../../masterrule.md) | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout |

