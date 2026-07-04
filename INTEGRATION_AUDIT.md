# Integration Audit — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` Appendix B

---

## Executive Verdict

| Integration | Configured | Health Check        | Production Ready      |
| ----------- | ---------- | ------------------- | --------------------- |
| Clerk       | ✅         | JWKS probe          | ✅                    |
| Stripe      | ✅         | API probe           | ✅ (webhook required) |
| PostgreSQL  | ✅         | `SELECT 1`          | ✅                    |
| Redis       | ✅         | `PING`              | ✅                    |
| Fleetbase   | ✅         | Adapter + API probe | ⚠️ Env-dependent      |
| Google Maps | ✅         | Geocode probe       | ⚠️ Key required       |
| Valhalla    | ✅         | `/status` probe     | ⚠️ Optional           |
| OSRM        | ✅         | Route probe         | ⚠️ Fallback only      |
| Firebase    | ⚠️         | Project ID only     | ❌ Log-only push      |
| WebSockets  | ✅         | Route registration  | ✅                    |
| SMTP        | ⚠️         | Optional            | Log-only local        |

---

## Integration Details

### Clerk (Authentication)

| Item         | Detail                                                         |
| ------------ | -------------------------------------------------------------- |
| **Config**   | `config.py` per-app keys; `clerk_registry.py`                  |
| **Health**   | `diagnostics_service._probe_clerk()`                           |
| **Usage**    | Website, merchant, admin, customer portals; API JWT validation |
| **Gap**      | `clerk_dev_bypass` must be off in production                   |
| **Severity** | Low                                                            |

### Stripe (Payments)

| Item         | Detail                                                                      |
| ------------ | --------------------------------------------------------------------------- |
| **Config**   | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_MOCK`                 |
| **Health**   | Live API probe in diagnostics                                               |
| **Usage**    | Checkout via `stripe_service.py`; webhooks via `StripeWebhookService`       |
| **Gap**      | Local dev needs `stripe listen --forward-to localhost:8001/webhooks/stripe` |
| **Severity** | Medium (dev ergonomics)                                                     |

### PostgreSQL

| Item         | Detail                           |
| ------------ | -------------------------------- |
| **Config**   | `DATABASE_URL` (postgresql only) |
| **Health**   | `/health/ready`                  |
| **Usage**    | All commercial domain data       |
| **Severity** | None                             |

### Redis

| Item         | Detail                                            |
| ------------ | ------------------------------------------------- |
| **Config**   | `REDIS_URL`                                       |
| **Health**   | `/health/ready`, `require_redis_for_production()` |
| **Usage**    | Event bus, queues, idempotency, rate limits       |
| **Severity** | None                                              |

### Fleetbase

| Item         | Detail                            |
| ------------ | --------------------------------- |
| **Config**   | `FLEETBASE_*` in `config.py`      |
| **Health**   | Adapter bridge + API probe        |
| **Usage**    | Sole path via `fleetbase-adapter` |
| **Gap**      | Runtime WARNING when stack down   |
| **Severity** | Medium                            |

### Google Maps

| Item         | Detail                                                   |
| ------------ | -------------------------------------------------------- |
| **Config**   | `GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` |
| **Health**   | Geocode probe                                            |
| **Usage**    | Admin, merchant, website maps; `@porterchain/maps`       |
| **Gap**      | Customer tracking map not wired                          |
| **Severity** | Medium                                                   |

### Valhalla / OSRM (Routing)

| Item         | Detail                                        |
| ------------ | --------------------------------------------- |
| **Config**   | `VALHALLA_BASE_URL`, `OSRM_HOST`              |
| **Health**   | Diagnostics probes only (not `/health/ready`) |
| **Usage**    | `MapsService`, Route Center optimization      |
| **Severity** | Medium                                        |

### Firebase (Push)

| Item         | Detail                                      |
| ------------ | ------------------------------------------- |
| **Config**   | `FIREBASE_PROJECT_ID`, credentials          |
| **Health**   | Reports healthy on project_id alone         |
| **Usage**    | `FCMService` — log-only without credentials |
| **Gap**      | **HIGH** — not production-ready for push    |
| **Severity** | High                                        |

### WebSockets

| Item          | Detail                                               |
| ------------- | ---------------------------------------------------- |
| **Endpoints** | `/v1/operations/live-map/ws`, `/v1/notifications/ws` |
| **Health**    | Route registration check                             |
| **Usage**     | Live map, notification inbox                         |
| **Fallback**  | 8s HTTP poll in `useLiveMapData`                     |
| **Severity**  | Low                                                  |

---

## Health Endpoints

| Endpoint                           | Scope                                                  |
| ---------------------------------- | ------------------------------------------------------ |
| `GET /health`                      | Liveness                                               |
| `GET /health/ready`                | PostgreSQL, Redis, Stripe configured, Fleetbase bridge |
| `GET /v1/admin/diagnostics/health` | Full integration dashboard (admin RBAC)                |

---

## Findings Summary

| ID   | Integration   | Severity | Issue                                            |
| ---- | ------------- | -------- | ------------------------------------------------ |
| I-01 | Firebase      | High     | Push log-only without credentials                |
| I-02 | Stripe        | Medium   | Local webhook forwarding not documented/enforced |
| I-03 | Valhalla/OSRM | Medium   | Not in readiness probe                           |
| I-04 | Google Maps   | Medium   | Customer tracking map missing                    |
| I-05 | Fleetbase     | Medium   | Runtime dependency on docker stack               |

---

## Local Verification Commands

```bash
curl http://localhost:8001/health/ready
curl http://localhost:8001/v1/admin/diagnostics/health  # requires admin auth
stripe listen --forward-to localhost:8001/webhooks/stripe
pnpm docker:fleetbase:verify
```

---

_Security: `SECURITY_AUDIT.md` · Fleetbase: `FLEETBASE_AUDIT.md`_
