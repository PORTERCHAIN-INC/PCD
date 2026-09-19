# Admin portal P0 e2e

## Auth (staff IdP)

Admin no longer uses Clerk on the shell. Playwright needs one of:

1. **Cookie jar** (preferred for live staff handshake)

```bash
mkdir -p e2e/.auth
pnpm exec playwright codegen http://localhost:3002/dashboard \
  --save-storage=e2e/.auth/staff.json
```

2. **Sid inject** — copy `pc_staff_sid` from a signed-in browser DevTools → Application → Cookies

```bash
ADMIN_STAFF_SID='staff_sess_…' ADMIN_RUN_LIVE=1 pnpm test:e2e:leads
```

3. **Local bypass** — admin must be running with `NEXT_PUBLIC_CLERK_DEV_BYPASS=true`. Empty storageState is fine; middleware lets the shell through and `AdminAuthProvider` issues Bearer `dev`. BFF stubs still intercept `/api/porterchain/v1/...`.

`.auth/*.json` is gitignored — never commit staff cookies.

## Run

```bash
# Unit/RTL (always; CI)
pnpm test:admin

# API P0
pnpm test:admin-p0:api

# Skeleton + leads e2e (soft-skips UI when :3002 is down)
pnpm test:admin-p0:e2e

# Full P0 bundle (Vitest → API → e2e)
pnpm test:admin-p0

# Live leads UI (hard-fail if portal down)
ADMIN_RUN_LIVE=1 \
ADMIN_STORAGE_STATE=apps/admin/e2e/.auth/staff.json \
pnpm --filter @porterchain/admin test:e2e:leads
```
