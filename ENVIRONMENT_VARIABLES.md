# Porterchain — Environment Variables

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Templates:** Organized copy-paste files live in [`env/`](./env/README.md). Copy to local `.env` files and fill secrets there — never commit real values.

---

## Variable naming conventions

| Prefix          | Scope                        | Example                             |
| --------------- | ---------------------------- | ----------------------------------- |
| `NEXT_PUBLIC_*` | Exposed to browser (website) | `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`   |
| `EXPO_PUBLIC_*` | Inlined at mobile build time | `EXPO_PUBLIC_API_URL`               |
| No prefix       | Server-only secrets          | `STRIPE_SECRET`, `CLERK_SECRET_KEY` |
| `PORTERCHAIN_*` | Porterchain platform config  | `PORTERCHAIN_API_URL`               |

---

## Website

**Files:** `env/website.env.example` → `website/.env.local`  
**Code:** `website/src/lib/env.ts`

| Variable                               | Required | Description                                     |
| -------------------------------------- | -------- | ----------------------------------------------- |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`      | Yes      | Browser-restricted Google Maps / Places API key |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`      | Yes      | API base for booking (`http://localhost:8001`)  |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`    | Yes      | Clerk — retail booking auth                     |
| `NEXT_PUBLIC_SITE_URL`                 | No       | Canonical URL for SEO / blog metadata           |
| `NEXT_PUBLIC_CONTACT_EMAIL`            | No       | Public contact email (forms, footer)            |
| `NEXT_PUBLIC_MERCHANT_PORTAL_URL`      | No       | Link to merchant portal                         |
| `NEXT_PUBLIC_ADMIN_PORTAL_URL`         | No       | Link to admin portal                            |
| `NEXT_PUBLIC_CUSTOMER_PORTAL_URL`      | No       | Link to customer portal                         |
| `NEXT_PUBLIC_DRIVER_PORTAL_URL`        | No       | Link to driver portal                           |
| `NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE` | No       | Zoho SalesIQ widget hash                        |
| `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED`     | No       | Enable chat widget                              |
| `NEXT_PUBLIC_SOCIAL_*`                 | No       | Footer social link overrides                    |
| `NEXT_PUBLIC_DRIVER_APP_IOS_URL`       | No       | App Store link on drive page                    |
| `NEXT_PUBLIC_DRIVER_APP_ANDROID_URL`   | No       | Play Store link on drive page                   |
| `NEXT_PUBLIC_ALLOW_STRIPE_MOCK`        | No       | Dev-only Stripe mock checkout                   |

---

## Customer portal

**Port:** 3004 (local) · **Production:** `customer.porterchain.com`

| Variable                            | Required | Description                            |
| ----------------------------------- | -------- | -------------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes      | Clerk frontend key                     |
| `CLERK_SECRET_KEY`                  | Yes      | Clerk server key (API routes only)     |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`   | Yes      | API base URL (`http://localhost:8001`) |
| `NEXT_PUBLIC_SITE_URL`              | No       | Portal base (`http://localhost:3004`)  |

Start: `pnpm dev:customer`

---

## Merchant portal

**Port:** 3001 (local) · **Production:** `merchant.porterchain.com`

| Variable                             | Required | Description                        |
| ------------------------------------ | -------- | ---------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`  | Yes      | Clerk frontend key                 |
| `CLERK_SECRET_KEY`                   | Yes      | Clerk server key (API routes only) |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`    | Yes      | API base URL                       |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Yes      | Stripe checkout (`STRIPE_KEY`)     |
| `PORTERCHAIN_STRIPE_SUCCESS_URL`     | Yes      | Post-payment redirect              |
| `PORTERCHAIN_STRIPE_CANCEL_URL`      | Yes      | Cancel redirect                    |

---

## Admin platform

**Port:** 3002 (local) · **Production:** `admin.porterchain.com`

| Variable                            | Required | Description                            |
| ----------------------------------- | -------- | -------------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes      | Clerk frontend key                     |
| `CLERK_SECRET_KEY`                  | Yes      | Clerk server key                       |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`   | Yes      | API base URL (`http://localhost:8001`) |
| `NEXT_PUBLIC_SITE_URL`              | No       | Portal base (`http://localhost:3002`)  |

