# Doppler & Environment Audit

**Type:** CANONICAL
**Owner:** Platform
**Last verified:** 2026-07-07

This report audits how environment variables / secrets flow through Doppler for
the Porterchain platform, documents the **required keys per app**, and lists
concrete cleanup actions (missing / unused / misnamed / duplicate / incorrectly
scoped secrets) plus a standardized naming convention.

> No secret **values** are included here. This is a names-and-wiring audit only.

---

## 1. How secrets flow (Doppler)

| Stage                    | Mechanism                                                                                                                                                                                               |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Source of truth**      | Doppler project `pcd`, config `prd` (`doppler.yaml`)                                                                                                                                                    |
| **CI → host**            | `DOPPLER_TOKEN` (+ `DOPPLER_PROJECT`/`DOPPLER_CONFIG`) in GitHub Actions; `deploy.yml` SSHes to the host                                                                                                |
| **Host materialization** | `infrastructure/deploy/sync-secrets.sh` runs `doppler secrets download` → writes `/opt/porterchain/.env` (chmod 600) and extracts `FIREBASE_CREDENTIALS_JSON` → `secrets/firebase-service-account.json` |
| **Runtime**              | `docker-compose.prod.yml` loads `/opt/porterchain/.env` for `${VAR}` substitution and per-service `environment:` blocks                                                                                 |
| **Next.js build**        | `NEXT_PUBLIC_*` injected at build time from GitHub secrets (`deploy.yml`); server-only `CLERK_SECRET_KEY` provided per portal container at runtime                                                      |
| **Dev**                  | `env/*.example` → local `.env` / `.env.local`; `env/clerk.env` + `pnpm clerk:sync`; `packages/config/monorepo-env.mjs` centralizes Next.js env injection                                                |
| **Break-glass**          | `doppler run -- <cmd>` (documented in `infrastructure/deploy/SECRETS.md`), not used in CI/Docker                                                                                                        |

**Centralization points**

- **Frontend:** `packages/config/monorepo-env.mjs` — `loadMonorepoEnv()`, `clerkKeysForPortal(portal)`, `*PublicEnv()`. `CLERK_SECRET_KEY` is deliberately excluded from public blocks (server-only). ✅
- **Backend:** two Pydantic settings layers — `apps/api/.../config.py` (`Settings`) and `shared/python/.../config/settings.py` (`PlatformSettings`). Startup now **fails fast** on missing required secrets via `apps/api/.../startup_checks.py`.

---

## 2. Required keys per app

Legend: **R** = required in production, **O** = optional/feature-flag, **build** = inlined at build, **runtime** = server-only.

### Backend API + Worker (server-only, from Doppler → `/opt/porterchain/.env`)

