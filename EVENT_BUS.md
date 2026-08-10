# Porterchain Event Bus

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `services/event-bus` (`porterchain-event-bus`)

---

## Purpose

Porterchain is **event-driven**. Every bounded context (booking, merchant, billing, notifications, Fleetbase bridge) communicates through a **centralized event bus** — never by calling another module's service directly.

Fleetbase remains the internal logistics engine. The Fleetbase adapter reacts to domain events; booking and admin modules do not import `FleetbaseSyncService` at call sites.

---

## Architecture

```
┌─────────────────┐     emit_event()      ┌──────────────────┐
│  API modules    │ ────────────────────► │  DomainEvent DB  │
│  (publishers)   │                       │  (audit log)     │
└────────┬────────┘                       └──────────────────┘
         │
         │ publish_domain_event()
         ▼
┌─────────────────┐     Redis Streams      ┌──────────────────┐
│   EventBus      │ ────────────────────► │ porterchain:     │
│  (central)      │   porterchain:events   │ events           │
└────────┬────────┘                       └────────┬─────────┘
         │                                         │
         │ subscribe / dispatch                      │ XREADGROUP
         ▼                                         ▼
┌─────────────────┐                       ┌──────────────────┐
│ HandlerRegistry │ ◄── worker loop ───── │ apps/worker      │
│ + handlers      │                       │ consume_once()   │
└────────┬────────┘                       └──────────────────┘
         │
         ├── Fleetbase sync handler
         ├── Notification handler
         ├── Billing queue enqueue
         ├── Webhook fan-out
         └── Task queues (email, SMS, push)
```

---

## Package layout

| Path                                                 | Responsibility                                            |
| ---------------------------------------------------- | --------------------------------------------------------- |
| `porterchain_event_bus/bus.py`                       | `EventBus` — publish, subscribe, dispatch, Redis consumer |
| `porterchain_event_bus/registry.py`                  | `HandlerRegistry` — pattern matching (`order.*`)          |
| `porterchain_event_bus/envelope.py`                  | `build_envelope()` — canonical event shape                |
| `porterchain_event_bus/idempotency.py`               | Processed-event deduplication (Redis / in-memory)         |
| `porterchain_event_bus/retry.py`                     | Exponential backoff retry policy                          |
| `porterchain_event_bus/dlq.py`                       | Dead letter queue (`porterchain:events:dlq`)              |
| `porterchain_event_bus/versioning.py`                | Per-event schema version registry                         |
| `porterchain_event_bus/handlers/`                    | Default cross-module reaction wiring                      |
| `shared/python/porterchain_shared/events/catalog.py` | Canonical `DomainEventType` enum                          |
| `apps/api/.../platform/bus.py`                       | API bridge: DB audit + bus publish                        |
| `apps/api/.../booking_engine/_core.py`               | `emit_event()` — single publish entry point               |

---

## Event envelope

Every event uses this shape (snake_case in Python, camelCase in TypeScript clients):

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "order.dispatch_ready",
  "occurred_at": "2026-06-29T12:00:00Z",
  "aggregate_type": "order",
  "aggregate_id": "ord_abc123",
  "correlation_id": "quote_xyz789",
  "actor_type": "system",
  "actor_id": "",
  "actor": { "type": "system", "id": null },
  "payload": {},
  "version": 1
}
```

---

## Publish

**Rule:** Modules call `emit_event()` only. Never call `FleetbaseSyncService`, `NotificationService`, or billing code from another module.

```python
from porterchain_api.booking_engine._core import emit_event
from porterchain_shared.events.catalog import DomainEventType

emit_event(
    db,
    event_type=DomainEventType.ORDER_DISPATCH_READY,
    aggregate_type="order",
    aggregate_id=order.id,
    correlation_id=order.quote_id,
    payload={"tracking_number": order.tracking_number},
)
db.commit()
```

Flow:

1. `emit_event()` writes a `DomainEvent` row (immutable audit log).
2. `publish_domain_event()` builds an envelope and calls `EventBus.publish()`.
3. With Redis: event is appended to stream `porterchain:events`.
4. Without Redis (dev): event is stored in memory; handlers run synchronously if `dispatch_sync=True`.

---

## Subscribe

Handlers register against event type patterns:

```python
from porterchain_event_bus import get_event_bus
from porterchain_shared.events.catalog import DomainEventType

bus = get_event_bus()

def on_dispatch_ready(envelope: dict) -> None:
  ...

