# Production secrets (DD-14)

**Type:** CANONICAL  
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)  
**ADR:** [ADR-013-secrets.md](../../docs/architecture/ADR-013-secrets.md)  
**Map:** [docs/SECRETS_MAP.md](../../docs/SECRETS_MAP.md) — start here for local / Doppler / GitHub / server alignment  
**Last verified:** 2026-07-07

Production runtime secrets must not be edited by hand on the droplet. **Doppler** is the system of record; GitHub holds deploy credentials and build-time public keys only.

---

## Architecture

```
Doppler (pcd / prd)
        │
        ├─► deploy: DOPPLER_TOKEN → sync-secrets.sh → /opt/porterchain/.env
        │                                      └─► secrets/firebase-service-account.json
        │
        └─► optional: doppler run locally for break-glass

GitHub Actions secrets (always required)
  DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY, DOPPLER_TOKEN
```

Legacy path (no `DOPPLER_TOKEN`): deploy still injects secrets from individual GitHub secrets — **removed 2026-07-07**; `DOPPLER_TOKEN` is now required in GitHub Actions.

---

## One-time Doppler setup

See **[CLERK_APPS_SETUP.md](./CLERK_APPS_SETUP.md)** for creating 4 Clerk applications and uploading keys.

1. Use project **`pcd`** at [doppler.com](https://www.doppler.com) (already created).
2. Create config **`prd`** (production).
3. Import secrets from current GitHub Actions / droplet `.env`:

| Doppler secret                   | Notes                                                         |
| -------------------------------- | ------------------------------------------------------------- |
| `POSTGRES_PASSWORD`              | DB password                                                   |
| `CLERK_SECRET_KEY`               | Legacy single-app `sk_live_…` (migrate to per-portal)         |
| `CLERK_PUBLISHABLE_KEY`          | Legacy `pk_live_…`                                            |
| `CLERK_JWKS_URL`                 | Legacy JWKS URL                                               |
| `CLERK_CUSTOMER_SECRET_KEY`      | Customer app `sk_live_…`                                      |
| `CLERK_CUSTOMER_PUBLISHABLE_KEY` | Customer `pk_live_…` (website + customer portal builds)       |
| `CLERK_CUSTOMER_JWKS_URL`        | Customer JWKS                                                 |
| `CLERK_MERCHANT_*`               | Merchant portal                                               |
| `CLERK_ADMIN_*`                  | Admin portal                                                  |
| `CLERK_DRIVER_*`                 | Driver portal + mobile                                        |
| `STRIPE_SECRET`                  | `sk_live_…`                                                   |
| `STRIPE_WEBHOOK_SECRET`          | `whsec_…`                                                     |
| `JWT_SECRET`                     | `openssl rand -hex 32` (alias: `SSO_JWT_SECRET` in docs only) |
| `GOOGLE_MAPS_SERVER_API_KEY`     | Server geocoding                                              |
| `FIREBASE_PROJECT_ID`            | e.g. `porterchain-55313`                                      |
| `FIREBASE_CREDENTIALS_JSON`      | Full service account JSON (single line)                       |
| `FIREBASE_WEB_VAPID_KEY`         | Web push (optional)                                           |
| `SENTRY_DSN`                     | Optional                                                      |
| `FLEETBASE_*`                    | When bridge enabled                                           |
| `PORTERCHAIN_PUSH_ENABLED`       | `true`                                                        |
| `PORTERCHAIN_PUSH_SEND`          | `true`                                                        |
| `API_REPLICAS`                   | `2`                                                           |

4. Create a **service token** for the droplet deploy (read-only, `prd` config).
5. Add to GitHub Actions:

```bash
gh secret set DOPPLER_TOKEN -b "dp.st.prd.xxxx"
```

Optional overrides:

```bash
gh variable set DOPPLER_PROJECT -b "pcd"
gh variable set DOPPLER_CONFIG -b "prd"
```

6. Install Doppler CLI on your laptop for rotation: `brew install dopplerhq/cli/doppler`

---

## Deploy integration

Each deploy runs on the droplet:

```bash
cd /opt/porterchain
bash sync-secrets.sh
docker compose -f docker-compose.prod.yml up -d ...
```

`sync-secrets.sh` is copied with `docker-compose.prod.yml` via CI.

---

## Rotation (quarterly or on incident)

| Secret                  | Procedure                                                             |
| ----------------------- | --------------------------------------------------------------------- |
| `JWT_SECRET`            | Generate new value in Doppler → redeploy → invalidate driver sessions |
| `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard → new endpoint secret → update Doppler → redeploy    |
| `CLERK_SECRET_KEY`      | Clerk Dashboard → rotate → update Doppler → redeploy all portals      |
| `POSTGRES_PASSWORD`     | `ALTER USER` in Postgres → update Doppler → redeploy                  |
| Firebase JSON           | GCP → new key → update Doppler → redeploy                             |

After Doppler update:

```bash
# Trigger GitHub Deploy workflow, or on droplet:
cd /opt/porterchain
DOPPLER_TOKEN=dp.st… bash sync-secrets.sh
docker compose -f docker-compose.prod.yml up -d
```

Never commit `.env` or paste secrets in Slack/email.

---

## Verification

```bash
pnpm secrets:verify   # local + GitHub + Doppler key names (no values)

# On droplet (keys only, no values):
grep -E '^[A-Z_]+=' /opt/porterchain/.env | cut -d= -f1 | sort

# Health after deploy:
curl -fsS https://api.porterchain.com/health/ready | jq '.checks.clerk, .clerk_mode, .clerk_apps'
bash scripts/verify-clerk.sh
```

---

## Related

| Document                                                       | Role                                                     |
| -------------------------------------------------------------- | -------------------------------------------------------- |
| [docs/SECRETS_MAP.md](../../docs/SECRETS_MAP.md)               | Four-store alignment (local / Doppler / GitHub / server) |
| [README.md](./README.md)                                       | Deploy pipeline                                          |
| [RUNBOOK.md](../../RUNBOOK.md)                                 | Day-2 ops                                                |
| [SECURITY.md](../../SECURITY.md)                               | Classification                                           |
| [env/production.env.example](../../env/production.env.example) | Non-secret prod URLs                                     |