| Key                                                                                                          | Req          | Group        | Notes                                                            |
| ------------------------------------------------------------------------------------------------------------ | ------------ | ------------ | ---------------------------------------------------------------- |
| `APP_ENV`, `APP_DEBUG`, `LOG_LEVEL`                                                                          | R            | Core         | `APP_ENV` gates fail-fast + dev bypass                           |
| `DATABASE_URL`                                                                                               | R            | Database     | must be `postgresql+psycopg://…`; local default rejected in prod |
| `REDIS_URL`                                                                                                  | R (prod)     | Redis/Queue  | in-memory fallback only when `APP_ENV=local`                     |
| `JWT_SECRET`                                                                                                 | R            | Auth         | driver/SSO token signing; non-default enforced in prod           |
| `CLERK_SECRET_KEY` + `CLERK_JWKS_URL` **or** `CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_SECRET_KEY`+`_JWKS_URL` | R            | Clerk        | legacy single-app or enterprise 4-app                            |
| `STRIPE_SECRET`, `STRIPE_WEBHOOK_SECRET`                                                                     | R            | Payments     | required by `sync-secrets.sh`                                    |
| `GOOGLE_MAPS_API_KEY`                                                                                        | R            | Maps         | **see naming issue #3 (`_SERVER_` vs `_API_`)**                  |
| `ROUTING_ENGINE`, `VALHALLA_BASE_URL`, `OSRM_HOST`                                                           | R            | Routing      | Valhalla primary, OSRM fallback                                  |
| `CORS_ORIGINS`, portal URLs (`*_PORTAL_URL`, `WEBSITE_URL`)                                                  | R            | Core         |                                                                  |
| `MAIL_HOST`/`MAIL_PORT`/`MAIL_USERNAME`/`MAIL_PASSWORD`/`MAIL_FROM_*`                                        | R (if email) | Email        | **not yet in prod compose / Doppler table (gap #1)**             |
| `SENTRY_DSN`                                                                                                 | O            | Logging      | recommended; currently a documented gap                          |
| `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_JSON`, `PORTERCHAIN_PUSH_*`                                     | O            | Push         | file mounted at `/run/secrets/firebase-service-account.json`     |
| `ZOHO_CALENDAR_*`                                                                                            | O            | Integrations | CRM calendar sync                                                |
| `FLEETBASE_*`                                                                                                | O            | Integrations | dispatch bridge default off                                      |

### Next.js portals (Admin / Merchant / Driver / Customer / Website)

| Key                                                                                                   | Scope          | Req      | Notes                        |
| ----------------------------------------------------------------------------------------------------- | -------------- | -------- | ---------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`                                                                   | build/client   | R        | publishable — safe to expose |
| `CLERK_SECRET_KEY`                                                                                    | runtime/server | R        | **never** `NEXT_PUBLIC_`     |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`                                                                     | build/client   | R        | API base                     |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`                                                                     | build/client   | R (maps) | browser-restricted key       |
| `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_*_PORTAL_URL`, `NEXT_PUBLIC_WEBSITE_URL`                         | build/client   | R/O      | cross-portal links           |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` / redirect vars                                                       | build/client   | R        | per-portal                   |
| `NEXT_PUBLIC_SENTRY_DSN`                                                                              | build/client   | O        | client DSN                   |
| Website server-only: `GOOGLE_MAPS_SERVER_API_KEY`, `ROUTING_ENGINE`, `VALHALLA_BASE_URL`, `OSRM_HOST` | runtime        | R        | not `NEXT_PUBLIC_` ✅        |

### Mobile (Expo)

`EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`, `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`, `EXPO_PUBLIC_APP_ENV`, `EXPO_PUBLIC_APP_KIND` (build-time public); EAS submit secrets separate.

---

## 3. Findings

### 3.1 Missing (referenced in code but absent from `env/*.example` / Doppler docs)

| Key(s)                                                                                                                                                                               | Group         | Action                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------- | --------------------------------------------------------------------------------------------------------------------- |
| `MAIL_*` / SMTP                                                                                                                                                                      | Email         | Add to Doppler + `docker-compose.prod.yml` if transactional email is required in prod (today it degrades to log-only) |
| `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`                                                                                                                                               | Logging       | Add to Doppler (already flagged in `PRIORITY_TODOS.md`)                                                               |
| `ZOHO_CALENDAR_*`                                                                                                                                                                    | Integrations  | Add to Doppler prod table if CRM calendar sync is enabled                                                             |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `PORTERCHAIN_VERSION`                                                                                                                                 | Observability | Add to templates; optional                                                                                            |
| `GOOGLE_MAPS_API_KEY` (API)                                                                                                                                                          | Maps          | Not present in API prod compose `environment:` block — **add it** (see #3.3)                                          |
| API tuning: `QUOTE_TTL_MINUTES`, `BOOKING_DRAFT_TTL_MINUTES`, `PRICING_CLIENT_TOLERANCE_*`, `ENABLE_DRIVER_AUTO_REOPTIMIZE`                                                          | Core          | Have code defaults; document in `env/api.env.example`                                                                 |
| SSO: `SSO_JWT_SECRET`, `SSO_TOKEN_TTL_SECONDS`, `JWT_ACCESS_TTL_MINUTES`, `JWT_REFRESH_TTL_DAYS`                                                                                     | Auth          | Document; have defaults                                                                                               |
| Frontend: `NEXT_PUBLIC_ALLOW_STRIPE_MOCK`, `NEXT_PUBLIC_DRIVER_DEV_LOGIN`, `NEXT_PUBLIC_ADMIN_URL`, `NEXT_PUBLIC_FLEETBASE_*`, `NEXT_PUBLIC_VALHALLA_URL`, `NEXT_PUBLIC_MAILHOG_URL` | Frontend      | Document or remove (dev-only)                                                                                         |

### 3.2 Unused (in templates but never referenced in application code)

Likely stale or Fleetbase-only — candidates for pruning from `env/api.env.example`:

- Payments: `STRIPE_KEY`, `PORTERCHAIN_STRIPE_SUCCESS_URL`, `PORTERCHAIN_STRIPE_CANCEL_URL`, `PORTERCHAIN_RETAIL_*` (code uses `RETAIL_CHECKOUT_*`), `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- Maps: `GOOGLE_MAPS_BROWSER_API_KEY`, `GOOGLE_MAPS_LOCALE` (API reads `GOOGLE_MAPS_API_KEY` only)
- Email: `PORTERCHAIN_FROM_*`, `PORTERCHAIN_TRACKING_URL`, `PORTERCHAIN_OPS_EMAILS`, `MAIL_MAILER`, `MAIL_ENCRYPTION`, worker `SMTP_*` (worker email uses `MAIL_*`)
- Driver onboarding: `DRIVER_APP_*`, `DRIVER_INVITE_*`, `AUTH_DRIVER_*`
- Fleetbase: `PORTERCHAIN_DISPATCHER_API_KEY`, `PORTERCHAIN_FLEETBASE_DRIVER_JOB_BRIDGE`, `PORTERCHAIN_FLEETBASE_ASSIGNMENT_REQUIRED`
- Other: `PUBLIC_INGEST_API_KEY`, `DIGITALOCEAN_API_TOKEN`, `REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD` (API uses `REDIS_URL`)

> Verify each against a full-text search before deleting; some are read by Fleetbase (Laravel) or deploy scripts rather than the Python/Next apps.

### 3.3 Misnamed / inconsistent

| Issue                   | Detail                                                                                                 | Recommended                                                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Maps server key**     | Templates/Doppler use `GOOGLE_MAPS_SERVER_API_KEY`; API `PlatformSettings` reads `GOOGLE_MAPS_API_KEY` | Add `AliasChoices("GOOGLE_MAPS_API_KEY","GOOGLE_MAPS_SERVER_API_KEY")` or standardize on one name; ensure the API prod compose passes it |
| **Admin portal URL**    | driver-portal read `NEXT_PUBLIC_ADMIN_URL`; rest of repo uses `NEXT_PUBLIC_ADMIN_PORTAL_URL`           | **Fixed** in code (prefers standard, falls back). Standardize on `NEXT_PUBLIC_ADMIN_PORTAL_URL` and update the driver Dockerfile ARG     |
| **Zoho typo aliases**   | Code also accepts legacy `ZOHO_CALANDER_*` (misspelled)                                                | Standardize on `ZOHO_CALENDAR_*`; drop the typo aliases after migration                                                                  |
| **Worker SMTP vs MAIL** | `worker.env.example` documents `SMTP_*`, code reads `MAIL_*`                                           | Align the worker template to `MAIL_*`                                                                                                    |

### 3.4 Duplicate / overlapping

- `Settings` (API) and `PlatformSettings` (shared) both read `APP_ENV`, `SENTRY_DSN`, routing, etc. — acceptable, but the split is a source of drift; consider a single settings source over time.
- `FLEETBASE_DISPATCH_BRIDGE` vs `PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE` (aliased in code) — pick one.
- `RETAIL_CHECKOUT_*` (code) vs `PORTERCHAIN_RETAIL_*` (templates) — consolidate.

### 3.5 Client-exposure safety ✅

- No server-only secret is exposed via `NEXT_PUBLIC_*`. `CLERK_SECRET_KEY`, `STRIPE_SECRET`, `JWT_SECRET`, DB creds are server-only.
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` (browser-restricted), `NEXT_PUBLIC_SENTRY_DSN`, and feature flags are safe to expose.
- **Watch:** `website/src/lib/quote/geocode.ts` falls back to the browser Maps key for server geocoding if the server key is unset — a misconfiguration risk (not a client leak). Prefer failing if `GOOGLE_MAPS_SERVER_API_KEY` is missing server-side.
- **Note:** deploy docs reference a Clerk **test** instance (`relaxing-warthog-11`); confirm production uses production Clerk instances.

---

## 4. Recommended standardized naming convention

- **Server-only secrets:** no prefix (e.g. `STRIPE_SECRET`, `CLERK_SECRET_KEY`, `JWT_SECRET`).
- **Client-exposed (Next.js):** `NEXT_PUBLIC_<DOMAIN>_<NAME>` and MUST be non-sensitive.
- **Client-exposed (Expo):** `EXPO_PUBLIC_<DOMAIN>_<NAME>`.
- **Portal URLs:** `NEXT_PUBLIC_<PORTAL>_PORTAL_URL` (e.g. `NEXT_PUBLIC_ADMIN_PORTAL_URL`) — deprecate `NEXT_PUBLIC_ADMIN_URL`.
- **Per-portal Clerk (enterprise):** `CLERK_<PORTAL>_{PUBLISHABLE_KEY,SECRET_KEY,JWKS_URL}`.
- **Maps:** `GOOGLE_MAPS_SERVER_API_KEY` (server) and `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` (browser); retire the ambiguous `GOOGLE_MAPS_API_KEY` after adding an alias.
- **Feature flags:** boolean, explicit, e.g. `FLEETBASE_DISPATCH_BRIDGE`, `PORTERCHAIN_PUSH_ENABLED`.

---

## 5. Startup validation

`apps/api/src/porterchain_api/startup_checks.py` runs at API startup and refuses
to boot when required secrets are missing outside `APP_ENV=local`, reporting all
missing keys at once:

```
Refusing to start: missing required configuration for APP_ENV='production'.
Set these via Doppler (see docs/DOPPLER_AUDIT.md): STRIPE_SECRET, ...
```

Currently enforced: `DATABASE_URL` (non-local), `JWT_SECRET`, `STRIPE_SECRET`,
`STRIPE_WEBHOOK_SECRET`, and Clerk (legacy or enterprise). Extend
`collect_missing_required()` as more secrets become hard requirements (e.g.
`REDIS_URL`, `GOOGLE_MAPS_API_KEY`) once they are guaranteed in Doppler.

---

## 6. Action checklist

- [ ] Add `MAIL_*`/SMTP + `SENTRY_DSN` + `NEXT_PUBLIC_SENTRY_DSN` to Doppler `prd` and prod compose.
- [ ] Add `GOOGLE_MAPS_API_KEY` alias for `GOOGLE_MAPS_SERVER_API_KEY`; pass to API prod compose.
- [ ] Standardize `NEXT_PUBLIC_ADMIN_PORTAL_URL` (update driver Dockerfile ARG/ENV).
- [ ] Consolidate `RETAIL_CHECKOUT_*` vs `PORTERCHAIN_RETAIL_*`; drop unused `STRIPE_KEY`.
- [ ] Remove Zoho `ZOHO_CALANDER_*` typo aliases after migration.
- [ ] Prune confirmed-unused template vars (§3.2) after a full-text search.
- [ ] Confirm production Clerk instances (not the `relaxing-warthog-11` test instance).
- [ ] Prefer failing over browser-key fallback in `website/src/lib/quote/geocode.ts`.