Start: `pnpm dev:admin`

---

## Customer mobile app (Expo)

**Files:** `apps/mobile-customer/.env.example` → `apps/mobile-customer/.env`

| Variable                            | Required | Description                   |
| ----------------------------------- | -------- | ----------------------------- |
| `EXPO_PUBLIC_API_URL`               | Yes      | API origin, no trailing slash |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`   | Optional | Maps SDK key                  |
| `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes      | Clerk auth                    |
| `EXPO_PUBLIC_APP_KIND`              | Yes      | `customer`                    |

Start: `pnpm dev:mobile-customer`

---

## Worker

**Files:** `env/worker.env.example` → `apps/worker/.env`

Shares most API env vars (Redis, database, event bus). No HTTP port. Start: `pnpm dev:worker`

---

## Fleetbase console (dispatch UI)

**Port:** 4200 (local) · Separate from Porterchain admin (`:3002`)

| Variable                         | Required | Description                                          |
| -------------------------------- | -------- | ---------------------------------------------------- |
| `CONSOLE_HOST`                   | Yes      | Console base URL                                     |
| `BRANDING_LOGO_URL`              | No       | White-label logo                                     |
| `BRANDING_ICON_URL`              | No       | Favicon / icon                                       |
| `REGISTRY_HOST`                  | Yes      | Fleetbase registry (`https://registry.fleetbase.io`) |
| `PORTERCHAIN_DISPATCHER_API_KEY` | Yes      | Dispatcher API authentication                        |

---

## Driver app (Expo)

**Files:** `apps/mobile-driver/.env`, `eas.json` build env

| Variable                          | Required | Description                           | Build context |
| --------------------------------- | -------- | ------------------------------------- | ------------- |
| `EXPO_PUBLIC_API_URL`             | Yes      | API origin, no trailing slash         | All profiles  |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | Yes      | Maps SDK key (iOS + Android)          | All profiles  |
| `APPLE_ASC_KEY_PATH`              | Submit   | App Store Connect `.p8` key path      | Local submit  |
| `APPLE_ASC_KEY_ID`                | Submit   | ASC API key ID                        | Local submit  |
| `APPLE_ASC_ISSUER_ID`             | Submit   | ASC issuer ID                         | Local submit  |
| `EXPO_TOKEN`                      | Optional | Non-interactive EAS auth              | CI            |
| `VERIFY_ASC_KEY`                  | Optional | Preflight ASC key check (`0` to skip) | Deploy script |

**EAS profile overrides:**

| Profile     | `EXPO_PUBLIC_API_URL`         |
| ----------- | ----------------------------- |
| development | `http://127.0.0.1:8001`       |
| preview     | `https://api.porterchain.com` |
| production  | `https://api.porterchain.com` |

---

## Porterchain API (FastAPI)

**Port:** 8001 (local) · **Path:** `apps/api/`

### Core

| Variable                 | Required | Description                      |
| ------------------------ | -------- | -------------------------------- |
| `PORTERCHAIN_API_URL`    | Yes      | Self-referential API URL         |
| `APP_ENV`                | Yes      | `local`, `staging`, `production` |
| `APP_DEBUG`              | Dev      | Debug mode                       |
| `LOG_LEVEL`              | No       | `debug`, `info`, `warning`       |
| `DIGITALOCEAN_API_TOKEN` | Optional | Infrastructure automation        |

### Auth

| Variable                | Required | Description                           |
| ----------------------- | -------- | ------------------------------------- |
| `CLERK_PUBLISHABLE_KEY` | Yes      | Unified Platform Clerk app public key |
| `CLERK_SECRET_KEY`      | Yes      | Unified Platform Clerk app secret     |
| `CLERK_JWKS_URL`        | Yes      | Unified Platform JWT verification URL |
| `CLERK_DEV_BYPASS`      | Local    | Requires `APP_ENV=local`              |

