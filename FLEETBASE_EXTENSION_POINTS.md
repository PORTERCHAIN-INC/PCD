# Fleetbase Extension Points — Porterchain Guide


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Goal:** Integrate with Fleetbase **without modifying upstream OSS source** (AGPL compliance + upgrade path)

> **Current integration:** [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) · **Adapter:** [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)

---

## Extension model

Fleetbase is built as installable **PHP packages** (Laravel) + **Ember engines** (console UI), discovered via:

| Mechanism         | Location                                              |
| ----------------- | ----------------------------------------------------- |
| Composer packages | `api/composer.json` require block                     |
| Ember engines     | `console/package.json` dependencies                   |
| Git submodules    | `apps/fleetbase/packages/*` (source mirrors)          |
| Registry          | `https://registry.fleetbase.io` via `registry-bridge` |
| CLI               | `flb extension:install`                               |

### Submodule repos (`.gitmodules`)

| Path                       | Repository                |
| -------------------------- | ------------------------- |
| `packages/core-api`        | fleetbase/core-api        |
| `packages/fleetops`        | fleetbase/fleetops        |
| `packages/fleetops-data`   | fleetbase/fleetops-data   |
| `packages/storefront`      | fleetbase/storefront      |
| `packages/ledger`          | fleetbase/ledger          |
| `packages/registry-bridge` | fleetbase/registry-bridge |
| `packages/ember-core`      | fleetbase/ember-core      |
| `packages/ember-ui`        | fleetbase/ember-ui        |
| `packages/iam-engine`      | fleetbase/iam-engine      |
| `packages/dev-engine`      | fleetbase/dev-engine      |

Initialize for local development:

```bash
cd apps/fleetbase && git submodule update --init --recursive
```

---

## Recommended Porterchain extensions

### 1. `porterchain-bridge` (PHP — **priority**)

**Purpose:** Implement `/int/v1/porterchain/*` routes expected by Porterchain API.

| Endpoint                               | Handler responsibility                                       |
| -------------------------------------- | ------------------------------------------------------------ |
| `POST porterchain/orders`              | Map Porterchain payload → Fleetbase Order + Payload + Places |
| `POST porterchain/drivers`             | Upsert driver; set `meta.porterchain_driver_id`              |
| `POST porterchain/vehicles`            | Upsert vehicle                                               |
| `GET porterchain/orders/{id}/tracking` | Aggregate tracker + positions                                |

**Package structure (standard Fleetbase extension):**

```
porterchain-bridge/
├── composer.json          # type: library, extra.laravel.providers
├── server/src/
│   ├── Providers/PorterchainBridgeServiceProvider.php
│   ├── Http/Controllers/Internal/v1/PorterchainOrderController.php
│   ├── Http/Middleware/VerifyPorterchainServiceKey.php
│   └── routes.php
└── extension.json         # Fleetbase extension manifest
```

**Registration:** Add to `api/composer.json` repositories + require, or install via registry after publishing.

**Auth middleware:** Validate `PORTERCHAIN_DISPATCHER_API_KEY` or dedicated service Bearer — separate from merchant Clerk auth.

### 2. Porterchain webhook consumer ✅ **Implemented**

| Location | `apps/api/.../routers/webhooks.py` |
| -------- | ---------------------------------- |
| Route | `POST /webhooks/fleetbase` |
| Verify | HMAC via `FLEETBASE_WEBHOOK_SECRET` |
| Process | `fleetbase_engine/WebhookProcessor` |

Configure endpoint URL in Fleetbase dev console — no Fleetbase code change required.

### 3. Optional: `porterchain-ops-engine` (Ember — low priority)

**Purpose:** Ops-specific widgets in Fleetbase console (Porterchain branding, quick links).

Only needed if standard FleetOps UI is insufficient. **Not required for MVP** — use stock `@fleetbase/fleetops-engine`.

---

## Extension points in upstream code

