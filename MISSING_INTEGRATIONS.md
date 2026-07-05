# Porterchain — Missing Integrations


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Reference:** [masterrule.md](./masterrule.md)  
**Companion:** [GAP_ANALYSIS.md](./GAP_ANALYSIS.md), [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)

Living gap tracker — update when closing items. Canonical integration status: [INTEGRATIONS.md](./INTEGRATIONS.md).

---

## Resolved ✅

| ID | Item | Status |
| -- | ---- | ------ |
| E2E-001 | `order_source` on every order | ✅ Model + migration |
| E2E-002 | `order_type` classification | ✅ `order_metadata.py` |
| E2E-003 | NET payment terms | ✅ Enums + merchant profile |
| E2E-004 | Merchant `billing_cycle` | ✅ Field on `Merchant` |
| E2E-005 | Unified ops dispatch queue | ✅ State-only filter |
| E2E-006 | Event catalog aliases | ✅ Shared catalog |
| E2E-007 | Valhalla/OSRM authoritative pricing | ✅ Server-side routing |
| E2E-008 | Merchant Google Maps | ✅ `@porterchain/maps` |
| E2E-009 | Fleetbase cancel via adapter | ✅ `cancel_order` |
| E2E-010 | Claim/support notification handlers | ✅ Event bus |
| M-001 | Merchant API-key booking | ✅ **`POST /v1/merchant-api/bookings`** (⚠️ `order_source` defaults to `MERCHANT` — tag `API` TODO) |
| P-003 | Merchant webhook fanout delivery | ✅ **`WebhookDeliveryService`** + delivery history |
| P-005 | Customer app | ✅ **`apps/customer/` :3004** + **`apps/mobile-customer/`** |
| — | Driver mobile app | ✅ **`apps/mobile-driver/`** (72% readiness) |
| — | Clerk-only auth | ✅ Supabase/Twilio OTP removed |

---

## Still open

### ❌ Not implemented

| ID | Item | Notes |
| -- | ---- | ----- |
| M-002 | Merchant invoice batch / billing cycle job | NET terms cycle → statement batch |
| M-003 | Invoice PDF generation (`pdf_url`) | Document engine not built |
| M-005 | Auto driver assignment for retail | Ops policy — manual dispatch today |
| M-006 | Customer portal tracking map | UI gap |
| M-007 | Driver portal map visualization | UI gap |
| M-009 | `route.optimized` event emission | Fleetbase orchestrator not wired from admin |
| M-010 | Recurring booking templates cron | Model exists; no scheduler |
| M-011 | ADMIN / PHONE / PARTNER order sources | No admin-create-order flow |
| M-012 | Firebase production push creds | Token register works; API send needs creds |

### ⚠ Partial

| ID | Item | Notes |
| -- | ---- | ----- |
| P-001 | Pre-auth contact capture UX | Clerk profile + Stripe at checkout |
| P-002 | Merchant billing statement PDF | Summary API only |
| P-004 | Nearest driver (OSRM matrix) | Haversine in live map |
| P-006 | Merchant API `order_source=API` | Endpoint live; source tag not passed |
| P-007 | SMS notifications | Log-only channel |
| P-008 | Production readiness | See `PRODUCTION_READINESS_REPORT.md` |

---

## Module classification (July 2026)

| Module | Status |
| ------ | ------ |
| Website / Booking | ✅ Integrated |
| Customer portal + mobile | ⚠️ Active — gaps in map/PDF |
| Merchant portal | ✅ Integrated |
| Merchant API + webhooks | ✅ Implemented |
| Admin portal | ✅ Integrated |
| Porterchain API | ✅ Integrated |
| Fleetbase adapter + core | ✅ Integrated |
| Driver platform (web + mobile) | ⚠️ 72% mobile / web partial maps |
| Event bus + worker | ✅ Integrated |
| Billing / Notification | ⚠️ Embedded modules |
| Live map | ✅ Integrated |

---

## Rules for next integrations

1. Extend existing `*_engine` services — no parallel APIs
2. All Fleetbase traffic through adapter
3. All business logic in Application Services
4. Update this file when closing gaps

---

## Verification

```bash
curl http://localhost:8001/health/ready
pnpm docker:fleetbase:verify
cd apps/api && alembic upgrade head
```
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
