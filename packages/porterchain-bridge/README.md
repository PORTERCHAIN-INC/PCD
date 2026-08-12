# PorterChain ↔ Fleetbase bridge (`porterchain-bridge`)

**Type:** CANONICAL extension package (not upstream Fleetbase)  
**Authority:** [SSO.md](../../SSO.md) · [FLEETBASE_MODULES.md](../../FLEETBASE_MODULES.md)

## Why this exists

PorterChain Admin issues a short-lived SSO JWT and opens:

`{FLEETBASE_CONSOLE_URL}/porterchain/sso?token=…`

Fleetbase must:

1. Validate the JWT (`POST /int/v1/porterchain/sso/exchange`)
2. Provision/find the console user (no password)
3. Return a Sanctum token so the Ember console can `manuallyAuthenticate`

Without this package, the console falls through to `/auth` (login form).

This code previously lived as **uncommitted** files in the sibling `PC` Fleetbase fork. PCD now owns the permanent copy here.

## Layout

```
packages/porterchain-bridge/
├── composer.json
├── bootstrap.php              # Docker autoload without composer require
├── config/porterchain-sso.php
├── routes/sso.php
├── docker/RouteServiceProvider.php
├── src/
│   ├── Providers/PorterchainBridgeServiceProvider.php
│   ├── Http/Controllers/SsoController.php
│   └── Services/SsoBridgeService.php
└── console/                   # Ember SSO route (synced into apps/fleetbase/console)
    └── app/routes|templates/porterchain/sso.*
```

## Local Docker wiring

`infrastructure/docker/fleetbase.porterchain.override.yml` mounts:

- package → `/fleetbase/api/packages/porterchain-bridge`
- `docker/RouteServiceProvider.php` → Fleetbase `app/Providers/RouteServiceProvider.php`

Console: Ember route lives in `apps/fleetbase/console` (thin sync from this package). Rebuild:

```bash
pnpm docker:fleetbase:up
# after console route changes:
cd apps/fleetbase && docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml up -d --build console
```

## Env (Fleetbase application)

| Variable                                     | Purpose                                             |
| -------------------------------------------- | --------------------------------------------------- |
| `PORTERCHAIN_SSO_JWT_SECRET`                 | Same as PorterChain `JWT_SECRET` / `SSO_JWT_SECRET` |
| `PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID` | Company for provisioned users                       |

## Verify

```bash
curl -sS -X POST http://localhost:8000/int/v1/porterchain/sso/exchange \
  -H 'Content-Type: application/json' -d '{"token":"bad"}'
# expect: {"error":"sso_token_invalid"} (not "There is nothing to see here.")
```
