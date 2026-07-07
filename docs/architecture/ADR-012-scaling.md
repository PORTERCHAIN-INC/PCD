# ADR-012 — Horizontal scaling path

**Type:** CANONICAL ADR  
**Status:** Accepted  
**Date:** 2026-07-06  
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)  
**Checklist:** §0.7.3 (DD-03), §3.4.6  
**Related:** [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) · [REALTIME_FLOW.md](./REALTIME_FLOW.md) · [DATABASE_ARCHITECTURE.md](../../DATABASE_ARCHITECTURE.md) · [infrastructure/deploy/README.md](../../infrastructure/deploy/README.md)

---

## Context

Production today runs on a **single DigitalOcean droplet** with PostgreSQL, Redis, Caddy, one or more API containers, a worker, and five Next.js portals (`docker-compose.prod.yml`).

Investor diligence (DD-03) requires a documented path off “one box forever” without rewriting the modular monolith into microservices (masterrule §21).

---

## Decision

**Scale the stateless Porterchain API horizontally** behind Caddy while keeping PostgreSQL, Redis, and the worker as shared coordination layers. Move to **managed Postgres + Redis** before adding a second droplet or Kubernetes.

| Phase | Trigger | Topology | Effort |
| ----- | ------- | -------- | ------ |
| **A — Now** | DD-03 close; p95 headroom | Same droplet, **2 API replicas**, in-compose Postgres/Redis | 1–2 days |
| **B — Growth** | DB CPU >60% sustained or backup SLA | **Managed Postgres 16** + **Managed Redis 7**; 2–4 API replicas | 1–2 weeks |
| **C — Scale-out** | >500 RPS API or multi-region | DO App Platform / ECS / K8s; read replica for analytics (DD-19) | 4–8 weeks |

Phases are **sequential**. Do not jump to Kubernetes while still on a single droplet DB.

---

## Stateless API prerequisites (closed)

These must remain true for every API replica:

| Concern | Mechanism | Code / config |
| ------- | --------- | ------------- |
| HTTP sessions | None — Clerk JWT per request | `auth/clerk.py` |
| Rate limiting | Redis-backed, fail-closed | `platform/rate_limit_middleware.py` (DD-06) |
| In-app notification WS | Redis pub/sub fanout | `notification_engine/realtime.py` (DD-11) |
| Stripe / Fleetbase webhooks | Idempotency store (Redis) | `stripe_webhook_service.py`, event bus |
| Background work | Single worker fleet, Redis queues | `apps/worker/` (DD-04) |
| DB connections | Pooled per replica | `config.py` `db_pool_size=10`, `db_max_overflow=20` |

**Live-map WebSocket** (`/v1/admin/operations/live-map/ws`) is sticky by connection — Caddy round-robin is acceptable; each replica polls DB/Fleetbase independently every 5s. Notification WS (`/v1/notifications/ws`) uses Redis pub/sub so any replica can serve the connection.

---

## Phase A — Two API replicas (same droplet)

### Compose

- Remove fixed `container_name` on the `api` service so Compose can scale.
- Deploy with `API_REPLICAS` (default **2**):

```bash
cd /opt/porterchain
export API_REPLICAS=2
docker compose -f docker-compose.prod.yml up -d --remove-orphans --scale api=$API_REPLICAS
```

### Load balancing

Caddy `reverse_proxy api:8001` resolves the Docker service name to **all** running API containers (round-robin). No config change required beyond scaling.

### Migrations

Run **once** per deploy (any replica):

```bash
docker compose -f docker-compose.prod.yml exec -T api \
  python -w /app/apps/api scripts/repair_and_migrate.py
```

CI deploy workflow uses the same pattern.

### Connection budget

| Replicas | `db_pool_size` | Max DB connections (API only) |
| -------- | -------------- | ----------------------------- |
| 1        | 10             | ~30 (with overflow)           |
| 2        | 10             | ~60                           |
| 4        | 10             | ~120 — reduce pool to 5 first |

Postgres default `max_connections=100` on the droplet image is sufficient for 2 replicas + worker; raise or move to managed PG before 4 replicas.

### Rollback

```bash
export API_REPLICAS=1
docker compose -f docker-compose.prod.yml up -d --scale api=1
```

---

## Phase B — Managed data plane

### Postgres (DigitalOcean Managed Database)

1. Provision **PostgreSQL 16** cluster (single primary; HA standby optional).
2. Set `DATABASE_URL` on API + worker to managed connection string (`?sslmode=require`).
3. `pg_dump` from droplet Postgres → restore to managed; cut over during maintenance window.
4. Remove `postgres` service from compose (or keep as staging-only).

### Redis (DigitalOcean Managed Redis)

1. Provision **Redis 7** with TLS.
2. Set `REDIS_URL` on API + worker.
3. Remove in-compose `redis` service.

### Secrets

Phase B pairs with **DD-14** (secret manager). Until then, store managed URLs in droplet `.env` with `chmod 600`.

---

## Phase C — Multi-node / orchestrator (defer)

Adopt when Phase B is saturated or compliance requires isolated networks:

- Container orchestrator (DO App Platform, ECS Fargate, or K8s).
- API Deployment with HPA on CPU + p95 latency.
- Worker as separate Deployment (replicas=1 until queue depth metric warrants more).
- Managed Postgres with **read replica** for analytics queries (DD-19).
- Fleetbase remains external execution plane — not co-scaled with Porterchain API.

---

## Observability gates

Before scaling past 2 replicas in production:

| Gate | Target |
| ---- | ------ |
| `pnpm load:booking` p95 quote | < 3s (see RUNBOOK § Load testing) |
| API p95 `/health` | < 200 ms |
| Postgres connections | < 80% of `max_connections` |
| Redis memory | < 70% |
| Worker heartbeat | `porterchain:worker:heartbeat` present |

---

## Consequences

**Positive**

- DD-03 / EXE-G5 scale path documented and executable without architecture rewrite.
- API deploys become rolling-friendly (`up --scale` replaces all replicas).
- Managed PG/Redis path is explicit for Series A infra review.

**Negative / risks**

- Live-map WS clients may hop replicas on reconnect (acceptable for admin map).
- In-compose Postgres is still a single point of failure until Phase B.
- Pool sizing must be revisited when replica count changes.

---

## Out of scope

- Microservice extraction (masterrule §21).
- Fleetbase horizontal scale (Fleetbase vendor concern).
- Multi-region active-active.

---

## Governance

| Document | Role |
| -------- | ---- |
| [PRIORITY_TODOS.md](../PRIORITY_TODOS.md) | DD-03 tracking |
| [RUNBOOK.md](../../RUNBOOK.md) | Ops execution |
| [masterrule.md](../../masterrule.md) | Monolith-first policy |
