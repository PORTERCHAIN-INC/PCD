# Route Center Performance

**Scope:** Enterprise Route Center admin module and `/v1/admin/route-center` API

---

## Design Principles

1. **Reuse hot paths** — Planning queue reads existing control tower query; live map reuses WS infrastructure.
2. **No N+1 Fleetbase calls in list views** — Orchestrator runs only on explicit optimize action per plan.
3. **Pagination** — `list_plans` and `history` default `limit=100` / `50`, max 500 / 200.
4. **JSON stop storage** — Avoids join-heavy stop tables for v1; suitable for < 50 stops per plan.

---

## API Latency Expectations

| Endpoint              | Typical work                | Notes                               |
| --------------------- | --------------------------- | ----------------------------------- |
| `GET /dashboard`      | 3–5 DB aggregates           | Cached client-side via `useApiData` |
| `GET /planning-queue` | 1 queue query (limit 200)   | Same cost as operations queue       |
| `GET /plans`          | Indexed status filter       | `ix_route_center_plans_status`      |
| `POST /optimize`      | O(stops) Valhalla legs      | ~15s timeout per leg; dominant cost |
| `POST /simulate`      | Same as optimize without FB | Lighter (no orchestrator)           |
| `POST /dispatch`      | O(orders) assign + FB sync  | Async retry on FB failure           |
| `GET /live-execution` | LiveMapService snapshot     | Same as operations live-map         |

---

## Routing Engine Performance

### Valhalla

- Per-leg HTTP POST with 15s timeout
- Multi-stop route with N stops → N-1 sequential requests
- **Recommendation:** Batch optimize off-peak; cap stops per plan (~30) in UI

### OSRM

- Single request for all waypoints when refining
- Preferred for full-path distance when `OSRM_URL` configured
- Falls back to Valhalla legs if OSRM unavailable

---

## Frontend Performance

| Page           | Strategy                                                   |
| -------------- | ---------------------------------------------------------- |
| Dashboard      | Single API call; KPI tiles static until refetch            |
| Planning Queue | One `planning-queue` call; checkbox selection local state  |
| Live Execution | Embeds `LiveMapApp` — uses existing WS + 15s poll fallback |
| Route 360      | Single `getPlan` includes audit + live_map snapshot        |

`useApiData` avoids duplicate fetches per mount; manual `refetch` after mutations.

---

## Database Indexes

```sql
ix_route_center_plans_status
ix_route_center_plans_zone
ix_route_center_plans_driver_id
ix_route_center_plans_vehicle_id
ix_route_center_plans_template_id
ix_route_center_templates_template_type
ix_route_center_templates_merchant_id
```

---

## Scalability Notes

| Concern              | Mitigation                                                 |
| -------------------- | ---------------------------------------------------------- |
| Large planning queue | Bucket dedup in UI; server limit 200                       |
| Concurrent optimizes | Stateless API; consider job queue for > 10 stops           |
| Live map WS fanout   | Existing ops WS scaling applies                            |
| Simulation storage   | JSON on plan row; archive completed plans to history query |

---

## Future Optimizations (not implemented)

- Background optimize job via queue worker
- OSRM `table` API for driver nearest-neighbor matrix
- Redis cache for dashboard KPIs (60s TTL)
- WebSocket channel scoped to `plan_id` for Route 360 live tab
- Stop table normalization if plans exceed 100 stops regularly

---

## Monitoring

Align with masterrule §16 Observability:

- Log `route.optimized`, `route.dispatched` via `AdminAuditLog`
- Fleetbase adapter errors → `AuditLogger` + `RetryQueue`
- Valhalla/OSRM warnings logged at `MapsService` WARNING level

Recommended metrics (Datadog / similar):

- `route_center.optimize.duration_ms`
- `route_center.optimize.stops_count`
- `route_center.dispatch.orders_count`
- `route_center.plans.by_status` gauge
