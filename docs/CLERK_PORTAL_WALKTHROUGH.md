# Clerk portal login walkthrough (§0.4.10)

**Type:** CANONICAL  
**Checklist:** §0.4.10 · PRIORITY_TODOS #1  
**Last verified:** 2026-07-08 (local dev layer)  
**Keys:** Local = test (`env/clerk.env`); Prod = live (Doppler — deferred)

## Prerequisites

```bash
pnpm docker:up
pnpm db:migrate
pnpm dev:api
pnpm dev          # website :3000, portals via turbo
# Optional: pnpm dev:worker
pnpm clerk:sync   # after editing env/clerk.env
cd apps/api && PYTHONPATH=src python scripts/seed_dev_portal_users.py
```

Local API: `CLERK_DEV_BYPASS=true` · Portals: `NEXT_PUBLIC_CLERK_DEV_BYPASS=true` (Bearer `dev`).

For real Clerk JWT testing: set bypass `false`, run `pnpm clerk:sync`, restart portals.

## Walkthrough matrix (local dev — 2026-07-08)

| Portal   | URL                   | Clerk app (test)    | API access check                       | Sign-in         | API gate | Notes                                     |
| -------- | --------------------- | ------------------- | -------------------------------------- | --------------- | -------- | ----------------------------------------- |
| Admin    | http://localhost:3002 | relaxing-warthog-11 | `GET /v1/auth/admin/access` → 200      | [x] dev bypass  | [x] 200  | Dashboard center loads after `_deps` fix  |
| Merchant | http://localhost:3001 | noted-jaguar-86     | `GET /v1/merchant/dashboard` → 200     | [x] dev bypass  | [x] 200  | Open `/dashboard` directly in dev mode    |
| Customer | http://localhost:3004 | up-leopard-98       | `GET /v1/customers/me/dashboard` → 200 | [x] dev bypass  | [x] 200  | Auto-provisions customer from dev claims  |
| Driver   | http://localhost:3003 | secure-urchin-81    | `GET /driver-api/v1/dashboard` → 200   | [x] email login | [x] 200  | Use `marco@porterchain.com` (seed script) |
| Website  | http://localhost:3000 | (customer keys)     | quote + track anonymous OK             | [x] N/A         | N/A      | Marketing only                            |

### API gate smoke (dev bypass)

```bash
API=http://localhost:8001
H="Authorization: Bearer dev"

curl -s -o /dev/null -w "admin %{http_code}\n" -H "$H" "$API/v1/auth/admin/access"
curl -s -o /dev/null -w "merchant %{http_code}\n" -H "$H" "$API/v1/merchant/dashboard"
curl -s -o /dev/null -w "customer %{http_code}\n" -H "$H" "$API/v1/customers/me/dashboard"
curl -s -o /dev/null -w "driver %{http_code}\n" "$API/driver-api/v1/dashboard"
# Expected: all 200
```

```bash
curl -s http://localhost:8001/health/ready | python3 -m json.tool | grep -A6 clerk
# clerk_mode: enterprise · all 4 apps ok
```

## Steps per portal

1. Open URL → Clerk sign-in (or dev bypass)
2. Confirm dashboard loads (no CORS/500 in console)
3. DevTools → Network → API call returns 200 with JSON body
4. Check `/health/ready` shows `clerk_mode: enterprise` when all 4 JWKS configured

## Dev fixes applied (2026-07-08)

| Issue                                    | Fix                                                            |
| ---------------------------------------- | -------------------------------------------------------------- |
| Merchant 500 `_dashboard` not defined    | `__all__` in `routers/merchant/_deps.py`                       |
| Customer/merchant 403 clerk_app_mismatch | Skip app check for `dev_clerk_user` in `portal_guard.py`       |
| Driver 500 recursion                     | Alias `guard_portal_ready` import in `routers/driver/_deps.py` |

## Prod verification (deferred)

Prod sign-in matrix runs after dev layer complete:

```bash
pnpm validate:p0:prod
curl -fsS https://api.porterchain.com/health/ready | jq '.clerk_mode, .clerk_apps'
bash scripts/verify-clerk.sh   # on droplet
```

Record prod results in a separate prod pass (date + tester + screenshot path).
