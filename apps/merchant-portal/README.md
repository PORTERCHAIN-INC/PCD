# Porterchain Merchant Portal

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Secure B2B portal for approved business customers. Next.js 16 on **port 3001**.

> **See also:** [MERCHANT_ARCHITECTURE_REPORT.md](../../MERCHANT_ARCHITECTURE_REPORT.md)

---

## Setup

```bash
pnpm install
cp env/merchant-portal.env.example apps/merchant-portal/.env.local
pnpm dev:merchant
# or: pnpm --filter @porterchain/merchant-portal dev
```

Open [http://localhost:3001](http://localhost:3001).

---

## Architecture

```
Merchant portal (:3001)
    ↓ Clerk Bearer token
Porterchain API (:8001) /v1/merchant/*
    ↓
merchant_engine, billing_engine, booking_engine
    ↓
Fleetbase adapter (server-side only)
```

External integrations may also use `/v1/merchant-api/*` with `X-Api-Key` (documented in merchant API settings).

**Dev auth:** `Authorization: Bearer dev` + `X-Merchant-Org-Id` when API `CLERK_DEV_BYPASS=true`.

---

## Modules

| Route                | Feature                           |
| -------------------- | --------------------------------- |
| `/dashboard`         | Overview, KPIs, quick actions     |
| `/book`              | Single delivery booking           |
| `/bulk`              | CSV upload, validate, confirm     |
| `/orders`            | Search, filter, cancel, duplicate |
| `/orders/[order_id]` | Order detail                      |
| `/track`             | Live tracking timeline            |
| `/billing`           | Statements, invoices, balance     |
| `/reports`           | Monthly analytics                 |
| `/api`               | API keys, webhooks                |
| `/team`              | RBAC team management              |
| `/settings`          | Business profile                  |
| `/onboarding`        | Merchant onboarding               |

---

## Environment

Copy from `env/merchant-portal.env.example`:

| Variable                             | Purpose                            |
| ------------------------------------ | ---------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`  | Clerk auth                         |
| `CLERK_SECRET_KEY`                   | Server-side Clerk                  |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`    | API base (`http://localhost:8001`) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe checkout                    |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`    | Order tracking maps                |

See [ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md).

---

## Related Documents

| Document                                                                         | Purpose            |
| -------------------------------------------------------------------------------- | ------------------ |
| [../merchant/README.md](../merchant/README.md)                                   | Path alias pointer |
| [../../MERCHANT_PRODUCTION_READINESS.md](../../MERCHANT_PRODUCTION_READINESS.md) | Readiness          |
| [../../RBAC.md](../../RBAC.md)                                                   | Permissions        |

---

## Governance

| Document                                                       | Role              |
| -------------------------------------------------------------- | ----------------- |
| [../../masterrule.md](../../masterrule.md)                     | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout   |
