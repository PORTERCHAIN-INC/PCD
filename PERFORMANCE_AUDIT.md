# Performance Audit — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` §16 (Observability)

---

## Executive Verdict

| Area | Status |
|------|--------|
| Connection pool | **PASS** |
| PostgreSQL indexes | **PARTIAL** |
| Caching | **PARTIAL** |
| Background workers | **PASS** |
| API latency patterns | **ACCEPTABLE** |
| Query optimization | **PARTIAL** |

---

## Connection Pool

| Setting | Implementation |
|---------|----------------|
| Engine | SQLAlchemy + psycopg |
| `pool_pre_ping` | ✅ Enabled |
| Pool size | Configurable via env |
| SQLite | Rejected at startup |

---

## Database Performance

### Indexes (Applied)

| Index | Purpose |
|-------|---------|
| `ix_orders_state_created_at` | Control tower / queue |
| `ix_orders_merchant_state` | Merchant order lists |
| `ix_domain_events_type_occurred` | Event queries |
| `ix_fleetbase_sync_jobs_pending` | Retry drain |
| GIN on CRM JSONB | Company/lead search |
| `uq_orders_quote_id` | Idempotency |

### Gaps

| ID | Severity | Issue | Effort |
|----|----------|-------|--------|
| P-M01 | Medium | JSONB migration incomplete for non-CRM tables | 1–2 days |
| P-M02 | Medium | Missing FK indexes on some newer tables | 4 hours |
| P-L01 | Low | String UUID vs native UUID | Future |

---

## Caching

| Layer | Implementation | Status |
|-------|----------------|--------|
| Redis | Event bus, queues, idempotency | ✅ |
| HTTP response cache | Not global | ⚠️ |
| Clerk JWKS | Cached in auth module | ✅ |
| Maps/routing | No result cache | ⚠️ Medium |

### P-M03 — No routing result cache (Medium)

Repeated Valhalla/OSRM calls for same coordinates. Recommend short-TTL Redis cache for route matrices in Route Center.

---

## Background Workers

| Worker | Function | Interval |
|--------|----------|----------|
| `apps/worker` | Event bus consume | 1s block |
| Queue drain | Email, SMS, push, billing | Per batch |
| Fleetbase retry | `process_retry_queue` | 60s |

**Queue monitoring:** Diagnostics + Prometheus metrics for depth and DLQ.

---

## API Performance Patterns

### Good

- Thin routers on quotes, webhooks, booking drafts
- Pagination on admin grids
- Live map 8s poll fallback (reduces WS pressure)

### Concerns

| ID | Severity | Issue | File |
|----|----------|-------|------|
| P-H01 | High | `driver.py` router — large handler surface, multiple commits per request | `routers/driver.py` |
| P-M04 | Medium | Admin pricing endpoints N+1 merchant lookups | `routers/admin.py` |
| P-M05 | Medium | CRM list without cursor pagination on large datasets | `crm_service.py` |

---

## Homepage Latency (Fixed)

`GET /v1/booking-drafts/active` returned 404 for anonymous users causing ~785ms delay. Fixed: returns `200 null` + sessionStorage hint on website.

---

## Observability (§16)

| Requirement | Status |
|-------------|--------|
| Structured logging | ✅ |
| Correlation IDs | ⚠️ Partial on HTTP→event |
| Queue depth monitoring | ✅ Diagnostics |
| DLQ monitoring | ✅ |
| Integration health | ✅ Full diagnostics dashboard |
| Webhook success rate | ⚠️ Manual via diagnostics |

---

## Recommended Actions

1. **High** — Refactor `driver.py` router (reduces latency + improves maintainability)
2. **Medium** — Route result caching for Route Center
3. **Medium** — Add Valhalla/OSRM to readiness for routing-dependent deploys
4. **Low** — Continue JSONB + index rollout per `POSTGRESQL_PERFORMANCE.md`

---

*Database detail: `DATABASE_AUDIT.md` · Production gates: `PRODUCTION_READINESS_REPORT.md`*
