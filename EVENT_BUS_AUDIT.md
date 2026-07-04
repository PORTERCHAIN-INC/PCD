# Event Bus Audit — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` §12, ADR-005

---

## Executive Verdict

| Area | Status |
|------|--------|
| Infrastructure (Redis Streams, DLQ, retry) | **PASS** |
| Worker consumer | **PASS** |
| Core retail lifecycle emissions | **PASS** |
| Fleetbase → canonical events | **IMPROVED** (fixed mapping) |
| Reverse logistics events | **PARTIAL** (claims wired) |
| `notification.sent` async channels | **FIXED** |

---

## Architecture

```
Application Service → emit_event() → domain_events table
                              ↓
                    publish_domain_event()
                              ↓
              Redis Stream (porterchain:events)
                              ↓
              apps/worker → consume_once() → handlers
                              ↓ (failure)
              DLQ (porterchain:events:dlq)
```

**Paths:**
- `services/event-bus/porterchain_event_bus/`
- `apps/api/src/porterchain_api/platform/bus.py`
- `apps/worker/run.py`

---

## Required Events Matrix

| Event (canonical) | Catalog | Emitted (prod) | Publisher | Consumer |
|-------------------|---------|----------------|-----------|----------|
| BookingCreated (`booking.created`) | ⚠️ engine only | ✅ | `confirmation_service` | Notifications |
| PaymentSucceeded (`payment.succeeded`) | ✅ | ✅ | `payment_service.mark_succeeded` | Billing, notifications |
| OrderCreated (`order.created`) | ✅ | ✅ | `confirmation_service` | Fleetbase sync, notifications |
| DriverAssigned (`order.driver_assigned`) | ✅ | ⚠️ Partial | Driver platform, FB webhooks | Notifications |
| PickupStarted (`order.arrived_pickup`) | ✅ | ⚠️ Partial | Driver stops, FB (fixed map) | Notifications |
| PickedUp (`order.pickup_completed`) | ✅ | ⚠️ Partial | Driver stops, FB (fixed map) | Notifications |
| Delivered (`order.delivered`) | ✅ | ⚠️ Partial | Driver stops, FB | Notifications |
| PODCompleted (`order.pod_completed`) | ✅ | ⚠️ Partial | `porterchain_driver/pod.py` | Notifications |
| InvoiceGenerated (`order.invoiced`) | ✅ | ✅ | `confirmation_service` | Billing |
| NotificationSent (`notification.sent`) | ✅ | ✅ Fixed | `notification_engine`, `delivery_service` | Analytics |
| ReturnRequested (`refund.requested`) | ✅ | ⚠️ Partial | Claims, FB returns (fixed map) | Billing (TBD) |
| RefundCompleted (`refund.issued`) | ✅ | ⚠️ Partial | Claims compensation | Billing (TBD) |

---

## Infrastructure Checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Publisher | ✅ | `emit_event` + `publish_domain_event` |
| Consumer | ✅ | `apps/worker` consumer group `porterchain-workers` |
| Retry | ✅ | 5 attempts, exponential backoff (2s–900s) |
| Dead Letter Queue | ✅ | `porterchain:events:dlq`, maxlen 50k |
| Idempotency | ✅ | `RedisIdempotencyStore`, 7-day TTL |
| Stripe dedupe | ✅ | `stripe:{event_id}` |
| Correlation ID | ⚠️ Partial | Envelope field; HTTP `X-Request-ID` not auto-propagated |

---

## Findings

### EB-H01 — Fleetbase event mapping incomplete (High) — FIXED

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Root Cause** | `FLEETBASE_EVENT_TO_DOMAIN_EVENT` had 7 entries; `order.started` mapped to wrong event |
| **Fix Applied** | Expanded mapping in `fleetbase-adapter/events/__init__.py` |
| **Effort** | 2 hours (done) |

### EB-H02 — `notification.sent` missing for email/SMS/push (High) — FIXED

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Root Cause** | Only in_app channel emitted; worker `_mark_sent` updated DB only |
| **Fix Applied** | `delivery_service._mark_sent` now emits `notification.sent` |
| **Effort** | 1 hour (done) |

### EB-H03 — Refund events E2E-only (High) — PARTIAL FIX

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Root Cause** | Claims used ad-hoc `claim.*` types |
| **Fix Applied** | `refund.requested` on payment_dispute/chargeback; `refund.issued` on compensation |
| **Remaining** | Billing engine consumer for refund events |
| **Effort** | 1 day remaining |

### EB-M01 — Catalog drift (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | `booking_engine/events.py` vs `porterchain_shared/events/catalog.py` diverge |
| **Recommended Fix** | Add `booking.created` to `DomainEventType`; deprecate duplicates |
| **Effort** | 4 hours |

### EB-M02 — Dual publisher paths (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | `porterchain_shared.events.publisher` + `porterchain_event_bus` |
| **Recommended Fix** | Consolidate to single publisher |
| **Effort** | 1 day |

### EB-L01 — Dispatch queue processor stub (Low)

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Root Cause** | `processors/dispatch.py` logs only; real dispatch via event handlers |
| **Effort** | Document or remove stub |

---

## Handlers Registered

Via `porterchain_event_bus/handlers/__init__.py`:
- Fleetbase sync (`fleetbase_sync_handler`)
- Billing (`billing_handler`)
- Notifications (`notification_handler`)
- Merchant webhooks
- Booking notifications

---

*Stripe webhook idempotency: `BOOKING_WORKFLOW_AUDIT.md` · DLQ monitoring: `PERFORMANCE_AUDIT.md`*
