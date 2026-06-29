# Porterchain Admin & Operations Platform

Internal operating system for Porterchain staff. Runs on **port 3002**.

## Setup

```bash
pnpm install
cp env/admin.env.example apps/admin/.env.local
pnpm dev:admin
```

API: `GET/POST /v1/admin/*` on `localhost:8001`

Dev auth: `Authorization: Bearer dev` with `CLERK_DEV_BYPASS=true` on API.

## Modules

Dashboard · CRM · Merchants · Drivers · Operations · Live Map · Orders · Claims · Pricing · Finance · Support · Reports · Settings

Fleetbase is accessed only through the Porterchain API bridge — never embedded in this UI.