bus.subscribe(DomainEventType.ORDER_DISPATCH_READY, on_dispatch_ready)
bus.subscribe("order.*", on_any_order_event)  # wildcard fan-out
```

Default handlers are registered via `register_default_handlers()` at API startup and worker startup.

---

## Consume (worker)

Production: `apps/worker/run.py` runs a loop calling `EventBus.consume_once()`:

- Consumer group: `porterchain-workers`
- Consumer name: `porterchain-worker`
- Acknowledges messages with `XACK` after successful dispatch

```bash
pnpm dev:worker
```

---

## Retry

`RetryPolicy` (default: **5 attempts**, exponential backoff from **2s**, cap **900s**):

| Attempt | Delay (typical) |
| ------- | --------------- |
| 1       | immediate       |
| 2       | 2s              |
| 3       | 4s              |
| 4       | 8s              |
| 5       | 16s (capped)    |

On final failure, the event is sent to the DLQ with error metadata.

Configure:

```python
from porterchain_event_bus import EventBus, RetryPolicy

bus = EventBus(retry_policy=RetryPolicy(max_attempts=5, base_delay_seconds=2.0))
```

---

## Dead letter queue

Failed events land in `porterchain:events:dlq` (Redis) or an in-memory deque (dev).

DLQ entry:

```json
{
  "event_id": "...",
  "event_type": "order.dispatch_ready",
  "payload": {},
  "error": "Connection refused",
  "attempts": 3,
  "dead_lettered_at": "2026-06-29T12:05:00Z"
}
```

Ops should monitor DLQ depth and replay after fixing root cause.

---

## Idempotency

`IdempotencyStore` tracks processed `event_id` values:

- Redis key prefix: `porterchain:events:processed:{event_id}`
- TTL: 7 days (configurable)

Handlers that enqueue side effects (email, billing) are safe under at-least-once delivery.

---

## Logging

Structured log lines at each stage:

| Level   | Message                                          |
| ------- | ------------------------------------------------ |
| INFO    | `event published: {event_id} ({event_type})`     |
| DEBUG   | `skipping duplicate event {event_id}`            |
| WARNING | `handler failed for {event_type} attempt N/M`    |
| ERROR   | `event dead-lettered: {event_id} ({event_type})` |

---

## Event versioning

`versioning.py` maintains `EVENT_SCHEMA_VERSIONS`. Bump the version when a payload field is removed or its type changes incompatibly.

Consumers should tolerate `envelope.version <= schema_version_for(event_type)`.

```python
from porterchain_event_bus.versioning import schema_version_for, is_compatible

schema_version_for("order.booked")  # → 2
is_compatible("order.booked", 1)    # → True
```

---

## Redis keys

| Key                                 | Purpose             |
| ----------------------------------- | ------------------- |
| `porterchain:events`                | Main event stream   |
| `porterchain:events:dlq`            | Dead letter stream  |
| `porterchain:events:processed:{id}` | Idempotency markers |

---

## Local development

```bash
cd apps/api
pip install -e ../../services/event-bus -e ../../shared/python
pnpm dev:api     # handlers register on startup; sync dispatch without Redis
pnpm dev:worker  # consumes Redis stream when available
```

Set `REDIS_URL` in environment (see `ENVIRONMENT_VARIABLES.md`). Without Redis, the bus falls back to in-memory mode with synchronous handler dispatch in the API process.

---

## Adding a new handler

1. Add event type to `porterchain_shared/events/catalog.py` and `packages/events/src/catalog.ts`.
2. Register schema version in `versioning.py`.
3. Emit the event from the owning module via `emit_event()`.
4. Add a handler in `porterchain_event_bus/handlers/` or a module-specific handler file.
5. Document in `EVENT_CATALOG.md` and [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md).

**Do not** import the consuming module from the publishing module.

---

## Related documents

| Document                                                                     | Purpose                               |
| ---------------------------------------------------------------------------- | ------------------------------------- |
| [EVENT_CATALOG.md](./EVENT_CATALOG.md)                                       | Full event reference                  |
| [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md) | Lifecycle diagrams and handler wiring |
| [docs/archive/EVENT_BUS_AUDIT.md](./docs/archive/EVENT_BUS_AUDIT.md)         | Historical audit (July 2026)          |
| [DOMAIN_MODEL.md](./DOMAIN_MODEL.md)                                         | Bounded contexts and aggregates       |

---
