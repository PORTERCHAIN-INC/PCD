# Merchant Portal — Architecture Audit

**Original audit:** 2026-06-30  
**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Scope:** `apps/merchant-portal/`, `merchant_engine/`, `/v1/merchant/*`, `/v1/merchant-api/*`

> **Gap tracker:** [MERCHANT_GAP_ANALYSIS.md](./MERCHANT_GAP_ANALYSIS.md) · **Readiness:** [MERCHANT_PRODUCTION_READINESS.md](./MERCHANT_PRODUCTION_READINESS.md)

**Status key:** ✅ Implemented · ⚠ Partial · ❌ Missing · 🚫 Violation

---

## 1. Locked topology compliance

```
Merchant Portal (:3001)
    ↓ HTTPS /v1/*
FastAPI Router → merchant_engine → PostgreSQL 16
    ↓ (async)
Event Bus → fleetbase_engine → fleetbase-adapter → Fleetbase (:8000)
```

| Check                             | Status | Evidence                                      |
| --------------------------------- | ------ | --------------------------------------------- |
| Portal calls Porterchain API only | ✅     | `NEXT_PUBLIC_PORTERCHAIN_API_URL` → `:8001`   |
| No direct Fleetbase HTTP          | ✅     | No `:8000` / Fleetbase SDK in merchant-portal |
| Routers delegate to services      | ✅     | `routers/merchant.py` thin controllers        |
| Fleetbase via adapter             | ✅     | `transition_to_dispatch_ready` → event → sync |

**Verdict:** ✅ **Compliant**

---

## 2. Implemented (July 2026)

### Frontend highlights

| Feature                   | Route        | API                                    |
| ------------------------- | ------------ | -------------------------------------- |
| Dashboard + notifications | `/dashboard` | `GET /dashboard`, inbox mark-read      |
| Book + maps autocomplete  | `/book`      | `POST /bookings`                       |
| Bulk CSV                  | `/bulk`      | `/bulk/upload`, `/bulk/{id}/confirm`   |
| Orders + Order 360        | `/orders`    | CRUD + cancel/duplicate                |
| Tracking + map embed      | `/track`     | `/track/{number}`, live tracking       |
| Billing                   | `/billing`   | statement, invoices                    |
| Reports                   | `/reports`   | summary, overview                      |
| Integrations              | `/api`       | API keys, webhooks, usage, rate limits |
| Team                      | `/team`      | invite, remove, roles (backend)        |
| Settings                  | `/settings`  | profile, recipients, addresses         |

### Backend services

`MerchantBookingService`, `MerchantBulkService`, `MerchantOrdersService`, `MerchantDashboardService`, `MerchantBillingService`, `MerchantReportsService`, `MerchantProfileService`, `MerchantTeamService`, `MerchantApiKeyService`, `IntegrationsService`, `WebhookDeliveryService`, RBAC, gateway middleware.

### Programmatic API (`/v1/merchant-api/*`) — ✅ Added

| Route                             | Auth                            |
| --------------------------------- | ------------------------------- |
| `POST /bookings`                  | `X-Api-Key` + `shipments:write` |
| `GET /orders`, `GET /orders/{id}` | `shipments:read`                |
| `GET /track/{tracking_number}`    | `shipments:read`                |
| `POST /orders/{id}/cancel`        | `shipments:write`               |

---

## 3. Partially implemented

| Area                       | Exists                       | Gap                                         |
| -------------------------- | ---------------------------- | ------------------------------------------- |
| NET batch billing          | Statement + invoice list     | No scheduled NET_7/NET_14 run               |
| Reports scheduled delivery | Profile metadata             | No worker                                   |
| Team                       | DB invites                   | No Clerk Organizations API sync             |
| Bulk upload                | UI accepts `.xlsx`           | Parser is CSV-only                          |
| Booking templates          | DB model                     | No service/UI                               |
| Cancel → Fleetbase         | Direct `sync_cancellation()` | Should use `order.cancelled` event (G-M010) |
| Live merchant map          | Poll-based tracking          | No merchant WebSocket (admin live-map only) |
| API key scopes UI          | Defaults on create           | Scope checkboxes missing                    |

---

## 4. Missing (follow-on)

| Item                                     | Priority |
| ---------------------------------------- | -------- |
| ERP OAuth connectors                     | P3       |
| Server-side order manifest export        | P3       |
| Dedicated merchant-portal Docker service | P3       |
| `apps/merchant/` path migration          | P3       |

---

## 5. Architecture violations

| ID    | Issue                                 | Status (July 2026)                       |
| ----- | ------------------------------------- | ---------------------------------------- |
| AV-01 | Direct cancel sync bypasses event bus | ⚠ **Open**                               |
| AV-02 | Duplicate order lookup in router      | ⚠ Low — acceptable                       |
| AV-03 | Webhook secret storage                | ✅ **Fixed** — encrypted secret          |
| AV-04 | Webhook worker stub                   | ✅ **Fixed** — `deliver_merchant_fanout` |

**No violations:** UI → Fleetbase, business logic in React, pricing in UI, Fleetbase HTTP outside adapter.

---

## 6. Security posture

| Control                             | Status |
| ----------------------------------- | ------ |
| Clerk JWT on portal                 | ✅     |
| `X-Merchant-Org-Id` scoping         | ✅     |
| RBAC module checks                  | ✅     |
| API key SHA-256 + scopes            | ✅     |
| API key router                      | ✅     |
| Webhook HMAC delivery               | ✅     |
| Gateway rate limits on merchant-api | ✅     |
| Dev bypass gated (`local` + flag)   | ✅     |

---

## 7. Compliance score

| Dimension            | June 2026 | July 2026 (est.) |
| -------------------- | --------- | ---------------- |
| Locked topology      | 95/100    | 95/100           |
| Layered architecture | 92/100    | 92/100           |
| Fleetbase boundary   | 98/100    | 98/100           |
| Feature completeness | 78/100    | 85/100           |
| API design           | 85/100    | 92/100           |
| Security             | 80/100    | 88/100           |

**Overall merchant surface: ~90/100** — foundation gaps from June audit resolved; operational polish remains.

---

## 8. Related documents

| Document                                                                   | Purpose                |
| -------------------------------------------------------------------------- | ---------------------- |
| [MERCHANT_GAP_ANALYSIS.md](./MERCHANT_GAP_ANALYSIS.md)                     | Prioritized gaps       |
| [docs/architecture/MERCHANT_FLOW.md](./docs/architecture/MERCHANT_FLOW.md) | Flow diagram           |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)         | Platform certification |

---

_Audit per masterrule §19 — preserve locked topology; search existing code before new modules._
