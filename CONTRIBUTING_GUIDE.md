# Contributing Guide

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Repository:** Porterchain (PCD monorepo)

---

## Principles

1. **Porterchain owns the customer experience** — website, merchant portal, pricing, billing.
2. **Fleetbase owns fleet execution** — dispatch, routing, GPS, driver ops console.
3. **The adapter is the only bridge** — no direct Fleetbase HTTP calls outside `services/fleetbase-adapter/`.
4. **Never modify Fleetbase core** — treat `apps/fleetbase/` as read-only upstream.
5. **Never mix business logic into Fleetbase** — no merchant contracts, Stripe, or Clerk code in Fleetbase.
6. **Simplify before expanding** — [masterrule §21](./masterrule.md#21-simplification--essential-complexity): essential complexity only; thin routers; no `merchant_engine` → `admin_engine` imports.
7. **Docs follow code** — update canonical docs or OpenAPI; follow [Appendix C](./masterrule.md#appendix-c--documentation-simplification-program) (39 groups × 5 files).
8. **Refactor over rewrite** — strangler extractions only; no greenfield rewrites. Ship incremental PRs; keep production running. See [docs/api/CHANGELOG.md](./docs/api/CHANGELOG.md) for API compatibility.

---

## Refactor policy (§0.3.5)

| Do                                                                          | Don't                                          |
| --------------------------------------------------------------------------- | ---------------------------------------------- |
| Extract `*_service.py` modules ≤400 LOC                                     | Split into microservices                       |
| Add ADR before Phase 2 surfaces                                             | Add CRM UI / Route Center before prod dispatch |
| Run `pnpm validate:d2` + `validate:d3` before merge                         | Bypass Fleetbase via direct HTTP in apps       |
| Run `pnpm validate:precommit` locally (auto via Husky after `pnpm install`) | Skip format/D2 checks before push              |
| Pin Docker tags/digests (see `.cursor/rules/dependency-freeze.mdc`)         | Upgrade Next/React/TS without approval         |

## Repository layout

See [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md) for the full map.

| Area                          | You may edit            | You must not edit         |
| ----------------------------- | ----------------------- | ------------------------- |
| `website/`                    | Booking UX, marketing   | Fleetbase API calls       |
| `apps/merchant-portal/`       | B2B portal              | Fleetbase schema          |
| `apps/admin/`                 | Ops dashboard           | Fleetbase console source  |
| `apps/customer/`              | Retail customer portal  | Fleetbase API calls       |
| `apps/driver-portal/`         | Driver web dashboard    | Fleetbase API calls       |
| `apps/mobile-driver/`         | Driver mobile app       | Fleetbase API calls       |
| `apps/mobile-customer/`       | Customer mobile app     | Fleetbase API calls       |
| `apps/worker/`                | Event bus + queues      | Direct Fleetbase HTTP     |
| `apps/api/`                   | All Porterchain domains | Direct Fleetbase HTTP     |
| `services/fleetbase-adapter/` | Integration logic       | Porterchain pricing rules |
| `apps/fleetbase/`             | **Nothing** (read-only) | Core packages, console    |
| `infrastructure/docker/`      | Compose overlays        | —                         |

---

## Where to put changes

| Change type                     | Location                                                   |
| ------------------------------- | ---------------------------------------------------------- |
| New Fleetbase API wrapper       | `services/fleetbase-adapter/`                              |
| Order status webhook handling   | Adapter `events/` + API `fleetbase_engine/`                |
| SSO / RBAC                      | `apps/api/auth/` + adapter `auth/`                         |
| Public tracking page            | `website/`                                                 |
| Merchant invoice logic          | `apps/api/` billing domains                                |
| Docker port for Fleetbase MySQL | `infrastructure/docker/fleetbase.porterchain.override.yml` |
| Fleetbase custom routes         | Separate bridge extension (not `apps/fleetbase/api/`)      |

---

## Fleetbase: directories you must never modify

```
apps/fleetbase/api/                 # Laravel application shell
apps/fleetbase/api/vendor/          # Composer packages (runtime logic)
apps/fleetbase/console/             # Ember console application
apps/fleetbase/console/node_modules/
apps/fleetbase/packages/            # Upstream git submodules
apps/fleetbase/docker/              # Upstream Docker build
apps/fleetbase/infra/               # Upstream Helm chart
apps/fleetbase/scripts/             # Upstream install scripts
```

**Allowed** Porterchain touchpoints for Fleetbase:

- `infrastructure/docker/fleetbase.porterchain.override.yml`
- `env/fleetbase.env.example`
- `vendor/fleetbase/README.md` (documentation only)
- Future `porterchain-bridge` Composer extension (separate repo/package)

---

## Development setup

### Node / frontend

Requires Node **24.18.0** (see `.nvmrc`) and pnpm **9.15+**.

```bash
corepack enable
pnpm install
pnpm dev              # turbo — website, portals
pnpm dev:merchant
pnpm dev:admin
pnpm dev:customer
pnpm dev:driver
pnpm dev:mobile-driver
pnpm dev:mobile-customer
```

### Python / API

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../.. && pnpm dev:api
```

### Fleetbase stack

```bash
pnpm docker:fleetbase:up
pnpm docker:fleetbase:verify
```

---

## Code conventions

### Python (adapter + API)

- Use existing service class patterns in `fleetbase-adapter/`
- Suppress and log Fleetbase sync failures via `ErrorHandler` — return `None`, don't crash API requests
- Type hints on all public methods
- No comments that merely restate the code

### TypeScript (apps + packages)

- Shared UI in `packages/ui`
- Shared types in `packages/types`
- Match existing Next.js App Router patterns

### Imports

```python
# Preferred (new code)
from porterchain_fleetbase_adapter import FleetbaseAdapter

# Deprecated (still works via shim)
from porterchain_fleetbase import FleetbaseIntegrationService
```

---

## Pull request checklist

- [ ] No changes under `apps/fleetbase/api/` or `apps/fleetbase/console/` (except submodule pointer updates)
- [ ] No direct `httpx` calls to Fleetbase outside `fleetbase-adapter/`
- [ ] No Porterchain pricing/billing logic in adapter mappers
- [ ] Webhook event mappings updated if Fleetbase events change
- [ ] `apps/api/requirements.txt` updated if adapter dependencies change
- [ ] Documentation updated for architectural changes

---

## Testing

| Layer           | How to test                                    |
| --------------- | ---------------------------------------------- |
| Adapter unit    | Import tests, mapper assertions                |
| API integration | `pnpm dev:api` + Fleetbase Docker stack        |
| Webhooks        | `POST /webhooks/fleetbase` with signed payload |
| SSO             | Admin portal "Open Fleetbase Console" button   |

---

## Security

- Fleetbase API keys are server-side only — never in frontend env
- Webhook signatures must be verified by `WebhookService`
- Clerk JWT validation stays in `apps/api/auth/`
- Do not commit secrets — use `env/*.env.example` templates

---

## Documentation

When making architectural changes, update:

- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md) (if paths change)
- [EXTENSION_GUIDE.md](./EXTENSION_GUIDE.md) (if extension patterns change)
- [docs/README.md](./docs/README.md) index

---

## Getting help

| Topic               | Document                                                                               |
| ------------------- | -------------------------------------------------------------------------------------- |
| System design       | [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md) |
| Product scope       | [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)                                   |
| Fleetbase internals | [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                                 |
| Adapter design      | [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)               |
| Upgrading Fleetbase | [UPGRADE_GUIDE.md](./UPGRADE_GUIDE.md)                                                 |

---

## Related documents

- [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)
- [EXTENSION_GUIDE.md](./EXTENSION_GUIDE.md)
- [UPGRADE_GUIDE.md](./UPGRADE_GUIDE.md)

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
