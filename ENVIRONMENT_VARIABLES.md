# Porterchain — Environment Variables

**Document version:** 1.1  
**Date:** June 29, 2026

> **Templates:** Organized copy-paste files live in [`env/`](./env/README.md). Copy to local `.env` files and fill secrets there — never commit real values.

> **Security:** Never commit real secrets. Rotate any credentials that were previously stored in `details.md`.

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

**Files:** `website/env.example`, `website/.env.local`  
**Active in code today:** 2 variables

| Variable                          | Required | Description                                     | Example                   |
| --------------------------------- | -------- | ----------------------------------------------- | ------------------------- |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Yes      | Browser-restricted Google Maps / Places API key | `AIza...`                 |
| `NEXT_PUBLIC_SITE_URL`            | No       | Canonical URL for SEO / blog metadata           | `https://porterchain.com` |

### Planned / documented (not wired in PCD website code)

| Variable                               | Required | Description                          |
| -------------------------------------- | -------- | ------------------------------------ |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`      | Yes      | Public API base for booking submit   |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`    | Yes      | Clerk — retail booking auth          |
| `NEXT_PUBLIC_CONTACT_EMAIL`            | No       | Public contact email (forms, footer) |
| `NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE` | No       | Zoho SalesIQ widget hash             |
| `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED`     | No       | Enable chat widget                   |
| `NEXT_PUBLIC_SOCIAL_LINKEDIN`          | No       | Footer social override               |
| `NEXT_PUBLIC_SOCIAL_INSTAGRAM`         | No       | Footer social override               |
| `NEXT_PUBLIC_SOCIAL_FACEBOOK`          | No       | Footer social override               |
| `NEXT_PUBLIC_SOCIAL_YOUTUBE`           | No       | Footer social override               |
| `NEXT_PUBLIC_SOCIAL_WHATSAPP`          | No       | Footer social override               |
| `NEXT_PUBLIC_DRIVER_APP_IOS_URL`       | No       | App Store link on drive page         |
| `NEXT_PUBLIC_DRIVER_APP_ANDROID_URL`   | No       | Play Store link on drive page        |

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

**Port:** 3002 (local) · **Production:** internal ops URL

| Variable                            | Required | Description                            |
| ----------------------------------- | -------- | -------------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes      | Clerk frontend key                     |
| `CLERK_SECRET_KEY`                  | Yes      | Clerk server key                       |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`   | Yes      | API base URL (`http://localhost:8001`) |
| `NEXT_PUBLIC_SITE_URL`              | No       | Portal base (`http://localhost:3002`)  |

Start: `pnpm dev:admin`

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

| Variable                | Required | Description                  |
| ----------------------- | -------- | ---------------------------- |
| `CLERK_PUBLISHABLE_KEY` | Yes*     | Legacy single-app public key |
| `CLERK_SECRET_KEY`      | Yes*     | Legacy single-app secret     |
| `CLERK_JWKS_URL`        | Yes*     | Legacy JWT verification URL  |
| `CLERK_DEV_BYPASS`      | Local    | Requires `APP_ENV=local`     |

\*Local dev: set legacy `CLERK_*` only. Production enterprise: set per-class keys below (empty fields fall back to legacy).

| Variable                                                                                   | Required | Description                                                    |
| ------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------- |
| `CLERK_CUSTOMER_SECRET_KEY` / `CLERK_CUSTOMER_JWKS_URL` / `CLERK_CUSTOMER_PUBLISHABLE_KEY` | Prod     | Customer Clerk app (website, customer portal, customer mobile) |
| `CLERK_MERCHANT_SECRET_KEY` / `CLERK_MERCHANT_JWKS_URL` / `CLERK_MERCHANT_PUBLISHABLE_KEY` | Prod     | Merchant portal                                                |
| `CLERK_ADMIN_SECRET_KEY` / `CLERK_ADMIN_JWKS_URL` / `CLERK_ADMIN_PUBLISHABLE_KEY`          | Prod     | Admin portal                                                   |
| `CLERK_DRIVER_SECRET_KEY` / `CLERK_DRIVER_JWKS_URL` / `CLERK_DRIVER_PUBLISHABLE_KEY`       | Prod     | Driver portal + driver mobile                                  |

Frontends use `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` or `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` with the matching class publishable key — see [AUTHENTICATION.md](./AUTHENTICATION.md).

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

| Variable            | Required | Description           |
| ------------------- | -------- | --------------------- |
| `MAIL_MAILER`       | Yes      | `smtp`                |
| `MAIL_HOST`         | Yes      | `smtp.zohocloud.ca`   |
| `MAIL_PORT`         | Yes      | `465`                 |
| `MAIL_USERNAME`     | Yes      | SMTP user             |
| `MAIL_PASSWORD`     | Yes      | SMTP password         |
| `MAIL_ENCRYPTION`   | Yes      | `ssl`                 |
| `MAIL_FROM_ADDRESS` | Yes      | `ops@porterchain.com` |
| `MAIL_FROM_NAME`    | Yes      | Display name          |

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

## Environment file template layout (target monorepo)

```
/
├── env/                            # Committed templates (no secrets)
│   ├── README.md
│   ├── website.env.example
│   ├── api.env.example
│   ├── fleetbase.env.example
│   ├── merchant-portal.env.example
│   ├── mobile-driver.env.example
│   └── compose.env.example
├── details.md                      # Index only — points to env/
├── website/.env.local              # gitignored — your website secrets
├── apps/api/.env                   # gitignored
└── .env                            # gitignored — Docker Compose secrets
```

---

## Validation checklist

- [ ] No `sk_*`, `whsec_*`, or SMTP passwords in git
- [ ] Browser keys restricted by HTTP referrer
- [ ] Server keys restricted by IP
- [ ] `NEXT_PUBLIC_*` contains no secrets
- [ ] Production uses secret manager (DO Secrets, Vault, or CI vars)
- [ ] `details.md` removed and all contained secrets rotated

---

_Source: `website/env.example`, `details.md` (sanitized), `CONNECTIONS.md`, codebase grep. Reconcile when monorepo is consolidated._
