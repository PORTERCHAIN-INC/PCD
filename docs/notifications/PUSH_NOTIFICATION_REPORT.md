# Push Notification Report

> Audit date: 2026-06-30  
> Authority: `masterrule.md` §11.3

## Executive Summary

Porterchain had **notification scaffolding** (queues, worker, templates, event handlers) but **no production FCM delivery**, **no unified device registry**, and **several architecture violations**. This report documents the pre-implementation state and the enterprise engine delivery.

---

## Already Implemented

| Area | Evidence |
|------|----------|
| Notification Engine module | `apps/api/src/porterchain_api/notification_engine/` |
| Worker queue routing | `apps/worker/processors/__init__.py` — EMAILS, SMS, PUSH |
| Event bus handler | `notification.queued` → Redis queues |
| Email delivery | SMTP via `delivery_service.py` (log-only without SMTP) |
| SMS scaffold | Twilio via `delivery_service.py` (log-only without Twilio) |
| Templates (10) | `templates.py` |
| Delivery audit table | `notification_delivery_logs` |
| Booking confirmation flow | `NotificationOrchestrator.send_booking_confirmation` |
| Driver push register endpoint | `POST /driver-api/v1/push/register` (legacy JSON storage) |
| Admin integration health | Settings → Firebase / SMTP / push status |
| Domain event catalog | `shared/python/porterchain_shared/events/catalog.py` |

---

## Partially Implemented

| Area | Gap |
|------|-----|
| **FCM push** | `_send_push()` logs only; no `firebase-admin` |
| **Device tokens** | Stored in `driver.performance` JSON, not dedicated table |
| **Event handlers** | Only 4 events wired; recipient payload shape broken (dict vs string) |
| **Templates** | Missing `order_booked`, `driver_alert`, tracking lifecycle templates |
| **Admin send push** | Audit log only — no engine dispatch |
| **In-app notifications** | No model, bell, or WebSocket |
| **Preferences** | No user opt-out |
| **Retry / DLQ** | Failed status logged; no backoff |
| **Env vars** | `FIREBASE_CREDENTIALS_PATH`, `PORTERCHAIN_DRIVER_PUSH_*` documented but unwired |
| **Mobile app** | No `expo-notifications` client |

---

## Missing

| Area | Required by spec |
|------|------------------|
| `notification_records` table | Full audit lifecycle |
| `notification_devices` table | FCM token management |
| `notification_preferences` table | Category × channel prefs |
| `NotificationEngine.dispatch()` | Single entry point |
| `FCMService` | Firebase Admin SDK |
| `EventRouter` | All domain events → notifications |
| Admin `/admin/notifications` | Dashboard, queue, history, devices |
| WebSocket realtime bell | `/v1/notifications/ws` |
| Recipient routing engine | No hardcoded recipients in modules |
| Search across notifications | Recipient, order, tracking, claim |
| Campaign / broadcast | Future |
| Slack / Teams | Future |

---

## Duplicate Logic

| Location | Issue | Resolution |
|----------|-------|------------|
| `services/python/porterchain_services/notifications/service.py` | Direct Redis enqueue bypassing engine | Deprecate; route through `NotificationEngine` |
| `notification_engine/orchestrator.py` | Direct `DeliveryService.enqueue` | Refactor to `NotificationEngine.dispatch` |
| `services/driver-platform/porterchain_driver/push.py` | Own `notify_driver` + JSON token storage | Delegate to `DeviceService` + `NotificationEngine` |
| `booking_engine/notification_handler.py` | Parallel queue path | Refactor to `EventRouter` |
| `booking_engine/notification_service.py` | Thin wrapper | Keep as facade over engine |

---

## Architecture Violations

| Violation | Severity | Fix |
|-----------|----------|-----|
| Admin `POST /drivers/{id}/action` type=push — no engine call | High | Wire to `NotificationEngine.dispatch` |
| `notification_handler._queue_notification` recipient dict | High | Normalize in engine |
| `porterchain_services` direct queue enqueue | Medium | Deprecate |
| FCM referenced but never called | High | Implement `FCMService` |
| Modules would hardcode email in event payloads | Medium | `EventRouter` resolves recipients |

---

## Implementation Delivered

See `docs/notifications/NOTIFICATION_ARCHITECTURE.md` for the post-implementation architecture.

| Deliverable | Status |
|-------------|--------|
| Enterprise models + migration | ✅ |
| `NotificationEngine` single entry | ✅ |
| `FCMService` + env wiring | ✅ |
| `DeviceService` unified registration | ✅ |
| `EventRouter` for domain events | ✅ |
| Retry with exponential backoff | ✅ |
| Admin API + `/admin/notifications` UI | ✅ |
| WebSocket in-app realtime | ✅ |
| Handler refactor (no direct sends) | ✅ |

---

## Verification Checklist

- [ ] Run `alembic upgrade head`
- [ ] Set `FIREBASE_PROJECT_ID` + credentials in API/worker
- [ ] Register device from client
- [ ] Trigger `booking.confirmed` → email + in-app
- [ ] Trigger `order.driver_assigned` → driver push
- [ ] Admin `/admin/notifications` shows queue + history
- [ ] WebSocket bell updates on new in-app notification
- [ ] Failed push retries with backoff
- [ ] Invalid FCM token deactivated