Primary local/dev/prod target is **unified only** — one Platform Clerk app shared by every portal (see [docs/runbooks/clerk-consolidation.md](./docs/runbooks/clerk-consolidation.md)). `CLERK_MODE=enterprise` (divergent 4-app / 12-key) is **retired**; `pnpm clerk:sync` exits with an error if requested. Per-portal `CLERK_{PORTAL}_*` names below remain as **slot aliases** filled from the Platform triad (compose / dual-read compat) — not a supported second mode.

| Variable                                                                                   | Required | Description                                                |
| ------------------------------------------------------------------------------------------ | -------- | ---------------------------------------------------------- |
| `CLERK_CUSTOMER_SECRET_KEY` / `CLERK_CUSTOMER_JWKS_URL` / `CLERK_CUSTOMER_PUBLISHABLE_KEY` | Alias    | Customer slot (same Platform keys after `pnpm clerk:sync`) |
| `CLERK_MERCHANT_SECRET_KEY` / `CLERK_MERCHANT_JWKS_URL` / `CLERK_MERCHANT_PUBLISHABLE_KEY` | Alias    | Merchant slot (Platform triad expand)                      |
| `CLERK_ADMIN_SECRET_KEY` / `CLERK_ADMIN_JWKS_URL` / `CLERK_ADMIN_PUBLISHABLE_KEY`          | Alias    | Admin / Platform rename path when triad empty              |
| `CLERK_DRIVER_SECRET_KEY` / `CLERK_DRIVER_JWKS_URL` / `CLERK_DRIVER_PUBLISHABLE_KEY`       | Alias    | Driver slot (Platform triad expand)                        |

Frontends use `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` or `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` with the unified Platform publishable key — see [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md).

### Driver onboarding (API server)

| Variable                                              | Default                 | Description              |
| ----------------------------------------------------- | ----------------------- | ------------------------ |
| `DRIVER_PORTAL_BASE_URL`                              | `http://localhost:3003` | Invite link base         |
| `DRIVER_APP_DOWNLOAD_URL`                             | —                       | Marketing drive page     |
| `DRIVER_APP_IOS_URL`                                  | —                       | App Store URL in emails  |
| `DRIVER_APP_ANDROID_URL`                              | —                       | Play Store URL in emails |
| `DRIVER_INVITE_TOKEN_EXPIRE_SECONDS`                  | `604800`                | 7-day invite TTL         |
| `AUTH_DRIVER_INVITE_VALIDATE_MAX_ATTEMPTS_PER_MINUTE` | `30`                    | Rate limit               |
| `AUTH_DRIVER_INVITE_ACCEPT_MAX_ATTEMPTS_PER_MINUTE`   | `15`                    | Rate limit               |

### Transactional email (notifications — not auth)

| Variable                   | Required | Description                |
| -------------------------- | -------- | -------------------------- |
| `PORTERCHAIN_FROM_EMAIL`   | Yes      | Default transactional from |
| `PORTERCHAIN_FROM_NAME`    | Yes      | Default from name          |
| `PORTERCHAIN_TRACKING_URL` | Yes      | Tracking page base         |
| `PORTERCHAIN_OPS_EMAILS`   | Yes      | Comma-separated ops alerts |

### Retail billing

| Variable                                | Required | Description               |
| --------------------------------------- | -------- | ------------------------- |
| `PORTERCHAIN_RETAIL_PAY_URL_BASE`       | Yes      | Retail pay page base      |
| `PORTERCHAIN_RETAIL_STRIPE_SUCCESS_URL` | Yes      | Success redirect template |
| `PORTERCHAIN_RETAIL_STRIPE_CANCEL_URL`  | Yes      | Cancel redirect template  |

---

## Fleetbase (Laravel API)

**Port:** 8000 (conflicts with Porterchain API in local dev — see PORT_CONFIGURATION.md)

