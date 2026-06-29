# Porterchain Merchant Portal

Secure B2B portal for approved business customers. Runs on **port 3001**.

## Setup

```bash
# From repo root
pnpm install
cp env/merchant-portal.env.example apps/merchant-portal/.env.local
# Configure Clerk keys and API URL

pnpm --filter @porterchain/merchant-portal dev
```

## API

All portal data flows through `GET/POST /v1/merchant/*` on the Porterchain API (`localhost:8001`).

Development uses `CLERK_DEV_BYPASS=true` on the API with headers:
- `Authorization: Bearer dev`
- `X-Merchant-Org-Id: dev_merchant_org`

## Modules

| Route | Feature |
|-------|---------|
| `/dashboard` | Overview, KPIs, quick actions |
| `/book` | Single delivery booking (Net terms) |
| `/bulk` | CSV upload, validate, confirm |
| `/orders` | Search, filter, cancel, duplicate |
| `/track` | Live tracking timeline |
| `/billing` | Statements, invoices, balance |
| `/reports` | Monthly analytics |
| `/api` | API keys, webhooks |
| `/team` | RBAC team management |
| `/settings` | Business profile |
