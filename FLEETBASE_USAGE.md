# Fleetbase Usage

**Reference:** [masterrule.md](./masterrule.md) §8, §13  
**Date:** June 30, 2026

---

## Fleetbase OWNS (execution only)

| Domain | Status | Integration path |
|--------|--------|------------------|
| Drivers | ✅ | `FleetbaseAdapter.sync_driver` |
| Vehicles | ✅ | `sync_vehicle` |
| Dispatch | ✅ | `sync_dispatch`, webhooks |
| GPS / tracking | ✅ | Webhooks + `fetch_tracking` |
| Current route | ✅ | `fetch_route` |
| Driver status | ✅ | Webhooks + driver bridge |
| Vehicle status | ✅ | Mirror via webhooks |
| Proof of delivery | ✅ | `sync_proofs`, driver uploads |
| Navigation | ✅ | Fleetbase mobile / external handoff |
| Dispatch queue | ✅ | Fleetbase console + SSO |
| Route execution | ✅ | In-flight order states |

---

## Fleetbase does NOT own

| Domain | Porterchain owner | Fleetbase touches? |
|--------|-------------------|-------------------|
| CRM | `admin_engine/crm_*` | ❌ |
| Merchants | `merchant_engine` | ❌ (meta ID only) |
| Pricing | `pricing_engine` | ❌ |
| Invoices | `models.Invoice` | ❌ |
| Payments / Stripe | `PaymentService` | ❌ |
| Finance | `AdminFinanceService` | ❌ |
| Claims | `AdminClaimsService` | ⚠️ Webhook can open claim record |
| Support | `AdminSupportService` | ❌ |
| Analytics | Reports services | ❌ |
| Documents | JSON attachments + POD mirror | ⚠️ POD proofs only |

---

## Integration boundary

```
All apps → FastAPI (:8001) → fleetbase_engine → porterchain_fleetbase_adapter → Fleetbase (:8000)
```

| Bypass check | Result |
|--------------|--------|
| UI → Fleetbase HTTP | ❌ None |
| Router → Fleetbase HTTP | ❌ None |
| Admin live map → Fleetbase | ❌ DB mirror only |

---

## Webhooks

| Endpoint | Handler |
|----------|---------|
| `POST /webhooks/fleetbase` | `WebhookIngressService` → `WebhookProcessor` |

Emits: `webhook.received`, `fleetbase.status_updated`, `fleetbase.pod_received`, order lifecycle events.

---

## Outbound sync

| Trigger | Action |
|---------|--------|
| `order.dispatch_ready` | `push_order` |
| `order.driver_assigned` | `push_driver_assignment` |
| Merchant cancel | `cancel_order` via adapter |
| Admin approve driver | `push_driver` + `push_vehicle` |

---

## Status

✅ Architecture compliant with masterrule  
⚠️ `sync_claim` audit-only (acceptable)  
⚠️ Orchestrator routes exist in adapter but not wired from admin UI