| Variable                                     | Required | Description                           |
| -------------------------------------------- | -------- | ------------------------------------- |
| `APP_NAME`                                   | Yes      | Application name                      |
| `APP_KEY`                                    | Yes      | Laravel encryption key (`base64:...`) |
| `APP_URL`                                    | Yes      | API public URL                        |
| `FLEETBASE_API_URL`                          | Yes      | Fleetbase API URL                     |
| `LOG_CHANNEL`                                | No       | `daily`, `stack`                      |
| `PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID` | Yes      | Default Fleetbase company             |
| `PORTERCHAIN_FLEETBASE_ASSIGNMENT_REQUIRED`  | Prod     | Enforce driver assignment             |
| `PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE`      | Yes      | Enable dispatch sync                  |
| `PORTERCHAIN_FLEETBASE_DRIVER_JOB_BRIDGE`    | Yes      | Enable driver job sync                |

### Session / filesystem

| Variable            | Value           | Description                |
| ------------------- | --------------- | -------------------------- |
| `SESSION_DRIVER`    | `file`          | Session storage            |
| `SESSION_LIFETIME`  | `120`           | Minutes                    |
| `SESSION_DOMAIN`    | `localhost`     | Cookie domain              |
| `FILESYSTEM_DRIVER` | `public`        | Local disk (migrate to S3) |
| `BROADCAST_DRIVER`  | `socketcluster` | Real-time events           |

---

## Redis

| Variable           | Required | Description               |
| ------------------ | -------- | ------------------------- |
| `REDIS_HOST`       | Yes      | Host (`cache` in Docker)  |
| `REDIS_PORT`       | Yes      | `6379`                    |
| `REDIS_PASSWORD`   | Optional | Password (`null` locally) |
| `CACHE_DRIVER`     | Yes      | `redis`                   |
| `QUEUE_CONNECTION` | Yes      | `redis`                   |

---

## PostgreSQL (Porterchain database)

**Port:** 5432 (local) · **Used by:** `apps/api/`, `apps/worker/`

| Variable       | Required | Description                                                 |
| -------------- | -------- | ----------------------------------------------------------- |
| `DATABASE_URL` | Yes      | `postgresql+psycopg://user:pass@localhost:5432/porterchain` |

**Pool tuning** (per API replica — see [ADR-012](./docs/architecture/ADR-012-scaling.md)):

| Variable          | Default | Description                                    |
| ----------------- | ------- | ---------------------------------------------- |
| `DB_POOL_SIZE`    | `10`    | SQLAlchemy pool size per process               |
| `DB_MAX_OVERFLOW` | `20`    | Extra connections beyond pool_size under burst |
| `DB_POOL_TIMEOUT` | `30`    | Seconds to wait for a free connection          |
| `DB_POOL_RECYCLE` | `1800`  | Recycle connections after N seconds (30 min)   |

At **2 API replicas** with defaults, budget ~60 max API DB connections (10+20 per replica). Reduce `DB_POOL_SIZE` to `5` before scaling to 4 replicas on a 100-connection Postgres instance.

| `DATABASE_URL_REPLICA` | No | Optional read-only URI for analytics (`get_read_db()`); see §3.4.7 |

SQLite is **not supported**. Run `pnpm db:migrate` before starting the API.

---

## MySQL (Fleetbase database)

| Variable        | Required | Description                       |
| --------------- | -------- | --------------------------------- |
| `DB_CONNECTION` | Yes      | `mysql`                           |
| `DB_HOST`       | Yes      | `database` (Docker) / `localhost` |
| `DB_PORT`       | Yes      | `3306`                            |
| `DB_DATABASE`   | Yes      | `fleetbase`                       |
| `DB_USERNAME`   | Yes      | DB user                           |
| `DB_PASSWORD`   | Yes      | DB password                       |

---

## Stripe

**Server-only — never in website `.env`**

| Variable                         | Required | Description                 |
| -------------------------------- | -------- | --------------------------- |
| `STRIPE_KEY`                     | Yes      | Publishable key (`pk_*`)    |
| `STRIPE_SECRET`                  | Yes      | Secret key (`sk_*`)         |
| `STRIPE_WEBHOOK_SECRET`          | Yes      | Webhook signing (`whsec_*`) |
| `PORTERCHAIN_STRIPE_SUCCESS_URL` | Yes      | Merchant invoice success    |
| `PORTERCHAIN_STRIPE_CANCEL_URL`  | Yes      | Merchant invoice cancel     |