### PHP service providers

| Provider                       | Package      | Registers                   |
| ------------------------------ | ------------ | --------------------------- |
| `CoreServiceProvider`          | core-api     | Core routes, models, macros |
| `FleetOpsServiceProvider`      | fleetops-api | FleetOps routes, migrations |
| `EventServiceProvider`         | both         | Event ↔ listener map        |
| `SocketClusterServiceProvider` | core-api     | Broadcasting                |

**Hook pattern:** Publish a package that adds:

- `routes.php` loaded in `ServiceProvider::boot()`
- Event listeners via `$this->app['events']->listen(...)` in your provider
- Migrations in `server/migrations/`

### Route macro

`$router->fleetbaseRoutes('resource', $callback)` — generates REST CRUD. Extensions can add custom routes alongside.

### Order meta / custom fields

| Approach                  | Use                                                        |
| ------------------------- | ---------------------------------------------------------- |
| `orders.meta` JSON        | `porterchain_order_id`, `merchant_org_id` (zero migration) |
| `fleetbase_custom_fields` | Structured Porterchain fields visible in console           |
| `order_configs`           | Custom workflow activities for Porterchain order types     |

**Recommended:** `meta` JSON for bridge IDs — simplest, no schema change.

### Ember extension registry

Console loads extensions via:

- `console/app/instance-initializers/load-extensions.js`
- `universe/extension-manager` service from `@fleetbase/ember-core`
- `initialize-registries.js` — UI injection points (`@fleetbase/console`, `auth:login`)

Publish Ember engine only if Porterchain-specific console UI is needed.

---

## Integration patterns (ranked)

| Pattern                         | Modify Fleetbase? | Upgrade risk | Best for                        |
| ------------------------------- | ----------------- | ------------ | ------------------------------- |
| **A. Consumable `v1` API only** | No                | Lowest       | MVP — use today                 |
| **B. PHP extension package**    | No (add package)  | Low          | Tailored bridge payloads        |
| **C. Webhooks → Porterchain**   | No                | Low          | Status sync                     |
| **D. Fork fleetops/core-api**   | Yes               | High         | Avoid                           |
| **E. Direct MySQL access**      | No                | Medium       | Avoid — bypasses business logic |

**Porterchain policy:** A + B + C. Never D or E.

---

## Pattern A — Use standard API today

Until `porterchain-bridge` extension ships:

```http
POST /v1/orders
Authorization: Bearer flb_live_xxx
Content-Type: application/json

{
  "pickup": { "address": "...", "location": [lng, lat] },
  "dropoff": { "address": "...", "location": [lng, lat] },
  "scheduled_at": "2026-06-29T14:00:00Z",
  "meta": { "porterchain_order_id": "ord_123" }
}
```

Create API credential in Fleetbase console → Developer → API Keys (`@fleetbase/dev-engine`).

---

## Pattern B — Extension install flow

### Development (Composer path)

1. Create `packages/porterchain-bridge/` (or separate repo)
2. Add path repository to `api/composer.json`
3. `composer require porterchain/bridge-api`
4. `php artisan migrate` (if migrations)
5. Rebuild Docker image OR mount package into container

### Production (Registry path)

1. Publish extension to Fleetbase registry (or private registry)
2. `php artisan registry:init` (already in deploy.sh)
3. Install via console → Extensions
4. `php artisan extension:install porterchain/bridge-api`

---

## Pattern C — Webhook registration

1. Fleetbase console → Developer → Webhooks
2. URL: `https://api.porterchain.com/v1/webhooks/fleetbase`
3. Events: `order.dispatched`, `order.driver_assigned`, `order.completed`, `order.canceled`
4. Mode: `live`
5. Store signing secret in Porterchain env

---

## Environment extension points

Fleetbase reads Porterchain-specific env vars (already in `env/fleetbase.env.example`):

