# Notification Architecture


**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Authority:** `masterrule.md` §6 (Logistics Orchestrator), §11.3 (Notification Engine)  
**Owner:** `apps/api/src/porterchain_api/notification_engine/`  
**See also:** [NOTIFICATION_FLOW.md](../architecture/NOTIFICATION_FLOW.md) · [NOTIFICATION_REPORT.md](../../NOTIFICATION_REPORT.md)

---

## Principle

**All notifications flow through the Notification Engine.** No portal, adapter, or engine module may call Firebase, SMTP, or Twilio directly.

```
Domain modules (booking, orders, claims, support, Fleetbase, Stripe)
        ↓
Internal Event Bus (Redis Streams + domain_events audit)
        ↓
notification_engine/event_router.py → NotificationEngine.dispatch()
        ↓
notification.queued → worker queues (emails | sms | push)
        ↓
DeliveryService → FCM / SMTP / log-only SMS
        ↓
Users (mobile push / email / in-app bell via WebSocket)
```

## Components

| Component | Path | Responsibility |
| --------- | ---- | -------------- |
| **NotificationEngine** | `notification_engine/engine.py` | Dispatch, preferences, retry scheduling, in-app realtime |
| **EventRouter** | `notification_engine/event_router.py` | Maps domain events → notification specs |
| **DeviceService** | `notification_engine/device_service.py` | FCM token registration, invalidation |
| **FCMService** | `notification_engine/fcm_service.py` | Firebase Admin SDK — only FCM touchpoint |
| **DeliveryService** | `notification_engine/delivery_service.py` | SMTP, FCM, SMS (log-only) |
| **PreferenceService** | `notification_engine/preference_service.py` | Per-user channel/category opt-in |
| **RealtimeHub** | `notification_engine/realtime.py` | WebSocket fan-out for in-app bell |
| **NotificationOrchestrator** | `notification_engine/orchestrator.py` | Direct sends (e.g. checkout recovery) |

There is no separate `retry_service.py` — retries use `NotificationEngine.schedule_retry()` on the record.

## Data Model

| Table | Purpose |
| ----- | ------- |
| `notification_records` | Full audit — status, retry, opened/clicked, search fields |
| `notification_devices` | FCM tokens per user/role/device |
| `notification_preferences` | Channel + category preferences |
| `notification_delivery_logs` | Per-attempt delivery log |

## Integration Rules

1. Modules emit **domain events** only — never enqueue email/SMS/push directly.
2. `register_notification_handlers()` subscribes domain events → `event_router.handle_domain_event`.
3. `NotificationEngine.dispatch()` creates `NotificationRecord`, checks preferences, emits `notification.queued` for async channels.
4. Event handler routes `notification.queued` → `emails` / `sms` / `push` Redis queues.
5. Worker `processors/notifications.py` → `deliver_notification()`.
6. `channel=in_app` broadcasts immediately via `RealtimeHub` (no worker queue).

## User API

| Route | Purpose |
| ----- | ------- |
| `POST /v1/notifications/devices/register` | Register FCM token |
| `GET /v1/notifications/inbox` | In-app notification center |
| `PATCH /v1/notifications/preferences` | Channel preferences |
| `WS /v1/notifications/ws?token=` | In-app realtime bell |

## Admin API

`/v1/admin/notifications/*` — dashboard, failed queue, manual retry, broadcast scaffold.

## RBAC

| Module | Roles |
| ------ | ----- |
| `notifications_read` | All admin roles (read-only) |
| `notifications` | `SUPER_ADMIN`, `ADMIN`, `DISPATCHER`, `SUPPORT_LEAD`, `MARKETING` |

## Channel Status (July 2026)

| Channel | Status |
| ------- | ------ |
| Email | SMTP when configured; log-only without `smtp_host` |
| Push (FCM) | Production-ready path; log-only without Firebase creds |
| In-app | Live — DB + WebSocket |
| SMS | **Log-only** — no Twilio integration yet |

## Related Docs

- [FCM_CONFIGURATION.md](./FCM_CONFIGURATION.md)
- [DEVICE_REGISTRATION_FLOW.md](./DEVICE_REGISTRATION_FLOW.md)
- [NOTIFICATION_EVENT_MATRIX.md](./NOTIFICATION_EVENT_MATRIX.md)
- [NOTIFICATION_DELIVERY_FLOW.md](./NOTIFICATION_DELIVERY_FLOW.md)
- [NOTIFICATION_TEMPLATE_CATALOG.md](./NOTIFICATION_TEMPLATE_CATALOG.md)
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](../../masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../../CTO_AUDIT_REPORT.md) | Doc vs code audit |