---

## Clerk

| Variable                | Required | Description                                                   |
| ----------------------- | -------- | ------------------------------------------------------------- |
| `CLERK_PUBLISHABLE_KEY` | Yes      | `pk_test_*` / `pk_live_*`                                     |
| `CLERK_SECRET_KEY`      | Yes      | `sk_test_*` / `sk_live_*`                                     |
| `CLERK_JWKS_URL`        | Yes      | `https://<instance>.clerk.accounts.dev/.well-known/jwks.json` |

---

## Firebase

| Variable                          | Required | Description               |
| --------------------------------- | -------- | ------------------------- |
| `FIREBASE_PROJECT_ID`             | Yes      | GCP project ID            |
| `FIREBASE_CREDENTIALS_PATH`       | Yes      | Service account JSON path |
| `PORTERCHAIN_DRIVER_PUSH_ENABLED` | Yes      | Master push toggle        |
| `PORTERCHAIN_DRIVER_PUSH_SEND`    | Yes      | Actually send push        |

> Driver mobile app does **not** use Firebase Auth. FCM is API-side only.

---

## Google Maps

| Variable                          | Required | Used by            | Description                            |
| --------------------------------- | -------- | ------------------ | -------------------------------------- |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Yes      | Website            | Browser key (HTTP referrer restricted) |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | Yes      | Driver app         | iOS/Android SDK key                    |
| `GOOGLE_MAPS_BROWSER_API_KEY`     | Yes      | Web (legacy alias) | Same as browser key                    |
| `GOOGLE_MAPS_SERVER_API_KEY`      | Yes      | API                | IP-restricted server key               |
| `GOOGLE_MAPS_API_KEY`             | Yes      | API                | Server geocoding / distance            |
| `GOOGLE_MAPS_LOCALE`              | No       | API                | `us`, `en-CA`                          |

**Required GCP APIs:**

- Maps JavaScript API
- Places API (New)
- Geocoding API
- Distance Matrix API (if used server-side)
- Maps SDK for iOS / Android (driver app)

---

## OSRM

| Variable    | Required | Description                                              |
| ----------- | -------- | -------------------------------------------------------- |
| `OSRM_HOST` | Yes      | OSRM router URL (e.g. `https://router.project-osrm.org`) |

Used as fallback when Valhalla unavailable. Driver app does **not** call OSRM directly.

---

## Valhalla

| Variable            | Required | Description                                   |
| ------------------- | -------- | --------------------------------------------- |
| `ROUTING_ENGINE`    | Yes      | `valhalla`                                    |
| `VALHALLA_BASE_URL` | Yes      | Host-accessible URL (`http://localhost:8002`) |
| `VALHALLA_BASE_URI` | Yes      | Docker-internal URL (`http://valhalla:8002`)  |

---

## Docker (compose service hostnames)

These are **not env vars** but Docker network DNS names referenced in env values:

| Hostname   | Service          |
| ---------- | ---------------- |
| `database` | MySQL            |
| `cache`    | Redis            |
| `valhalla` | Valhalla routing |

---

## Analytics

| Variable                               | Required | Description      |
| -------------------------------------- | -------- | ---------------- |
| `NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE` | No       | Chat widget ID   |
| `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED`     | No       | `true` / `false` |

No Google Analytics or PostHog vars documented yet. Add when adopted.

---

## Email (platform SMTP)

**SSOT:** [docs/notifications/ZOHO_MAIL.md](docs/notifications/ZOHO_MAIL.md) (Zoho Canada · Mailpit local · aliases)