| Variable                                     | Extension point                            |
| -------------------------------------------- | ------------------------------------------ |
| `PORTERCHAIN_API_URL`                        | Reverse HTTP callbacks to Porterchain      |
| `PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID` | Default tenant for bridge                  |
| `PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE`      | Feature flag                               |
| `PORTERCHAIN_DISPATCHER_API_KEY`             | Authenticate Porterchain → Fleetbase calls |
| `ROUTING_ENGINE=valhalla`                    | Shared routing with Porterchain Valhalla   |
| `BRANDING_*_URL`                             | White-label console                        |

These are **configuration extensions** — no code fork required.

---

## Docker extension points

| File                                                       | Purpose                           |
| ---------------------------------------------------------- | --------------------------------- |
| `docker-compose.yml`                                       | Upstream services                 |
| `docker-compose.override.yml`                              | Secrets (gitignored)              |
| `infrastructure/docker/fleetbase.porterchain.override.yml` | Porterchain ports, volumes, names |

Add Porterchain bridge container only if needed — current design uses Porterchain API as client.

---

## Console UI extension points

| Registry key         | Inject                                          |
| -------------------- | ----------------------------------------------- |
| `@fleetbase/console` | Sidebar items, header widgets                   |
| `auth:login`         | Custom login branding (already branded via env) |
| Dashboard widgets    | `initialize-widgets.js` pattern                 |

FleetOps routes are mounted by `@fleetbase/fleetops-engine` — not in local `router.js`.

---

## Order workflow extension

`fleetbase_order_configs` define activity flows:

- Add Porterchain-specific activities (e.g. `await_porterchain_payment`)
- Configure via console → FleetOps → Order Configs
- Or seed via extension migration

Use when Fleetbase dispatch must wait for Porterchain state gates.

---

## Notification extension

| Layer       | Extension                                                      |
| ----------- | -------------------------------------------------------------- |
| FleetOps    | `fleet-ops/settings/notification-settings`                     |
| Core        | `settings/notification-channels-config`                        |
| Porterchain | Replace customer emails; keep driver FCM in Fleetbase optional |

Register Porterchain ops email in Fleetbase notifiables for dispatch failures only.

---

## Testing extensions

| Test               | Command                                                             |
| ------------------ | ------------------------------------------------------------------- |
| Route registered   | `php artisan route:list \| grep porterchain`                        |
| Package discovered | `php artisan package:discover`                                      |
| Webhook fire       | Dispatch order in console → check `webhook-request-logs`            |
| Bridge round-trip  | Porterchain `ORDER_DISPATCH_READY` → verify `fleetbase_orders.meta` |

---

## AGPL guidance

| Allowed                                                | Avoid                                             |
| ------------------------------------------------------ | ------------------------------------------------- |
| Separate `porterchain-bridge` package (your copyright) | Embedding proprietary code inside forked fleetops |
| API-only integration                                   | Distributing modified Fleetbase without source    |
| Private extension registry                             | Removing AGPL notices                             |
| Running Fleetbase internal-only                        | Exposing Fleetbase UI to merchants                |

If you modify Fleetbase packages, you must comply with AGPL source distribution requirements.

---

## Implementation status (July 2026)

| Phase | Deliverable | Status |
| ----- | ----------- | ------ |
| **Now** | `v1` API bridge (`POST /v1/orders`, drivers, vehicles) | ✅ Production |
| **Now** | Fleetbase webhook → Porterchain handler | ✅ Implemented |
| **Now** | Driver/vehicle outbound sync on admin approval | ✅ Implemented |
| **Next** | `porterchain-bridge` PHP extension (SSO + tailored payloads) | ⚠️ SSO client exists; extension deploy needed |
| **Future** | Custom order config for retail vs B2B | Roadmap |

---

## Related documents

- [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)
- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [EVENT_CATALOG.md](./EVENT_CATALOG.md)
- [FLEETBASE_INSTALL.md](./FLEETBASE_INSTALL.md)
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
