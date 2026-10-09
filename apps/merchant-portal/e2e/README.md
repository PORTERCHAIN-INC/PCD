# Merchant portal live e2e (P0 golden path)

## What this proves

1. **Dispatcher** Clerk seat can preview (`routing_source` ∈ valhalla|osrm|haversine) and sandbox-confirm.
2. **Viewer** Clerk seat soft-forbids `/book` (ModuleGate) and gets API 403 on preview.
3. Day-plan / optimize enqueue after _live_ (non-sandbox) confirm is asserted in pytest `MP-BOOK-004`.

## One-time setup

```bash
# From repo root — installs Chromium for the merchant-portal Playwright version
pnpm test:merchant-p0:e2e:install
```

## Capture storage jars

**Prerequisite:** merchant portal must already answer on `:3001` (step 1 browsers alone is not enough).

```bash
# Terminal A — start portal (leave running)
pnpm --filter @porterchain/merchant-portal dev

# Confirm it answers (should print 200/307/302 quickly)
curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 http://127.0.0.1:3001/sign-in

# Terminal B — capture jars (opens a browser; sign in, then close the window)
pnpm run test:e2e:codegen:dispatcher   # OPS / dispatcher seat
pnpm run test:e2e:codegen:viewer       # READONLY / viewer seat

# Confirm jars exist (non-empty)
ls -la apps/merchant-portal/e2e/.auth/
```

## Run

```bash
# CI / always: API golden + offline contracts (no browser auth)
pnpm test:merchant-p0

# Live golden (only runs if jar files exist — otherwise skips cleanly)
cd apps/merchant-portal
MERCHANT_E2E_LIVE=1 \
MERCHANT_STORAGE_STATE_DISPATCHER=e2e/.auth/dispatcher.json \
MERCHANT_STORAGE_STATE_VIEWER=e2e/.auth/viewer.json \
pnpm test:e2e:live
```

Or from repo root (paths relative to `apps/merchant-portal` cwd):

```bash
MERCHANT_E2E_LIVE=1 \
MERCHANT_STORAGE_STATE_DISPATCHER=e2e/.auth/dispatcher.json \
MERCHANT_STORAGE_STATE_VIEWER=e2e/.auth/viewer.json \
pnpm test:merchant-p0:live
```

Do **not** paste comment lines (`# ...`) into the same shell paste as commands on zsh.

## Local stack without Clerk jars

Against the local dev stack (merchant portal dev auth, Bearer `dev`), dispatcher/owner journeys
and the page smoke tests run without a storage state:

```bash
MERCHANT_E2E_LIVE=1 MERCHANT_E2E_LOCAL_BYPASS=1 pnpm --filter @porterchain/merchant-portal exec playwright test
```

Viewer-role checks (MP-AUTH-006, viewer persona) still need `MERCHANT_STORAGE_STATE_VIEWER`.
Never use the bypass against staging or production.
