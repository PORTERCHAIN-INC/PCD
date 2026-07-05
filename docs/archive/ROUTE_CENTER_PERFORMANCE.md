# Route Center Performance

**Last verified:** 2026-07-04  
**Scope:** Enterprise Route Center admin module and `/v1/admin/route-center` API  
**Architecture:** [ROUTE_CENTER_ARCHITECTURE.md](./ROUTE_CENTER_ARCHITECTURE.md)

---

## Design principles

1. **Reuse hot paths** — Planning queue reads Control Tower query; live map reuses WS infrastructure.
2. **No N+1 Fleetbase in list views** — Orchestrator runs only on explicit `POST .../optimize` per plan.
3. **Pagination** — `list_plans` default `limit=100` (max 500); `history` default 50 (max 200).
4. **JSON stop storage** — Avoids join-heavy stop tables for v1; suitable for < 50 stops per plan.

---

## API latency expectations

| Endpoint | Typical work | Notes |
| -------- | ------------ | ----- |
| `GET /dashboard` | 3–5 DB aggregates + tower stats | Client refetch via `useApiData` |
| `GET /planning-queue` | 1 queue query (limit 200) | Same cost as operations queue |
| `GET /plans` | Indexed status filter | `ix_route_center_plans_status` |
| `POST /optimize` | O(stops) Valhalla legs | ~15s timeout per leg; dominant cost |
| `POST /simulate` | Same routing without Fleetbase orchestrator | Lighter than optimize |
| `POST /dispatch` | O(orders) assign + FB sync | Async retry on FB failure |
| `GET /live-execution` | `LiveMapService.snapshot` | Same as operations live-map |

---

## Routing engine performance

### Valhalla

- Per-leg HTTP POST, 15s timeout in `MapsService`
- N stops → N−1 sequential requests in `route_distance_meters`
- **Recommendation:** Cap stops per plan (~30) in UI; batch optimize off-peak

### OSRM

- Optional refinement via `_osrm_leg_matrix` on optimize when `engine=osrm`
- Falls back to Valhalla leg sum if OSRM unavailable

See [ROUTING_ENGINE_AUDIT.md](./ROUTING_ENGINE_AUDIT.md).

---

## Frontend performance

| Page | Strategy |
| ---- | -------- |
| Dashboard | Single API call; KPI tiles until refetch |
| Planning Queue | One `planning-queue` call; checkbox selection local |
| Live Execution | Embeds `LiveMapApp` — WS + poll fallback |
| Route 360 | Single `getPlan` includes audit + live snapshot |

`useApiData` avoids duplicate fetches per mount; manual `refetch` after mutations.

Client: `apps/admin/src/lib/route-center.ts`

---

## Database indexes

```
ix_route_center_plans_status
ix_route_center_plans_zone
ix_route_center_plans_driver_id
ix_route_center_plans_vehicle_id
ix_route_center_plans_template_id
ix_route_center_templates_template_type
ix_route_center_templates_merchant_id
```

---

## Scalability notes

| Concern | Mitigation |
| ------- | ---------- |
| Large planning queue | Bucket dedup in UI; server limit 200 |
| Concurrent optimizes | Stateless API; consider worker queue for > 10 stops |
| Live map WS fanout | Existing ops WS scaling applies |
| Simulation storage | JSON on plan row; history query for completed plans |

---

## Future optimizations (not implemented)

- Background optimize job via `apps/worker/`
- OSRM `table` API for driver nearest-neighbor matrix
- Redis cache for dashboard KPIs (60s TTL)
- WebSocket channel scoped to `plan_id` for Route 360 live tab
- Stop table normalization if plans exceed 100 stops regularly

---

## Monitoring

Align with masterrule §16:

- `route.optimized`, `route.dispatched` → `AdminAuditLog`
- Fleetbase adapter errors → `AuditLogger` + `RetryQueue`
- Valhalla/OSRM warnings → `MapsService` at WARNING level

Suggested metrics:

- `route_center.optimize.duration_ms`
- `route_center.optimize.stops_count`
- `route_center.dispatch.orders_count`
- `route_center.plans.by_status`
