# Porterchain — Missing Integrations

**Reference:** [masterrule.md](masterrule.md)  
**Last updated:** June 30, 2026 (End-to-end architecture audit)  
**Companion:** [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md), [GAP_ANALYSIS.md](GAP_ANALYSIS.md)

---

## Resolved in this audit ✅

| ID      | Integration                         | Implementation                                                                              |
| ------- | ----------------------------------- | ------------------------------------------------------------------------------------------- |
| E2E-001 | `order_source` on every order       | `Order` model + migration + confirmation/merchant/bulk services                             |
| E2E-002 | `order_type` classification         | `order_metadata.py` + set at order creation                                                 |
| E2E-003 | NET_7 / NET_14 payment terms        | `PaymentTerms` + `MerchantPaymentTerms` enums                                               |
| E2E-004 | Merchant `billing_cycle` field      | `Merchant.billing_cycle` (WEEKLY/BIWEEKLY/MONTHLY)                                          |
| E2E-005 | Unified ops queue (no source split) | Verified — `dispatch_queue()` state-only filter                                             |
| E2E-006 | Event catalog completeness          | `payment.started`, `CustomerAuthenticated`, `PickedUp`, `Delivered`, `PODCompleted` aliases |
| E2E-007 | Valhalla/OSRM authoritative pricing | `services/routing.py` (prior session)                                                       |
| E2E-008 | Merchant Google Maps                | `@porterchain/maps` (prior session)                                                         |
| E2E-009 | Fleetbase cancel via adapter        | `cancel_order` (prior session)                                                              |
| E2E-010 | Claim/support notification handlers | Event bus (prior session)                                                                   |

---

## Still open — documented roadmap

### ❌ Missing (not implemented — avoid scope creep)

| ID    | Item                                          | Why deferred                                 |
| ----- | --------------------------------------------- | -------------------------------------------- |
| M-001 | Merchant API-key booking endpoints            | Requires new auth middleware + public router |
| M-002 | Merchant invoice run / batch billing job      | masterrule §11.2 future scope                |
| M-003 | Invoice PDF generation (`pdf_url`)            | Document engine not built                    |
| M-004 | Dedicated pre-Clerk email/phone collection UI | Clerk+Stripe design is intentional           |
| M-005 | Auto driver assignment for retail             | Ops policy — manual dispatch today           |
| M-006 | Customer portal tracking map                  | UI gap                                       |
| M-007 | Driver portal map visualization               | UI gap                                       |
| M-008 | WebSockets beyond live map                    | Poll acceptable for v1                       |
| M-009 | `route.optimized` event emission              | Fleetbase orchestrator not wired from admin  |
| M-010 | Recurring booking templates cron              | Model exists; no scheduler                   |
| M-011 | ADMIN / PHONE / PARTNER order sources         | No admin-create-order flow yet               |
| M-012 | Firebase webhook ingress                      | Push outbound only (correct)                 |

### ⚠ Partial

| ID    | Item                             | Notes                             |
| ----- | -------------------------------- | --------------------------------- |
| P-001 | Email/phone before auth          | Clerk profile + Stripe collection |
| P-002 | Merchant billing statement       | Summary API only; no PDF          |
| P-003 | Merchant webhook fanout delivery | Worker stub                       |
| P-004 | Nearest driver (OSRM matrix)     | Haversine in live map             |
| P-005 | Customer app                     | Thin; website portal fuller       |

---

## Module classification summary

| Module                       | Status                                 |
| ---------------------------- | -------------------------------------- |
| Website / Booking            | ✅ Fully Integrated (⚠ email/phone UX) |
| Customer Portal              | ⚠ Partially Integrated                 |
| Merchant Portal              | ✅ Fully Integrated (⚠ API booking)    |
| Admin Portal                 | ✅ Fully Integrated                    |
| Logistics Orchestrator (API) | ✅ Fully Integrated                    |
| Fleetbase Adapter            | ✅ Fully Integrated                    |
| Fleetbase Core               | ✅ Fully Integrated                    |
| Driver Platform              | ⚠ Partially Integrated                 |
| Event Bus                    | ✅ Fully Integrated                    |
| Billing Engine               | ⚠ Partially Integrated                 |
| Pricing Engine               | ✅ Fully Integrated                    |
| Notification Engine          | ⚠ Partially Integrated                 |
| Live Map                     | ✅ Fully Integrated                    |
| Reports                      | ✅ Fully Integrated (read-only)        |

---

## Verification commands

```bash
curl http://localhost:8001/health
pnpm docker:fleetbase:verify
cd apps/api && alembic upgrade head   # order_source migration
```

---

## Rules for next integrations

1. Extend existing `*_engine` services — no parallel APIs
2. All Fleetbase traffic through adapter
3. All business logic in Application Services
4. Update this file when closing gaps
