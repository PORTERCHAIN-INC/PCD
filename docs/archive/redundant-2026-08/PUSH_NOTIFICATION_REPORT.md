# Push Notification Report

**Type:** REPORT
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [NOTIFICATION_ARCHITECTURE.md](NOTIFICATION_ARCHITECTURE.md) (canonical doc).

**Original audit:** 2026-06-30  
**Authority:** `masterrule.md` §11.3

> **Current architecture:** [NOTIFICATION_ARCHITECTURE.md](./NOTIFICATION_ARCHITECTURE.md) · **E2E snapshot:** [NOTIFICATION_REPORT.md](../../NOTIFICATION_REPORT.md) (`pnpm validate:e2e:reports`)

This document records the **June 2026 pre-implementation audit** and the **July 2026 delivered state**. Use the architecture docs for day-to-day reference.

---

## Executive Summary (June 2026 baseline)

Porterchain had notification scaffolding (queues, worker, templates, handlers) but incomplete FCM delivery, fragmented device storage, and partial event routing. An enterprise notification engine was delivered in the same audit cycle.

---

## Delivered (July 2026) ✅

| Deliverable                          | Evidence                                                                   |
| ------------------------------------ | -------------------------------------------------------------------------- |
| Enterprise models + migration        | `notification_records`, `notification_devices`, `notification_preferences` |
| `NotificationEngine.dispatch()`      | `notification_engine/engine.py`                                            |
| `FCMService` (Firebase Admin SDK)    | `notification_engine/fcm_service.py`                                       |
| `DeviceService` unified registration | `POST /v1/notifications/devices/register`                                  |
| Driver alias                         | `POST /driver-api/v1/push/register` → `DeviceService`                      |
| `EventRouter` for 30+ domain events  | `notification_engine/event_router.py`                                      |
| Retry scheduling                     | `NotificationEngine.schedule_retry()`                                      |
| Admin API + UI scaffold              | `/v1/admin/notifications/*`                                                |
| In-app inbox + WebSocket bell        | `GET /v1/notifications/inbox`, `WS /v1/notifications/ws`                   |
| Template catalog (40+ keys)          | `notification_engine/templates.py`                                         |
| Worker channel processors            | `emails`, `sms` (log-only), `push` queues                                  |

---

## Remaining Gaps (July 2026)

| Area                                    | Status                                          |
| --------------------------------------- | ----------------------------------------------- |
| Production Firebase credentials         | Required for real push in staging/prod          |
| SMS                                     | Log-only — no Twilio                            |
| `revoke-all` devices HTTP route         | Service method exists; route not exposed        |
| Dedicated retry worker drain            | Record-based retry fields; no background poller |
| Merchant/customer web push clients      | Endpoints ready; client wiring partial          |
| `quote.created`, `support.ticket_reply` | Templates exist; EventRouter not subscribed     |

---

## Historical — Pre-Implementation Gaps (June 2026)

<details>
<summary>Partially implemented before enterprise engine</summary>

- FCM `_send_push()` log-only
- Tokens in `driver.performance` JSON
- ~4 event handlers wired
- No in-app model or WebSocket
- No preference opt-out

</details>

<details>
<summary>Architecture violations fixed</summary>

- Admin push action bypassing engine → wired through `NotificationEngine`
- Recipient dict shape in legacy handler → normalized in `EventRouter`
- Direct queue enqueue bypassing engine → deprecated paths delegate to engine

</details>

---

## Verification Checklist

- [ ] `pnpm db:migrate` (includes `e6f7a8b9c0d1_enterprise_notifications`)
- [ ] Set `FIREBASE_PROJECT_ID` + credentials in API + worker
- [ ] Register device from client (`/v1/notifications/devices/register` or driver push alias)
- [ ] Trigger `booking.confirmed` → email + in-app (+ push when FCM configured)
- [ ] Trigger `order.driver_assigned` → driver push
- [ ] Admin `/admin/notifications` shows queue + history
- [ ] WebSocket bell updates on new in-app notification
- [ ] Invalid FCM token deactivated in `notification_devices`
- [ ] Run `pnpm validate:e2e:reports` → [NOTIFICATION_REPORT.md](../../NOTIFICATION_REPORT.md)

---

## Governance

| Document                                                              | Role              |
| --------------------------------------------------------------------- | ----------------- |
| [masterrule.md](../../masterrule.md)                                  | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../archive/reports-2026-08/CTO_AUDIT_REPORT.md) | Doc vs code audit |
