# Event Bus Audit — Porterchain Platform

**Date:** July 3, 2026  
**Last verified:** 2026-07-04  
**Status:** Historical audit snapshot

For current event infrastructure and catalog, use **[EVENT_BUS.md](./EVENT_BUS.md)** and **[EVENT_CATALOG.md](./EVENT_CATALOG.md)**.

---

## Executive verdict (July 2026)

| Area                                       | Status                             |
| ------------------------------------------ | ---------------------------------- |
| Infrastructure (Redis Streams, DLQ, retry) | **PASS**                           |
| Worker consumer (`apps/worker`)            | **PASS**                           |
| Core retail lifecycle emissions            | **PASS**                           |
| Fleetbase → canonical events               | **IMPROVED** (mapping expanded)    |
| Reverse logistics / refund events          | **PARTIAL** — billing consumer TBD |
| `notification.sent` async channels         | **FIXED**                          |

---

## Architecture (summary)

```
emit_event() → domain_events table → publish_domain_event()
    → Redis Stream (porterchain:events)
    → apps/worker → consume_once() → handlers
    → DLQ on failure (porterchain:events:dlq)
```

**Paths:** `services/event-bus/porterchain_event_bus/`, `apps/api/.../platform/bus.py`, `apps/worker/run.py`

---

## Findings log

| ID     | Severity | Issue                                                        | Status                                                         |
| ------ | -------- | ------------------------------------------------------------ | -------------------------------------------------------------- |
| EB-H01 | High     | Fleetbase event mapping incomplete                           | **Fixed** — `fleetbase-adapter/events/`                        |
| EB-H02 | High     | `notification.sent` missing for email/SMS/push               | **Fixed** — `delivery_service._mark_sent`                      |
| EB-H03 | High     | Refund events E2E-only                                       | **Partial** — claims emit `refund.*`; billing consumer pending |
| EB-M01 | Medium   | Catalog drift (`booking_engine/events.py` vs shared catalog) | Open — align on `DomainEventType`                              |
| EB-M02 | Medium   | Dual publisher paths                                         | Open — consolidate publishers                                  |
| EB-L01 | Low      | Dispatch queue processor stub                                | Documented — real dispatch via event handlers                  |

---

## Handlers registered

Via `porterchain_event_bus/handlers/__init__.py`:

- Fleetbase sync (`fleetbase_sync_handler`)
- Billing queue on `payment.succeeded`
- Notifications (`notification_handler` + queue routing)
- Merchant webhooks (`order.*` fan-out)
- Claims / cancellation / return / damage sync

See [docs/architecture/EVENT_BUS_FLOW.md](./docs/architecture/EVENT_BUS_FLOW.md) for wiring diagram.

---

## Open items (post-audit)

| Item                                                                  | Owner          |
| --------------------------------------------------------------------- | -------------- |
| Billing engine consumer for `refund.requested` / `refund.issued`      | Billing module |
| Add `booking.created` to shared catalog or deprecate engine-only type | Platform       |
| HTTP `X-Request-ID` → envelope `correlation_id` propagation           | API middleware |

---

_Related: [EVENT_BUS_REPORT.md](./EVENT_BUS_REPORT.md) · [EVENT_BUS.md](./EVENT_BUS.md) · [masterrule.md](./masterrule.md) §12_
