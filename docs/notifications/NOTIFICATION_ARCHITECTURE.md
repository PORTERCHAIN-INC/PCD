# Notification Architecture

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-08-07

**Authority:** `masterrule.md` §6 (Logistics Orchestrator), §11.3 (Notification Engine)  
**Owner:** `apps/api/src/porterchain_api/notification_engine/`  
**See also:** [NOTIFICATION_UPGRADE_PLAN.md](./NOTIFICATION_UPGRADE_PLAN.md) · [NOTIFICATION_FLOW.md](../architecture/NOTIFICATION_FLOW.md) · [ZOHO_MAIL.md](./ZOHO_MAIL.md) · [FCM_CONFIGURATION.md](./FCM_CONFIGURATION.md)

---

## Principle

**All notifications flow through the Notification Engine.** No portal, adapter, or engine module may call Firebase, SMTP, or Twilio directly (auth-critical staff activate mail is the documented sync bypass via `staff_mail`).

```
Domain modules (booking, orders, claims, support, Fleetbase, Stripe)
        ↓
Internal Event Bus (Redis Streams + domain_events audit)
        ↓
hydrate_order_context (if thin payload) → event_router → staff fan-out
        ↓
NotificationEngine.dispatch() — idempotent; in_app immediate; email/sms/push queued
        ↓
notification.queued → worker queues (emails | sms | push)
        ↓
DeliveryService → FCM / SMTP / log-only SMS (skips if already sent)
        ↓
Users (mobile push / email / in-app bell via WebSocket)
```

## Phase 1 trigger matrix (trust baseline)

| Event                                                 | Customer            | Merchant       | Driver       | Ops staff (RBAC)          |
| ----------------------------------------------------- | ------------------- | -------------- | ------------ | ------------------------- |
| `booking.confirmed`                                   | email, push, in_app | in_app         | —            | in_app (`dispatch` roles) |
| `order.driver_assigned`                               | push, in_app        | in_app         | push, in_app | in_app                    |
| `fleetbase.status_updated`                            | push, in_app        | in_app         | —            | in_app on key states      |
| `payment.failed`                                      | email, in_app       | —              | —            | —                         |
| receipt / invoice                                     | email / in_app      | email / in_app | —            | finance module in_app     |
| `exception.opened` / `order.delayed` / `sla.breached` | email, push, in_app | in_app         | —            | in_app                    |
| claim / support                                       | email / in_app      | —              | conditional  | support module in_app     |

Staff fan-out uses real `AdminUser.id` (never `recipient_id="system"`). See [NOTIFICATION_UPGRADE_PLAN.md](./NOTIFICATION_UPGRADE_PLAN.md).

## Components

| Component                    | Path                                        | Responsibility                                           |
| ---------------------------- | ------------------------------------------- | -------------------------------------------------------- |
| **NotificationEngine**       | `notification_engine/engine.py`             | Dispatch, preferences, retry scheduling, in-app realtime |
| **EventRouter**              | `notification_engine/event_router.py`       | Maps domain events → notification specs                  |
| **Context**                  | `notification_engine/context.py`            | Order hydrate + deep links                               |
| **StaffFanout**              | `notification_engine/staff_fanout.py`       | RBAC topic → active AdminUser recipients                 |
| **DeviceService**            | `notification_engine/device_service.py`     | FCM token registration, invalidation                     |
| **FCMService**               | `notification_engine/fcm_service.py`        | Firebase Admin SDK — only FCM touchpoint                 |
| **DeliveryService**          | `notification_engine/delivery_service.py`   | SMTP, FCM, SMS (log-only)                                |
| **PreferenceService**        | `notification_engine/preference_service.py` | Per-user channel/category opt-in                         |
| **RealtimeHub**              | `notification_engine/realtime.py`           | WebSocket fan-out for in-app bell                        |
| **NotificationOrchestrator** | `notification_engine/orchestrator.py`       | Direct sends (e.g. checkout recovery)                    |

There is no separate `retry_service.py` — retries use `NotificationEngine.schedule_retry()` on the record.

## Data Model

| Table                        | Purpose                                                   |
| ---------------------------- | --------------------------------------------------------- |
| `notification_records`       | Full audit — status, retry, opened/clicked, search fields |
| `notification_devices`       | FCM tokens per user/role/device                           |
| `notification_preferences`   | Channel + category preferences                            |
| `notification_delivery_logs` | Per-attempt delivery log                                  |

## Integration Rules

1. Modules emit **domain events** only — never enqueue email/SMS/push directly.
2. `register_notification_handlers()` subscribes domain events → `event_router.handle_domain_event`.
3. Router hydrates Order context when payload is thin; expands `__staff:{topic}__` to real admins.
4. `NotificationEngine.dispatch()` creates `NotificationRecord` (idempotent), checks preferences, emits `notification.queued` for async channels — **no inline SMTP**.
5. Event handler routes `notification.queued` → `emails` / `sms` / `push` Redis queues.
6. Worker `processors/notifications.py` → `deliver_notification()` (no-op if already sent).
7. `channel=in_app` broadcasts immediately via `RealtimeHub` (no worker queue).

## User API

| Route                                     | Purpose                    |
| ----------------------------------------- | -------------------------- |
| `POST /v1/notifications/devices/register` | Register FCM token         |
| `GET /v1/notifications/inbox`             | In-app notification center |
| `PATCH /v1/notifications/preferences`     | Channel preferences        |
| `WS /v1/notifications/ws?token=`          | In-app realtime bell       |

## Admin API

`/v1/admin/notifications/*` — dashboard, failed queue, manual retry, broadcast scaffold.

## RBAC

| Module               | Roles                                                             |
| -------------------- | ----------------------------------------------------------------- |
| `notifications_read` | All admin roles (read-only)                                       |
| `notifications`      | `SUPER_ADMIN`, `ADMIN`, `DISPATCHER`, `SUPPORT_LEAD`, `MARKETING` |

## Channel Status (August 2026)

| Channel    | Status                                                  |
| ---------- | ------------------------------------------------------- |
| Email      | SMTP when configured; worker delivery only              |
| Push (FCM) | Production-ready path; log-only without Firebase creds  |
| In-app     | Live — DB + WebSocket; staff fan-out by RBAC            |
| SMS        | **Log-only** until `PORTERCHAIN_SMS_ENABLED` + provider |

## Phase 3 polish

- Quiet hours: `GET/PATCH /v1/notifications/settings` (mutes push/SMS; critical exempt)
- Channel fallback: failed push → SMS → email when addresses/prefs allow
- Delivery receipts: `GET /v1/admin/notifications/{id}/delivery-logs`
- Alias: `merchant.invoice_generated` → same specs as `merchant.billed`
- Legacy `porterchain_services.notifications` is deprecated

## Related Docs

- [NOTIFICATION_UPGRADE_PLAN.md](./NOTIFICATION_UPGRADE_PLAN.md)
- [FCM_CONFIGURATION.md](./FCM_CONFIGURATION.md)
- [ZOHO_MAIL.md](./ZOHO_MAIL.md)

---
