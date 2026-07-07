# Extension Guide — Fleetbase Adapter

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `services/fleetbase-adapter/`

> **Architecture:** [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md) · **Fleetbase extensions:** [FLEETBASE_EXTENSION_POINTS.md](./FLEETBASE_EXTENSION_POINTS.md)

---

## Purpose

Extend Porterchain's Fleetbase integration **without modifying Fleetbase core** or leaking Porterchain business logic into upstream code.

---

## Extension layers

```
Layer 1: Porterchain API (apps/api/) — business rules, fleetbase_engine/
Layer 2: Fleetbase Adapter (services/fleetbase-adapter/) — EXTEND HERE
Layer 3: Fleetbase bridge extension (Composer pkg) — SSO / tailored routes
Layer 4: Fleetbase OSS (apps/fleetbase/) — READ ONLY
```

---

## When to extend the adapter (Layer 2)

| Need                     | Where                      |
| ------------------------ | -------------------------- |
| New resource sync        | New module + service class |
| Order meta fields        | `mappers.py`               |
| Webhook event mapping    | `events/__init__.py`       |
| New API endpoint wrapper | Service module             |
| Retry / error handling   | `retry.py`, `errors.py`    |
| POD normalization        | `pod/__init__.py`          |

### Example: add a webhook event

```python
# services/fleetbase-adapter/porterchain_fleetbase_adapter/events/__init__.py

FLEETBASE_EVENT_TO_DOMAIN_EVENT["order.arrived_at_dropoff"] = "order.near_delivery"
```

Then ensure `fleetbase_engine/WebhookProcessor` handles the resulting Porterchain state.

### Example: add an API call

Expose via `OrderService` → `FleetbaseAdapter` in `integration.py`; wire from `fleetbase_engine/`, not routers directly.

---

## When to extend the Fleetbase bridge (Layer 3)

Separate Composer extension for:

| Need               | Endpoint                                                |
| ------------------ | ------------------------------------------------------- |
| SSO token exchange | `POST /int/v1/porterchain/sso/exchange`                 |
| Permission sync    | `POST /int/v1/porterchain/sso/users/{uuid}/permissions` |

Client stubs: `porterchain_fleetbase_adapter/auth/`. SSO extension deploy still required on Fleetbase side.

---

## When to extend Porterchain API (Layer 1)

| Need              | Location                                                                          |
| ----------------- | --------------------------------------------------------------------------------- |
| Sync triggers     | `fleetbase_engine/`, event handlers in `booking_engine/fleetbase_sync_handler.py` |
| Dispatch rules    | `admin_engine/`                                                                   |
| Tracking response | `booking_engine/tracking_service.py`                                              |
| Merchant webhooks | `merchant_engine/webhook_delivery_service.py`                                     |

API calls adapter via `get_fleetbase_integration()` — never construct Fleetbase payloads in routers.

---

## Adding a new adapter module

1. Create `services/fleetbase-adapter/porterchain_fleetbase_adapter/<module>/__init__.py`
2. Service class accepts `(FleetbaseSettings, FleetbaseClient, ErrorHandler)`
3. Register on `FleetbaseAdapter` in `integration.py`
4. Wire in `apps/api/services/fleetbase_integration.py`
5. Document in [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)

---

## Mapper guidelines

- Porterchain → Fleetbase mapping in `mappers.py`
- Always include `meta.porterchain_order_id` for webhook correlation
- Never send Stripe IDs, invoice amounts, or contract terms to Fleetbase

---

## Testing

```bash
cd apps/api && pip install -e ../../services/fleetbase-adapter
pnpm docker:fleetbase:up
pnpm dev:api
```

---

## Anti-patterns

| Anti-pattern                       | Correct approach            |
| ---------------------------------- | --------------------------- |
| Direct `httpx` to Fleetbase in API | Use adapter services        |
| Edit `apps/fleetbase/api/`         | Fleetbase extension package |
| Import adapter from frontends      | Frontend → API only         |

---

## Related documents

| Document                                                                       | Purpose             |
| ------------------------------------------------------------------------------ | ------------------- |
| [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)       | Adapter structure   |
| [services/fleetbase-adapter/README.md](./services/fleetbase-adapter/README.md) | Package quick start |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
