# Porterchain — Database Architecture

**Document version:** 1.0  
**Date:** June 29, 2026  
**Status:** Documented platform design — no migrations in PCD repo

---

## Data store summary

| Store | Engine | Purpose | Owner |
|-------|--------|---------|-------|
| **Fleetbase DB** | MySQL 8 | Dispatch, orders, drivers, Fleetbase entities | Fleetbase (Laravel) |
| **Porterchain extensions** | MySQL (same instance) | Billing, merchant onboarding, contracts | Porterchain (Laravel extensions) |
| **Porterchain API DB** | PostgreSQL 16 *(recommended)* | FastAPI-owned domain data | Porterchain API |
| **Redis** | Redis 7 | Cache, queues, rate limits, sessions | Shared infrastructure |

> **Current state:** Platform docs specify MySQL only (`DB_DATABASE=fleetbase`). PostgreSQL is recommended for Porterchain FastAPI-native tables when the API repo is consolidated.

---

## MySQL — Fleetbase primary database

### Connection

| Setting | Value |
|---------|-------|
| Host (Docker) | `database` |
| Port | `3306` |
| Database | `fleetbase` |
| User | `fleetbase` |
| Driver | `mysql` (Laravel Eloquent) |

### Schema ownership

```
fleetbase (MySQL database)
├── Fleetbase core tables          # Owned by Fleetbase — DO NOT modify directly
│   ├── companies
│   ├── users (Fleetbase users)
│   ├── drivers
│   ├── vehicles
│   ├── orders
│   ├── payloads
│   ├── places
│   ├── routes
│   └── ... (Fleetbase schema)
│
└── Porterchain extension tables   # Owned by Porterchain Laravel layer
    ├── porterchain_billing_records
    ├── porterchain_merchant_profiles
    ├── porterchain_contracts
    └── ... (inferred from api/app/Models/Porterchain/*)
```

**Rule:** Porterchain business logic accesses Fleetbase data through **API bridges**, not direct cross-schema writes from the website.

---

## Porterchain Laravel models (documented)

Source references in `PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md`:

| Model path | Domain |
|------------|--------|
| `api/app/Models/Porterchain/BillingRecord.php` | Payment terms, invoice metadata |
| `api/app/Services/Porterchain/MerchantOnboardingService.php` | Contract acceptance, merchant lifecycle |

### Merchant onboarding fields (documented)

| Field | Type | Purpose |
|-------|------|---------|
| `contract_status` | enum | `signed`, pending, etc. |
| `contract_signed_at` | timestamp | Legal acceptance |
| `contract_expires_at` | timestamp | Annual renewal |
| Merchant status | enum | `ACTIVE` after admin review |

### Billing payment terms

| Term ID | Label |
|---------|-------|
| `stripe` | Stripe checkout |
| `credit_card` | Credit card |
| `net_30` | Net 30 (default) |
| `net_45` | Net 45 |
| `immediate`, `net_7`, `net_14`, `custom` | API constants |

---

## PostgreSQL — recommended Porterchain API store

When `apps/api` is consolidated, use a **separate PostgreSQL database** for FastAPI-owned data:

```
porterchain_api (PostgreSQL database)
├── users_mirror          # Clerk user ID mapping (optional)
├── booking_sessions      # Retail booking state
├── otp_verifications     # Website OTP audit log
├── driver_invite_tokens  # Invite token hashes
├── api_keys              # Merchant integration keys
├── webhook_deliveries    # Outbound webhook log
└── audit_events          # Compliance audit trail
```

### Why separate from Fleetbase MySQL

| Reason | Detail |
|--------|--------|
| Schema ownership | Fleetbase upgrades must not break Porterchain tables |
| ORM fit | SQLAlchemy + Alembic for FastAPI |
| Migration velocity | Independent release cycles |
| Compliance | Audit tables with strict retention policies |

---

## Fleetbase tables (reference)

Fleetbase manages its own migrations via Laravel. Key entity groups:

