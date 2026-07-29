# Secrets map — one place, four stores

**Type:** CANONICAL  
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)  
**ADR:** [ADR-013-secrets.md](./architecture/ADR-013-secrets.md)  
**Last verified:** 2026-07-07

Every secret has **one canonical name** and **one owning store**. Other surfaces are copies or build-time inlines — never a second source of truth.

---

## The four stores

| Store                                           | Owns                                                      | Never put here                      |
| ----------------------------------------------- | --------------------------------------------------------- | ----------------------------------- |
| **Local** (`env/*.example` → gitignored `.env`) | Dev keys, Clerk scratch file                              | Production `sk_live_*` long-term    |
| **Doppler** (`pcd` / `prd`)                     | All prod **runtime** secrets                              | `NEXT_PUBLIC_*` (baked into images) |
| **GitHub Actions**                              | Deploy SSH + `DOPPLER_TOKEN` + **build-time** public keys | `sk_*` when Doppler is active       |
| **Server** (`/opt/porterchain/.env`)            | **Generated** on deploy — do not edit                     | Anything (read-only artifact)       |

**Mobile (EAS)** is a fifth surface for store builds only — see [Clerk flow](#clerk-unified-platform-triad) below.

**Unified identity Phase 6:** consumer access matrix + startup validation live in [clerk-doppler-secret-matrix.md](./architecture/clerk-doppler-secret-matrix.md). Local audit: `pnpm config:audit` (names only; does not call Doppler).

---

## Flow (production)

```
env/clerk.env  ──pnpm clerk:sync──►  local app .env files
       │
       ├── upload-clerk-to-doppler.sh ──►  Doppler prd (12 Clerk keys + all runtime)
       └── upload-clerk-to-github.sh  ──►  GitHub (4× pk_* only, for Docker build)

GitHub Deploy workflow
       │
       ├── docker build  ◄── GitHub secrets (NEXT_PUBLIC_*, CLERK_*_PUBLISHABLE_KEY)
       └── ssh droplet   ◄── DOPPLER_TOKEN
                │
                └── sync-secrets.sh ──► /opt/porterchain/.env (mode 600)
                         └── secrets/firebase-service-account.json
```

**Rule:** If `DOPPLER_TOKEN` is set (it is), runtime secrets live in Doppler only. GitHub keeps deploy creds + keys needed at **image build** time.

---

## Secret inventory

### Always in GitHub (deploy + CI)

| Secret           | Purpose                                 |
| ---------------- | --------------------------------------- |
| `DEPLOY_HOST`    | Droplet IP                              |
| `DEPLOY_USER`    | SSH user                                |
| `DEPLOY_SSH_KEY` | SSH private key                         |
| `DEPLOY_PORT`    | Optional, default 22                    |
| `DOPPLER_TOKEN`  | Read-only service token for `pcd`/`prd` |

### GitHub — build-time only (baked into Docker images)

| Secret                            | Used by                       |
| --------------------------------- | ----------------------------- |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | All portals + website         |
| `CLERK_CUSTOMER_PUBLISHABLE_KEY`  | Website, customer portal      |
| `CLERK_MERCHANT_PUBLISHABLE_KEY`  | Merchant portal               |
| `CLERK_ADMIN_PUBLISHABLE_KEY`     | Admin portal                  |
| `CLERK_DRIVER_PUBLISHABLE_KEY`    | Driver portal                 |
| `NEXT_PUBLIC_SENTRY_DSN`          | Portals (optional)            |
| `CLERK_PUBLISHABLE_KEY`           | Legacy fallback → customer pk |

**Not in GitHub when Doppler is active:** `sk_*`, `POSTGRES_PASSWORD`, `JWT_SECRET`, `STRIPE_*`, Firebase JSON, JWKS URLs.

### Doppler (`pcd` / `prd`) — prod runtime

| Secret                                                                         | Notes                                                                           |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `POSTGRES_PASSWORD`                                                            | DB password                                                                     |
| `CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_{SECRET_KEY,PUBLISHABLE_KEY,JWKS_URL}` | Portal slot aliases (same Platform triad after sync)                            |
| `CLERK_PUBLISHABLE_KEY` / `CLERK_SECRET_KEY` / `CLERK_JWKS_URL`                | Platform triad (canonical)                                                      |
| `STRIPE_SECRET`                                                                | `sk_live_…`                                                                     |
| `STRIPE_WEBHOOK_SECRET`                                                        | `whsec_…`                                                                       |
| `JWT_SECRET`                                                                   | `openssl rand -hex 32` — driver sessions + SSO                                  |
| `PUBLIC_INGEST_API_KEY`                                                        | Website inquiries → API CRM leads (`X-Ingest-Key`)                              |
| `GOOGLE_MAPS_SERVER_API_KEY`                                                   | Server geocoding                                                                |
| `FIREBASE_PROJECT_ID`                                                          | e.g. `porterchain-55313`                                                        |
| `FIREBASE_CREDENTIALS_JSON`                                                    | Extracted to file on sync                                                       |
| `FIREBASE_WEB_VAPID_KEY`                                                       | Web push                                                                        |
| `SENTRY_DSN`                                                                   | API errors (optional)                                                           |
| `PORTERCHAIN_PUSH_ENABLED`                                                     | `true`                                                                          |
| `PORTERCHAIN_PUSH_SEND`                                                        | `true`                                                                          |
| `API_REPLICAS`                                                                 | `2`                                                                             |
| `FLEETBASE_*`                                                                  | When bridge enabled (blocked)                                                   |
| `CLERK_WEBHOOK_SIGNING_SECRET`                                                 | Clerk Svix webhook (`POST /webhooks/clerk`) — add when unified webhooks enabled |

**Retired:** divergent 4-app enterprise keys as a supported mode. Slot names remain for dual-read / compose.

### GitHub repository variables (non-secret)

| Variable                   | Default |
| -------------------------- | ------- |
| `DOPPLER_PROJECT`          | `pcd`   |
| `DOPPLER_CONFIG`           | `prd`   |
| `API_REPLICAS`             | `2`     |
| `PORTERCHAIN_PUSH_ENABLED` | `true`  |
| `PORTERCHAIN_PUSH_SEND`    | `true`  |

### Local only

Copy templates from `env/README.md`. Clerk keys: one file `env/clerk.env` → `pnpm clerk:sync`.

| Template                   | Runtime file       |
| -------------------------- | ------------------ |
| `env/api.env.example`      | `apps/api/.env`    |
| `env/clerk.env.example`    | `env/clerk.env`    |
| `env/{portal}.env.example` | `apps/*/env.local` |

---

## Clerk (unified Platform triad)

**Single local source:** `env/clerk.env` (copy from `env/clerk.env.example`).

`CLERK_MODE=enterprise` (4-app / 12-key) is **retired**. Sync is unified-only; requesting enterprise exits with an error — see [clerk-consolidation.md](./runbooks/clerk-consolidation.md).

```bash
cp env/clerk.env.example env/clerk.env
# unified only: CLERK_MODE=unified + CLERK_PUBLISHABLE_KEY / CLERK_SECRET_KEY / CLERK_JWKS_URL
pnpm clerk:sync                          # → all portals + API + mobile .env (expands triad into portal slots)
# Prod Doppler/GitHub upload remains Phase 6+ manual ops — do not run casually
bash infrastructure/deploy/scripts/upload-clerk-to-doppler.sh
bash infrastructure/deploy/scripts/upload-clerk-to-github.sh   # pk_* only
# trigger Deploy workflow
```

| Portal   | Publishable (GitHub build / slot alias) | Secret + JWKS (Doppler runtime / slot alias)           |
| -------- | --------------------------------------- | ------------------------------------------------------ |
| Customer | `CLERK_CUSTOMER_PUBLISHABLE_KEY`        | `CLERK_CUSTOMER_SECRET_KEY`, `CLERK_CUSTOMER_JWKS_URL` |
| Merchant | `CLERK_MERCHANT_PUBLISHABLE_KEY`        | `CLERK_MERCHANT_SECRET_KEY`, `CLERK_MERCHANT_JWKS_URL` |
| Admin    | `CLERK_ADMIN_PUBLISHABLE_KEY`           | `CLERK_ADMIN_SECRET_KEY`, `CLERK_ADMIN_JWKS_URL`       |
| Driver   | `CLERK_DRIVER_PUBLISHABLE_KEY`          | `CLERK_DRIVER_SECRET_KEY`, `CLERK_DRIVER_JWKS_URL`     |

**Canonical Platform triad:**

| Consumer   | Names                                                                                                     |
| ---------- | --------------------------------------------------------------------------------------------------------- |
| Sync / API | `CLERK_MODE=unified`, `CLERK_UNIFIED_MODE`, `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWKS_URL` |
| Next apps  | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (+ server `CLERK_SECRET_KEY`)                                         |
| Expo       | `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` only                                                                  |
| Policy     | `CLERK_AUTHORIZED_PARTIES`, `CLERK_AUTHORIZED_ISSUERS`, `CLERK_AUDIENCE`, `CLERK_WEBHOOK_SIGNING_SECRET`  |

Each portal container maps its `CLERK_{PORTAL}_SECRET_KEY` → `CLERK_SECRET_KEY` at runtime (`docker-compose.prod.yml`). Under unified sync, all portal slots hold the same Platform keys.

Do **not** delete old Clerk apps in Doppler/Clerk dashboard until the retirement checklist + founder approval.

---

## Naming rules (no aliases in prod)

| Canonical                   | Accepts (local/docs only)                      | Notes                                      |
| --------------------------- | ---------------------------------------------- | ------------------------------------------ |
| `JWT_SECRET`                | `SSO_JWT_SECRET`, `PORTERCHAIN_SSO_JWT_SECRET` | One secret; SSO falls back to `JWT_SECRET` |
| `PORTERCHAIN_PUSH_ENABLED`  | `PORTERCHAIN_DRIVER_PUSH_ENABLED`              | Aliased in Python settings                 |
| `FIREBASE_CREDENTIALS_PATH` | —                                              | Local file path                            |
| `FIREBASE_CREDENTIALS_JSON` | —                                              | Prod: inline in Doppler, extracted on sync |

Do **not** configure divergent per-portal Clerk apps. Platform triad names (`CLERK_SECRET_KEY` / `CLERK_PUBLISHABLE_KEY` / `CLERK_JWKS_URL`) are canonical; portal slot aliases are filled from the same triad by `pnpm clerk:sync`.

---

## Gaps (known, optional)

| Secret                                  | Status                 | Action when needed                                                                                                                                                |
| --------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` | Not set                | Optional — add when Sentry project is created                                                                                                                     |
| `FLEETBASE_*`                           | Blocked (DD-05b)       | Add to Doppler when Fleetbase prod ready                                                                                                                          |
| SMTP (`MAIL_*` / `SMTP_*`)              | Prod via Zoho CA       | `bash infrastructure/deploy/scripts/upload-mail-to-doppler.sh` → Doppler `pcd`/`prd` → deploy `sync-secrets.sh`. See [ZOHO_MAIL.md](./notifications/ZOHO_MAIL.md) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`    | Not in deploy workflow | Add GitHub secret when merchant Stripe UI ships                                                                                                                   |

---

## Verify alignment

```bash
pnpm secrets:verify          # local + GitHub checklist (no values printed)
pnpm clerk:sync              # after editing env/clerk.env
bash infrastructure/deploy/scripts/validate-clerk-keys.sh env/clerk.env

# After deploy (on droplet — key names only):
grep -E '^[A-Z_]+=' /opt/porterchain/.env | cut -d= -f1 | sort

curl -fsS https://api.porterchain.com/health/ready | jq '.clerk_mode, .clerk_apps'
```

---

## Related

| Document                                                                  | Role                                                  |
| ------------------------------------------------------------------------- | ----------------------------------------------------- |
| [env/README.md](../env/README.md)                                         | Local templates                                       |
| [infrastructure/deploy/SECRETS.md](../infrastructure/deploy/SECRETS.md)   | Doppler setup + rotation                              |
| [docs/runbooks/clerk-consolidation.md](./runbooks/clerk-consolidation.md) | Clerk unified setup (primary) + legacy 4-app rollback |
| [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md)                   | Full variable catalog                                 |
