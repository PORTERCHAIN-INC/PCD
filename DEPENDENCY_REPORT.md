# Porterchain — Dependency Report

**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [INTEGRATIONS.md](INTEGRATIONS.md) (canonical doc).

**Scope:** PCD monorepo (`pnpm` workspaces + Python services)  
**Stack reference:** [TECH_STACK.md](./TECH_STACK.md)

> **This is an architecture-level dependency map.** Run `pnpm audit` and `pip audit` (or `pip-audit`) after dependency changes for live CVE counts.

---

## Executive summary

| Metric                   | Value                                                                      |
| ------------------------ | -------------------------------------------------------------------------- |
| Monorepo                 | **Yes** — pnpm 9.15 + Turbo 2.3                                            |
| Node.js                  | **22.22.3** (`.nvmrc`)                                                     |
| TypeScript workspaces    | 26 `package.json` roots (apps + packages + shared)                         |
| Python services          | API, worker, pricing-engine, fleetbase-adapter, event-bus, driver-platform |
| Package manager (JS)     | pnpm (lockfile: `pnpm-lock.yaml`)                                          |
| Package manager (Python) | pip / `apps/api/requirements.txt` + editable local packages                |
| Auth                     | **Clerk only** — Supabase/Twilio OTP removed                               |
| Porterchain DB           | **PostgreSQL 16** — SQLite removed                                         |

---

## Workspace layout

| Area               | Path                     | Key dependencies                                     |
| ------------------ | ------------------------ | ---------------------------------------------------- |
| Website            | `website/`               | Next 16, React 19, next-intl, `@porterchain/maps`    |
| Admin              | `apps/admin/`            | Next 16, Clerk, `@porterchain/ui`, live map          |
| Merchant portal    | `apps/merchant-portal/`  | Next 16, Clerk, Stripe (client), `@porterchain/maps` |
| Customer           | `apps/customer/`         | Next 16, Clerk, `@porterchain/maps`                  |
| Driver portal      | `apps/driver-portal/`    | Next 16, Clerk, `@porterchain/maps`                  |
| Mobile driver      | `apps/mobile-driver/`    | Expo 52, Clerk, `@porterchain/mobile-maps`           |
| Mobile customer    | `apps/mobile-customer/`  | Expo 52, Clerk, `@porterchain/mobile-maps`           |
| Shared packages    | `packages/*`, `shared/*` | maps, auth, types, ui, events, queue                 |
| API                | `apps/api/`              | FastAPI, SQLAlchemy, Alembic, Stripe, psycopg        |
| Worker             | `apps/worker/`           | Redis queues, shared Python services                 |
| Fleetbase (vendor) | `apps/fleetbase/`        | Laravel/MySQL — **do not modify**                    |

---

## Internal package graph (high level)

```
@porterchain/maps          ← website, admin, merchant, customer, driver-portal
@porterchain/auth          ← all Clerk portals
@porterchain/ui            ← admin, some portals
@porterchain/types         ← API clients, shared types
@porterchain/mobile-maps   ← mobile-driver, mobile-customer
@porterchain/events        ← event catalog (TS)
porterchain-pricing        ← apps/api (editable install)
porterchain-fleetbase-adapter ← apps/api, worker
porterchain_services       ← apps/api, worker (Python)
```

See [MODULE_DEPENDENCY_GRAPH.md](./MODULE_DEPENDENCY_GRAPH.md) for module-level detail.

---

## External integrations (runtime)

| Integration     | Where configured                     | Notes                                   |
| --------------- | ------------------------------------ | --------------------------------------- |
| Clerk           | All portals + mobile                 | Sole auth provider                      |
| Stripe          | `apps/api/` server-side              | Webhooks — never in browser for secrets |
| Google Maps     | `@porterchain/maps`, mobile SDK keys | Viz + geocode only                      |
| Fleetbase       | `services/fleetbase-adapter/`        | HTTP boundary                           |
| PostgreSQL      | `DATABASE_URL`                       | Required                                |
| Redis           | `REDIS_URL`                          | Queues + event bus                      |
| Firebase FCM    | API + mobile                         | Optional locally                        |
| Valhalla / OSRM | API + website quote                  | Routing — not Google                    |

See [INTEGRATIONS.md](./INTEGRATIONS.md) and [integrations.yaml](./integrations.yaml).

---

## CI dependency checks

| Job              | File                                        | Checks                                          |
| ---------------- | ------------------------------------------- | ----------------------------------------------- |
| Website monorepo | `.github/workflows/ci.yml` → `website`      | `pnpm install`, lint, format, build             |
| API PostgreSQL   | `.github/workflows/ci.yml` → `api-postgres` | Alembic migrate, pytest smoke, module validator |

**Recommended additions:** `pnpm audit --audit-level=high`, Python `pip-audit` on `requirements.txt`.

---

## Duplicate / version alignment

| Risk                       | Mitigation in repo                       |
| -------------------------- | ---------------------------------------- |
| React version drift        | pnpm workspace + shared peer deps        |
| Next.js across portals     | Same major (16.x) per app `package.json` |
| TypeScript                 | `packages/config` / shared tsconfig      |
| `@types/react` vs RN types | Separate mobile vs web type roots        |

---

## Removed / obsolete (July 2026)

| Item                             | Status                      |
| -------------------------------- | --------------------------- |
| `details.md`                     | Deleted                     |
| Supabase SDK                     | Not in monorepo             |
| Twilio OTP                       | Removed — Clerk only        |
| Single-project website-only repo | Superseded by full monorepo |
| SQLite as Porterchain DB         | Blocked at API startup      |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
