# Fleetbase Usage

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) §8, §13

> **Integration overview:** [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)

---

## Fleetbase OWNS (execution only)

| Domain            | Status | Integration path                            |
| ----------------- | ------ | ------------------------------------------- |
| Drivers           | ✅     | Adapter `sync_driver` + admin approval flow |
| Vehicles          | ✅     | `sync_vehicle`                              |
| Dispatch          | ✅     | `sync_dispatch`, webhooks                   |
| GPS / tracking    | ✅     | Webhooks + `fetch_tracking`                 |
| Current route     | ✅     | Adapter route/tracker APIs                  |
| Driver status     | ✅     | Webhooks + `driver_engine` bridge           |
| Proof of delivery | ✅     | POD capture + webhook sync                  |
| Dispatch queue    | ✅     | Fleetbase console (:4200) via SSO           |
| Route execution   | ✅     | In-flight order states via webhooks         |

---

## Fleetbase does NOT own

| Domain               | Porterchain owner                  | Fleetbase touches?                |
| -------------------- | ---------------------------------- | --------------------------------- |
| CRM                  | `admin_engine/crm_*`               | ❌                                |
| Merchants            | `merchant_engine`                  | ❌ (meta ID only on sync)         |
| Pricing              | `pricing_engine`                   | ❌                                |
| Invoices / Stripe    | `billing_engine`, `PaymentService` | ❌                                |
| Finance              | `AdminFinanceService`              | ❌                                |
| Claims               | `AdminClaimsService`               | ⚠️ Webhook may trigger claim sync |
| Support              | `AdminSupportService`              | ❌                                |
| Analytics            | Admin reports                      | ❌                                |
| Customer tracking UX | Website, `apps/customer/`          | Reads Fleetbase via adapter only  |

---

## Integration boundary

```
All apps → Porterchain API (:8001) → fleetbase_engine → fleetbase-adapter → Fleetbase (:8000)
```

| Bypass check               | Result                                             |
| -------------------------- | -------------------------------------------------- |
| UI → Fleetbase HTTP        | ❌ None                                            |
| Router → Fleetbase HTTP    | ❌ None                                            |
| Admin live map → Fleetbase | ❌ DB mirror only (WebSocket reads Porterchain DB) |

**Driver mobile** (`apps/mobile-driver/`) uses Porterchain API + Clerk — not Fleetbase Navigator auth.

---

## Webhooks (inbound)

| Endpoint                   | Handler                                      |
| -------------------------- | -------------------------------------------- |
| `POST /webhooks/fleetbase` | `WebhookIngressService` → `WebhookProcessor` |

Emits: `webhook.received`, order lifecycle domain events, `fleetbase.status_updated` where applicable.

---

## Outbound sync (event-driven)

| Trigger                                | Action                          |
| -------------------------------------- | ------------------------------- |
| `order.dispatch_ready`                 | `BookingSyncService.push_order` |
| `order.driver_assigned`                | `push_driver_assignment`        |
| Order cancel / return / damage / claim | Respective sync handlers        |
| Admin approve driver                   | `push_driver` + `push_vehicle`  |

Handlers: `booking_engine/fleetbase_sync_handler.py` — never direct calls from booking services.

---

## Open items

| Item                                                | Status                                               |
| --------------------------------------------------- | ---------------------------------------------------- |
| SSO console extension (`/int/v1/porterchain/sso/*`) | Client in adapter; Fleetbase extension deploy needed |
| Admin route orchestrator UI                         | Adapter routes exist; not wired from admin UI        |
| `route.optimized` event                             | Catalog only — not emitted from admin                |

---

## Related documents

| Document                                               | Purpose                |
| ------------------------------------------------------ | ---------------------- |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) | Full integration guide |
| [FLEETBASE_WEBHOOKS.md](./FLEETBASE_WEBHOOKS.md)       | Webhook setup          |
| [FLEETBASE_MODULES.md](./FLEETBASE_MODULES.md)         | Per-module decisions   |
