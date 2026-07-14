# Porterchain Admin & Operations Platform

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Internal control tower for Porterchain staff. Next.js 16 app on **port 3002**.

> **See also:** [docs/architecture/ADMIN_CONTROL_TOWER.md](../../docs/architecture/ADMIN_CONTROL_TOWER.md)

---

## Setup

```bash
pnpm install
cp env/admin.env.example apps/admin/.env.local
pnpm dev:admin
```

Open [http://localhost:3002](http://localhost:3002).

---

## Architecture

```
Admin UI (:3002)
    ↓ Clerk session → Bearer token
Porterchain API (:8001) /v1/admin/*
    ↓
admin_engine, operations, billing, fleetbase_engine, notifications
    ↓
Fleetbase adapter (server-side only — never called from this UI)
```

**Auth:** Clerk for identity; Porterchain JWT via `GET /v1/auth/admin/access` enforces staff allowlist. Clerk login alone does not grant admin access.

**Dev:** `Authorization: Bearer dev` when `CLERK_DEV_BYPASS=true` on API and `NEXT_PUBLIC_CLERK_DEV_BYPASS=true` in admin env.

---

## Modules

| Module         | Route prefix        | Purpose                                    |
| -------------- | ------------------- | ------------------------------------------ |
| Dashboard      | `/dashboard`        | KPIs, ops overview                         |
| Merchants      | `/merchants`        | Merchant onboarding and management         |
| Drivers        | `/drivers`          | Driver roster and detail                   |
| Operations     | `/operations`       | Control tower — dispatch and ops workflows |
| Live Map       | `/live-map`, `/map` | Fleet visualization                        |
| Orders         | `/orders`           | Order management                           |
| Booking drafts | `/booking-drafts`   | Draft reconciliation                       |
| Claims         | `/claims`           | Claims workflow                            |
| Pricing        | `/pricing`          | Rate configuration                         |
| Finance        | `/finance`          | Invoices, payouts                          |
| Support        | `/support`          | Ticket management                          |
| Notifications  | `/notifications`    | Admin notification tools                   |
| Settings       | `/settings`         | Staff, system config                       |
| System         | `/system`           | Health + diagnostics (tabs)                |

_Phase 2 deferred:_ CRM sales pipeline UI, Route Center, BI reports center — use Fleetbase console + module dashboards.

---

## Environment

Copy from `env/admin.env.example`:

| Variable                            | Purpose                            |
| ----------------------------------- | ---------------------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk auth                         |
| `CLERK_SECRET_KEY`                  | Server-side Clerk                  |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`   | API base (`http://localhost:8001`) |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`   | Live map embeds                    |

See [ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md) · [PORT_CONFIGURATION.md](../../PORT_CONFIGURATION.md).

---

## Related Documents

| Document                                                                     | Purpose            |
| ---------------------------------------------------------------------------- | ------------------ |
| [../../RBAC.md](../../RBAC.md)                                               | Role permissions   |
| [../../PRODUCTION_READINESS_REPORT.md](../../PRODUCTION_READINESS_REPORT.md) | Platform readiness |

---

## Governance

| Document                                                       | Role              |
| -------------------------------------------------------------- | ----------------- |
| [../../masterrule.md](../../masterrule.md)                     | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout   |