| Entity group | Purpose |
|--------------|---------|
| **Companies** | Fleetbase organizations (`PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID`) |
| **Orders** | Shipment orders created via console or API |
| **Drivers** | Fleetbase driver records (bridged to Porterchain driver IDs) |
| **Vehicles** | Fleet vehicle registry |
| **Routes** | Optimized routes with stops |
| **Places** | Geocoded locations |

Porterchain bridge flags control sync:
- `PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE`
- `PORTERCHAIN_FLEETBASE_DRIVER_JOB_BRIDGE`

---

## Redis usage

| Use case | Key pattern | TTL |
|----------|-------------|-----|
| Laravel cache | `fleetbase_cache:*` | Configurable |
| Queue jobs | `queues:*` | Job-dependent |
| Session (if migrated) | `session:*` | 120 min |
| Rate limiting | `rate_limit:auth:*` | 60s windows |
| OTP codes | `otp:{phone\|email}` | 5–10 min |
| Driver location buffer | `driver:location:{id}` | Short (real-time) |

### Configuration

```
CACHE_DRIVER=redis
QUEUE_CONNECTION=redis
REDIS_HOST=cache
REDIS_PORT=6379
```

---

## Caching strategy

| Layer | What | Invalidation |
|-------|------|--------------|
| **CDN** | Static assets, blog pages | Build-time |
| **Next.js** | ISR for blog, static pages | On-demand revalidation |
| **Redis** | API response cache (quotes, geocode) | TTL + event invalidation |
| **Application** | Fleetbase order lookups | On dispatch update webhook |

---

## Indexes (recommended)

### Porterchain API (PostgreSQL)

```sql
-- Booking sessions
CREATE INDEX idx_booking_sessions_created_at ON booking_sessions(created_at);
CREATE INDEX idx_booking_sessions_status ON booking_sessions(status);

-- Driver invites
CREATE UNIQUE INDEX idx_driver_invite_token_hash ON driver_invite_tokens(token_hash);
CREATE INDEX idx_driver_invite_expires ON driver_invite_tokens(expires_at);

-- Webhook deliveries
CREATE INDEX idx_webhook_deliveries_merchant_id ON webhook_deliveries(merchant_id);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);
```

### Fleetbase (via Laravel migrations — do not hand-edit)

Indexes are managed by Fleetbase upstream. Porterchain extensions should add indexes on:
- `merchant_id` foreign keys
- `contract_status`
- `billing_due_date`

---

## Data flow between stores

```
Website booking
  → Porterchain API (PostgreSQL: booking_sessions)
  → Fleetbase bridge (MySQL: orders)
  → Redis (queue: dispatch job)

Merchant onboarding
  → Clerk (identity)
  → Porterchain Laravel (MySQL: porterchain_merchant_*)
  → Admin review → ACTIVE

Driver execution
  → Porterchain API (PostgreSQL: execution audit)
  → Fleetbase (MySQL: routes, stops, POD metadata)
  → Object storage (POD images)
```

---

## Backup architecture

| Database | Frequency | Retention | Method |
|----------|-----------|-----------|--------|
| MySQL (Fleetbase) | Daily full + hourly binlog | 30 days | `mysqldump` / managed backup |
| PostgreSQL (API) | Daily full + WAL | 30 days | `pg_dump` / managed backup |
| Redis | AOF persistence | 7 days | Volume snapshot |

Store backups in separate region (DO Spaces / S3) with encryption at rest.

---

## Migration tooling (target)

| Project | Tool | Path |
|---------|------|------|
| Fleetbase | Laravel migrations | Fleetbase upstream |
| Porterchain Laravel | Laravel migrations | `api/database/migrations/` |
| Porterchain API | Alembic | `apps/api/alembic/versions/` |

**Rule:** Never run Fleetbase migrations from Porterchain CI without reviewing upstream changelog.

---

## Current gap in PCD repo

| Item | Status |
|------|--------|
| Migration files | **None** |
| ORM models | **None** |
| Prisma / Drizzle | **Not used** |
| SQLAlchemy | **Not in repo** |
| Seed data | **None** |

All database architecture above is derived from `details.md`, `PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md`, and `CONNECTIONS.md`.

---

*Reconcile with actual schemas when `apps/api` and Fleetbase stack are added to the monorepo.*
