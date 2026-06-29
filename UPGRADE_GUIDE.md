# Fleetbase Upgrade Guide

**Document version:** 1.0  
**Date:** June 29, 2026  
**Current Fleetbase version:** v0.7.40  
**Adapter package:** `services/fleetbase-adapter/`

---

## Overview

Fleetbase is an upstream dependency at `apps/fleetbase/`. Porterchain integrates exclusively through `services/fleetbase-adapter/`. When upgrading Fleetbase, update the clone — not Porterchain business logic inside Fleetbase.

---

## Pre-upgrade checklist

- [ ] Read Fleetbase release notes and changelog
- [ ] Note locked Composer package versions in `apps/fleetbase/api/composer.lock`
- [ ] Export current Fleetbase API key and company UUID
- [ ] Snapshot MySQL `fleetbase` database (if production data exists)
- [ ] Run Porterchain API integration smoke tests against current version
- [ ] Review [FLEETBASE_ANALYSIS.md](./FLEETBASE_ANALYSIS.md) for breaking changes

---

## Upgrade procedure

### 1. Update the Fleetbase clone

```bash
cd apps/fleetbase
git fetch --tags
git checkout v0.7.41   # example target tag
```

**Do not** cherry-pick Porterchain changes into `apps/fleetbase/`.

### 2. Rebuild Docker stack

```bash
pnpm docker:fleetbase:down
pnpm docker:fleetbase:up
pnpm docker:fleetbase:verify
```

Review `infrastructure/docker/fleetbase.porterchain.override.yml` for port/env compatibility.

### 3. Verify API compatibility

Check these adapter endpoints still work:

| Endpoint                         | Service           |
| -------------------------------- | ----------------- |
| `POST /v1/orders`                | `OrderService`    |
| `GET /v1/orders/{id}/tracker`    | `TrackingService` |
| `PATCH /v1/orders/{id}/dispatch` | `DispatchService` |
| `GET /v1/orders/{id}/proofs`     | `PodService`      |
| Webhook HMAC format              | `WebhookService`  |

```bash
# With Fleetbase running and API key configured:
cd apps/api && source .venv/bin/activate
python -c "
from porterchain_fleetbase_adapter import FleetbaseAdapter, FleetbaseSettings
a = FleetbaseAdapter(FleetbaseSettings(api_key='YOUR_KEY'))
print('enabled:', a.is_enabled)
"
```

### 4. Update adapter if needed

| Change type            | Files to update                               |
| ---------------------- | --------------------------------------------- |
| New order fields       | `mappers.py` → `build_order_payload`          |
| Renamed webhook events | `events/__init__.py` → `FLEETBASE_EVENT_TO_*` |
| New API paths          | Relevant service module in adapter            |
| Auth header changes    | `client/__init__.py`                          |
| Version header         | `config.py` → `api_version`                   |

### 5. Update bridge extension (if deployed)

Porterchain-specific routes (`/int/v1/porterchain/*`) live in a separate Fleetbase extension — not in upstream OSS. Upgrade the extension package independently:

- SSO exchange: `/int/v1/porterchain/sso/exchange`
- Permission sync: `/int/v1/porterchain/sso/users/{uuid}/permissions`

### 6. Run Porterchain smoke tests

```bash
pnpm dev:api          # :8001
# POST order → verify fleetbase_order_id persisted
# POST /webhooks/fleetbase → verify state transition
# GET /v1/orders/{tracking}/tracking → verify snapshot
```

---

## Version compatibility

`FleetbaseClient` sends `X-Fleetbase-Version: v1`. If Fleetbase responds with a different version header, the client logs a warning. Treat repeated warnings as a signal to review adapter mappers.

Document supported Fleetbase versions in `services/fleetbase-adapter/README.md` after each upgrade.

---

## Composer lock reference (v0.7.40)

| Package                  | Version |
| ------------------------ | ------- |
| `fleetbase/core-api`     | 1.6.47  |
| `fleetbase/fleetops-api` | 0.6.48  |

After upgrade, diff `composer.lock` and check FleetOps release notes for order/driver API changes.

---

## Rollback

```bash
cd apps/fleetbase
git checkout v0.7.40
pnpm docker:fleetbase:down
pnpm docker:fleetbase:up
```

Restore MySQL snapshot if schema migrations ran.

---

## What NOT to do during upgrade

| Action                                   | Why                                 |
| ---------------------------------------- | ----------------------------------- |
| Patch files in `apps/fleetbase/api/`     | Lost on next upstream pull          |
| Add Porterchain routes to Fleetbase core | Use extension package               |
| Change Fleetbase console for merchants   | Merchants use Porterchain portals   |
| Skip adapter testing                     | Silent payload/event mapping breaks |

---

## Post-upgrade documentation

After a successful upgrade, update:

1. `FLEETBASE_ANALYSIS.md` — version number and lock table
2. `FLEETBASE_APIS.md` — any endpoint changes
3. `FLEETBASE_EVENTS.md` — webhook event changes
4. This guide — current version row

---

## Related documents

- [FLEETBASE_INSTALL.md](./FLEETBASE_INSTALL.md)
- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [EXTENSION_GUIDE.md](./EXTENSION_GUIDE.md)
- [vendor/fleetbase/README.md](./vendor/fleetbase/README.md)