| Variable                 | Required | Dev (Mailpit)           | Production (Zoho CA)                 |
| ------------------------ | -------- | ----------------------- | ------------------------------------ |
| `MAIL_MAILER`            | Yes      | `smtp`                  | `smtp`                               |
| `MAIL_HOST`              | Yes      | `localhost`             | `smtp.zohocloud.ca`                  |
| `MAIL_PORT`              | Yes      | `1025`                  | `465` (SSL; API uses `SMTP_SSL`)     |
| `MAIL_USERNAME`          | Prod     | empty                   | e.g. `ops@porterchain.com`           |
| `MAIL_PASSWORD`          | Prod     | empty                   | Zoho app-specific password (Doppler) |
| `MAIL_ENCRYPTION`        | Prod     | empty                   | `ssl`                                |
| `MAIL_FROM_ADDRESS`      | Yes      | `ops@porterchain.com`   | Default From                         |
| `MAIL_FROM_ADDRESS2`     | No       | `sales@porterchain.com` | `from_alias=sales`                   |
| `MAIL_FROM_ADDRESS3`     | No       | `ravi@porterchain.com`  | Personal / founder From              |
| `MAIL_FROM_NAME`         | Yes      | `Porterchain (local)`   | `Porterchain`                        |
| `PORTERCHAIN_OPS_EMAILS` | No       | `ops@porterchain.com`   | Ops distribution                     |

**Aliases on `porterchain.com`:** `peter@`, `ravi@`, `billing@`, `no-reply@`, `ops@`, `sales@`, `support@`.

**IMAP / POP (clients only — not API):** `imap.zohocloud.ca:993` · `pop.zohocloud.ca:995` (SSL). See Zoho Mail doc.

---

## SMS (Twilio)

| Variable             | Required | Description         |
| -------------------- | -------- | ------------------- |
| `TWILIO_ACCOUNT_SID` | Yes      | Account SID         |
| `TWILIO_AUTH_TOKEN`  | Yes      | Auth token          |
| `TWILIO_FROM_NUMBER` | Yes      | E.164 sender number |

---

## Storage

| Variable                | Required | Description                        |
| ----------------------- | -------- | ---------------------------------- |
| `FILESYSTEM_DRIVER`     | Yes      | `public` (local) → migrate to `s3` |
| `AWS_ACCESS_KEY_ID`     | Future   | S3 access                          |
| `AWS_SECRET_ACCESS_KEY` | Future   | S3 secret                          |
| `AWS_DEFAULT_REGION`    | Future   | e.g. `tor1`                        |
| `AWS_BUCKET`            | Future   | POD uploads bucket                 |

---

## Logging

| Variable      | Required | Description              |
| ------------- | -------- | ------------------------ |
| `LOG_CHANNEL` | No       | `daily`, `stderr`        |
| `LOG_LEVEL`   | No       | `debug`, `info`, `error` |

---

## Monitoring

| Variable                 | Required    | Description           |
| ------------------------ | ----------- | --------------------- |
| `SENTRY_DSN`             | Recommended | Server error tracking |
| `NEXT_PUBLIC_SENTRY_DSN` | Recommended | Client error tracking |
| `SENTRY_AUTH_TOKEN`      | CI          | Source map upload     |
| `SENTRY_ORG`             | CI          | Sentry org slug       |
| `SENTRY_PROJECT`         | CI          | Project slug          |

Not currently configured in PCD repo.

---

## Environment file template layout

```
/
├── env/                            # Committed templates (no secrets)
│   ├── README.md
│   ├── website.env.example
│   ├── api.env.example
│   ├── worker.env.example
│   ├── admin.env.example
│   ├── merchant-portal.env.example
│   ├── customer-portal.env.example
│   ├── driver-portal.env.example
│   ├── mobile-driver.env.example
│   ├── fleetbase.env.example
│   └── compose.env.example
├── website/.env.local              # gitignored
├── apps/api/.env                   # gitignored
├── apps/worker/.env                # gitignored
└── infrastructure/docker/.env      # gitignored — Docker Compose secrets
```

---

## Validation checklist

- [ ] No `sk_*`, `whsec_*`, or SMTP passwords in git
- [ ] Browser keys restricted by HTTP referrer
- [ ] Server keys restricted by IP
- [ ] `NEXT_PUBLIC_*` contains no secrets
- [ ] Production uses secret manager — set `DOPPLER_TOKEN` in GitHub; see [infrastructure/deploy/SECRETS.md](./infrastructure/deploy/SECRETS.md)

---

_See [env/README.md](./env/README.md) and [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)._
---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
