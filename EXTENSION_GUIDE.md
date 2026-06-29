# Extension Guide — Fleetbase Adapter

**Document version:** 1.0  
**Date:** June 29, 2026  
**Package:** `services/fleetbase-adapter/`

---

## Purpose

This guide explains how to extend Porterchain's Fleetbase integration **without modifying Fleetbase core** or leaking Porterchain business logic into upstream code.

---

## Extension layers

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Porterchain API (apps/api/)                   │
│  Business rules, pricing, auth, webhooks to merchants   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Layer 2: Fleetbase Adapter (services/fleetbase-adapter)│
│  HTTP client, mappers, events, retries — EXTEND HERE      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Layer 3: Fleetbase Bridge Extension (future Composer pkg)│
│  /int/v1/porterchain/* routes, SSO trust, custom sync    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Layer 4: Fleetbase OSS (apps/fleetbase/) — READ ONLY     │
│  core-api, fleetops-api, console                        │
└─────────────────────────────────────────────────────────┘
```

---

## When to extend the adapter (Layer 2)

Extend `services/fleetbase-adapter/` when you need to:

| Need | Where |
|------|-------|
| New Fleetbase resource sync (e.g. facilities) | New module + service class |
| Additional order meta fields | `mappers.py` |
| New webhook event mapping | `events/__init__.py` |
| New Fleetbase API endpoint wrapper | Existing service module or new one |
| Custom retry / error handling | `retry.py`, `errors.py` |
| POD normalization changes | `pod/__init__.py` |

### Example: add a new webhook event

```python
# services/fleetbase-adapter/porterchain_fleetbase_adapter/events/__init__.py

FLEETBASE_EVENT_TO_ORDER_STATE["order.arrived_at_dropoff"] = "AT_DROPOFF"
FLEETBASE_EVENT_TO_DOMAIN_EVENT["order.arrived_at_dropoff"] = "order.arrived_at_dropoff"
```

Then handle the new Porterchain state in `apps/api/booking_engine/fleetbase_sync_service.py`.

### Example: add a new Fleetbase API call

```python
# services/fleetbase-adapter/porterchain_fleetbase_adapter/orders/__init__.py

def mark_ready(self, fleetbase_order_id: str) -> dict[str, Any] | None:
    try:
        return self.client.patch(f"/v1/orders/{fleetbase_order_id}/ready")
    except Exception as exc:
        self.errors.log_and_suppress(exc, "Fleetbase ready failed")
        return None
```

Expose via `FleetbaseAdapter` in `integration.py` if needed by the API.

---

## When to extend the Fleetbase bridge (Layer 3)

Create a **separate Composer extension package** when you need:

| Need | Example endpoint |
|------|------------------|
| Porterchain SSO token exchange | `POST /int/v1/porterchain/sso/exchange` |
| Permission sync from Porterchain RBAC | `POST /int/v1/porterchain/sso/users/{uuid}/permissions` |
| Bulk order import with Porterchain IDs | `POST /int/v1/porterchain/orders/bulk` |
| Custom webhook signing scheme | Bridge middleware |

Install the extension into the Fleetbase Docker image — never patch `apps/fleetbase/api/routes/`.

Adapter client calls for bridge routes go in `auth/__init__.py` or a new `bridge/` module.

---

## When to extend Porterchain API (Layer 1)

| Need | Location |
|------|----------|
| When to sync orders (after Stripe payment) | `booking_engine/` |
| Merchant-specific dispatch rules | `admin_engine/` |
| Public tracking response shape | `routers/orders.py` |
| Outbound merchant webhooks | `routers/webhooks.py` |

The API calls adapter methods — it does not construct Fleetbase payloads directly.

---

## Adding a new adapter module

1. Create `services/fleetbase-adapter/porterchain_fleetbase_adapter/<module>/__init__.py`
2. Implement a service class accepting `(FleetbaseSettings, FleetbaseClient, ErrorHandler)`
3. Register on `FleetbaseAdapter` in `integration.py`
4. Export from `__init__.py` `__all__`
5. Add shim re-export in `services/fleetbase/porterchain_fleetbase/<module>/` if needed
6. Wire in `apps/api/` via `fleetbase_integration.py` factory
7. Document in [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)

---

## Mapper guidelines

- Put Porterchain → Fleetbase field mapping in `mappers.py`
- Always include `meta.porterchain_order_id` for webhook correlation
- Never send Stripe customer IDs, invoice amounts, or contract terms
- Use `place_from_address()` for geo fields — do not duplicate address logic in API

---

## Event translation guidelines

- Fleetbase events are the source of truth for **execution state**
- Porterchain `OrderState` enum is the source of truth for **customer-facing status**
- Unmapped events should log at DEBUG and return `None` from `WebhookService.process`
- Add domain events to `packages/events` catalog when introducing new transitions

---

## Testing extensions

```bash
cd apps/api
source .venv/bin/activate
pip install -e ../../services/fleetbase-adapter

python -c "
from porterchain_fleetbase_adapter.events import EventTranslator
t = EventTranslator()
assert t.resolve_order_state('order.completed') == 'DELIVERED'
print('ok')
"
```

Integration tests against a running Fleetbase stack:

```bash
pnpm docker:fleetbase:up
pnpm dev:api
```

---

## Anti-patterns

| Anti-pattern | Correct approach |
|--------------|------------------|
| `httpx.post('http://fleetbase:8000/v1/orders')` in API | Use `OrderService` |
| Edit `apps/fleetbase/api/app/Http/` | Fleetbase bridge extension |
| Store merchant pricing in Fleetbase meta | Keep in Porterchain DB |
| Fork `fleetops-api` | Use adapter mappers + bridge routes |
| Import adapter from `website/` | Website → API only |

---

## Related documents

- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [FLEETBASE_EXTENSION_POINTS.md](./FLEETBASE_EXTENSION_POINTS.md)
- [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)
- [CONTRIBUTING_GUIDE.md](./CONTRIBUTING_GUIDE.md)
