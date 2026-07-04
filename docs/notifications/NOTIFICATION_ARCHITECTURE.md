# Notification Architecture

> **Authority:** `masterrule.md` §6 (Logistics Orchestrator), §11.3 (Notification Engine)  
> **Owner:** `apps/api/src/porterchain_api/notification_engine/`

## Principle

**All notifications flow through the Notification Engine.** No portal, adapter, or engine module may call Firebase, SMTP, or Twilio directly.

```
Website / Merchant / Admin / Customer / Driver / Fleetbase / Stripe / Claims / Support / Finance / Orders
        ↓
Internal Event Bus (Redis Streams + DB audit)
        ↓
Notification Engine (FastAPI — Logistics Orchestrator)
        ↓
┌───────────────┬──────────────┬──────────────┬──────────────┐
│ Push (FCM)    │ Email (SMTP) │ In-App       │ SMS (future) │
└───────────────┴──────────────┴──────────────┴──────────────┘
        ↓
Users (Android / iOS / Web Push / Email / Admin bell)
```

## Components

| Component              | Path                                        | Responsibility                                                     |
| ---------------------- | ------------------------------------------- | ------------------------------------------------------------------ |
| **NotificationEngine** | `notification_engine/engine.py`             | Single dispatch entry — templates, routing, preferences, audit     |
| **EventRouter**        | `notification_engine/event_router.py`       | Maps domain events → notification specs (recipients resolved here) |
| **DeviceService**      | `notification_engine/device_service.py`     | FCM token registration, invalidation, multi-device                 |
| **FCMService**         | `notification_engine/fcm_service.py`        | Firebase Admin SDK — only FCM touchpoint                           |
| **DeliveryService**    | `notification_engine/delivery_service.py`   | Worker delivery (SMTP, Twilio, FCM, in-app)                        |
| **PreferenceService**  | `notification_engine/preference_service.py` | Per-user channel/category opt-in                                   |
| **RetryService**       | `notification_engine/retry_service.py`      | Exponential backoff, DLQ                                           |
| **RealtimeHub**        | `notification_engine/realtime.py`           | WebSocket fan-out for in-app bell                                  |

## Data Model

| Table                        | Purpose                                                   |
| ---------------------------- | --------------------------------------------------------- |
| `notification_records`       | Full audit — status, retry, opened/clicked, search fields |
| `notification_devices`       | FCM tokens per user/role/device                           |
| `notification_preferences`   | Channel + category preferences                            |
| `notification_delivery_logs` | Per-attempt delivery log (legacy + worker trace)          |

## Integration Rules

1. Modules emit **domain events** only — never enqueue email/SMS/push.
2. `EventRouter` subscribes to domain events and calls `NotificationEngine.dispatch()`.
3. `NotificationEngine` creates `NotificationRecord`, checks preferences, enqueues worker jobs via `notification.queued`.
4. Worker calls `deliver_notification()` which updates record status and writes delivery logs.
5. In-app notifications push to WebSocket subscribers immediately on create.

## RBAC

| Module               | Roles                                                             |
| -------------------- | ----------------------------------------------------------------- |
| `notifications_read` | All admin roles (read-only)                                       |
| `notifications`      | `SUPER_ADMIN`, `ADMIN`, `DISPATCHER`, `SUPPORT_LEAD`, `MARKETING` |

## Non-Goals (Future)

- Slack / Microsoft Teams channels
- SMS production (Twilio scaffold exists)
- Campaign broadcast UI (admin scaffold only)

## Related Docs

- [FCM_CONFIGURATION.md](./FCM_CONFIGURATION.md)
- [DEVICE_REGISTRATION_FLOW.md](./DEVICE_REGISTRATION_FLOW.md)
- [NOTIFICATION_EVENT_MATRIX.md](./NOTIFICATION_EVENT_MATRIX.md)
- [NOTIFICATION_DELIVERY_FLOW.md](./NOTIFICATION_DELIVERY_FLOW.md)
