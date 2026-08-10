# Orders module — Control Tower & Order 360

**SSOT for ops ownership:** Fleetbase-first (execution) · PorterChain Admin (create, assign, exceptions, money)  
**Surfaces:** Operations board / queue / table · Order 360 drawer · Full Order 360 `/orders/[id]`  
**Last updated:** 2026-08-07 · **P0–P2 implementation complete** · §5 scorecard template ready

---

## 1. What we built (orders side of Control Tower)

| Area                             | Status     | What exists                                                                                                                                                                                                                                         |
| -------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Order 360 drawer**             | Done (P0)  | Opens from board / table / queue / exceptions / SLA; assign + mark exception; tabs Details / Timeline / POD / Money / Care                                                                                                                          |
| **Full Order 360 page**          | Done (P1)  | `/orders/[id]` — invoice/resend/labels/manifest wired; POD gallery + PC↔FB diff + comms logs                                                                                                                                                        |
| **Active Orders table**          | Done (P2)  | Filters, saved views, density; row → Order 360                                                                                                                                                                                                      |
| **New order builder**            | Done (P1)  | `single` / `hub_spoke` / `multi_pickup_delivery` / `scheduled_pickup`; syncs with `type: transport`                                                                                                                                                 |
| **Stop topology (MS-A only)**    | **Active** | Truth sync: Order 360 stop SoT · retail confirm · merchant copy honesty · Admin pick/drop fees. **Not** shipping portal 1:N UI / N:1 / per-stop notify yet — see [ADMIN_PARTNERS_UPGRADE_PLAN.md](./ADMIN_PARTNERS_UPGRADE_PLAN.md) § Stop topology |
| **Dispatch queue drag**          | Done (P0)  | Drag order → **driver** (assign), ranked suggestions — not column→column                                                                                                                                                                            |
| **Board drag column→column**     | Partial    | DnD UI works; API **only allows exception columns**                                                                                                                                                                                                 |
| **Mandatory-op popup on drop**   | Done (P0)  | Assigned → AssignDriverModal; Failed/Returned/Lost/Damaged → ExceptionReasonModal (reason required)                                                                                                                                                 |
| **Auto-invoice after POD**       | Done       | `InvoiceService.finalize_after_pod` on `order.pod_completed` → `INVOICED` + email                                                                                                                                                                   |
| **Stripe payment receipt email** | Done       | Enriched `payment.succeeded` / `order.invoiced` payloads; branded HTML mail                                                                                                                                                                         |
| **LOST board column**            | Fixed      | `ORDER_TRANSITIONS`: `FAILED→LOST`, `DELIVERED→LOST`                                                                                                                                                                                                |
| **Fleetbase assign/dispatch**    | Fixed      | Adapter `PUT {driver}` then `PATCH /dispatch`; multi-stop complete fallback                                                                                                                                                                         |

Master-plan guardrail (still in force):

> Execution moves stay in Fleetbase — the board marks exceptions only.

---

## 2. Ownership lock (Admin vs Fleetbase)

| PorterChain Admin / portals                      | Fleetbase + driver app                          |
| ------------------------------------------------ | ----------------------------------------------- |
| Create / import orders (all stop shapes)         | Receive synced orders + driver/vehicle registry |
| Assign / reassign / copilot / optimize           | Accept → en route → pickup → deliver            |
| Exceptions: failed, return, lost, damaged, retry | POD photo / signature / barcode                 |
| Invoice, receipt, Stripe, CRM, support           | Live GPS, route execution                       |
| Read-only map + Order 360 (adapter-fed)          | Open via Admin SSO (`Open Fleetbase`)           |

**Board drag rule:** Admin does not fake Accept→Delivered. Assign in Admin; advance execution in driver / Fleetbase; exceptions stay on the PC board.

---

## 3. Board drag behavior (current)

1. Drag ends on a **confirm column** → modal (no optimistic jump).
2. **Assigned** → `AssignDriverModal` (ranked drivers) → assign API.
3. **Failed / Returned / Lost / Damaged** → `ExceptionReasonModal` (reason ≥ 3 chars) → `POST /board/move` with `reason`.
4. **Accept → Delivered** (and other execution columns) → message: advance in Fleetbase / driver (API still blocks fake execution moves).

### A. Execution columns — Fleetbase-owned (blocked on board)

| Drop on column       | Target state                  | Mandatory ops                     | Where it lives                     |
| -------------------- | ----------------------------- | --------------------------------- | ---------------------------------- |
| Waiting dispatch     | `DISPATCH_READY`              | Booked + ready; retry from FAILED | PC; Exceptions retry               |
| Assigned             | `DRIVER_ASSIGNED`             | Select driver + assign            | **Modal** + queue drag / Order 360 |
| Accepted → Delivered | …                             | Driver / Fleetbase lifecycle      | Driver portal or Fleetbase console |
| Delivered (+ POD)    | `DELIVERED` / `POD_COMPLETED` | Deliver + POD                     | Driver → webhooks                  |

### B. Exception columns — PC board (popup done)

| Drop on column | Target state       | Popup            | Implemented?                       |
| -------------- | ------------------ | ---------------- | ---------------------------------- |
| Failed         | `FAILED`           | Reason + confirm | **Yes** — board + Order 360        |
| Returned       | `RETURN_TO_SENDER` | Reason + confirm | **Yes**                            |
| Damaged        | `DAMAGED`          | Reason + confirm | **Yes**                            |
| Lost           | `LOST`             | Reason + confirm | **Yes** (+ transition graph fixed) |

---

## 4. Money & notifications (2026-08 changes)

| Trigger                             | Behavior                                                                    |
| ----------------------------------- | --------------------------------------------------------------------------- |
| Stripe `checkout.session.completed` | Invoice + receipt row at confirmation; `payment.succeeded` email (customer) |
| `order.pod_completed`               | Auto-invoice if missing → transition `INVOICED` → merchant/customer email   |
| Email templates                     | Branded HTML shell; tagline **Moving commerce on chain**; Mailpit on local  |

**Code:** `booking_engine/invoice_service.py`, `payment_service.py`, `confirmation_service.py`, `notification_engine/email_layout.py`, `templates.py`, event-bus `_handle_pod_completed_invoice`.

**Order 360 Money tab (drawer):** shows invoice #, amount, Receipt + Invoice PDF links when present.

---

## 5. Order 360 — audit each function

Use this checklist on a live order (prefer one `INVOICED` with `order_*` Fleetbase id and one mid-flight). Mark **Pass / Fail / Partial** and note evidence (screenshot or API response).

### 5.1 Entry points

| #   | Function                      | How to test                               | Pass if                            | Likely status                             |
| --- | ----------------------------- | ----------------------------------------- | ---------------------------------- | ----------------------------------------- |
| E1  | Open drawer from board card   | Click card on Operations                  | Drawer loads detail                | Working                                   |
| E2  | Open drawer from queue row    | Click queue row                           | Same                               | Working                                   |
| E3  | Open drawer from orders table | Click row                                 | Same                               | Working                                   |
| E4  | Open full page                | Drawer “Open full page” or `/orders/{id}` | Full nav + tabs                    | Working                                   |
| E5  | Poll / refresh                | Leave open 10–20s                         | Soft refresh without flicker crash | Partial (poll present; verify stale data) |

### 5.2 Drawer tabs (`Order360Drawer`)

| #   | Tab / control          | Pass if                                       | Likely status | Notes                                    |
| --- | ---------------------- | --------------------------------------------- | ------------- | ---------------------------------------- |
| D1  | Details                | Merchant, customer, driver, stops meta, FB id | Working       | Read-only                                |
| D2  | Timeline               | Ordered events with states                    | Working       | Domain/order events                      |
| D3  | POD                    | Fleetbase proof gallery or empty CTA          | Working       | Photos/signatures/OTP when FB has proofs |
| D4  | Money                  | Invoice #, amount, real receipt/PDF only      | Working       | Fake hosts filtered                      |
| D5  | Care                   | Claims / tickets / incidents lists            | Partial       | Empty unless care data exists            |
| D6  | Assign driver          | `AssignDriverModal` → `DRIVER_ASSIGNED` + FB  | Working       | Ranked suggestions                       |
| D7  | Mark exception         | failed/returned/lost/damaged + reason         | Working       | Reason required (API)                    |
| D8  | Copy tracking          | Clipboard                                     | Working       |                                          |
| D9  | Route map              | Map renders for order                         | Partial       | Coords / maps key dependent              |
| D10 | Open Fleetbase         | Next-action CTA + ops toolbar SSO             | Working       | Drawer primary action when in-flight     |
| D11 | Next-best-action strip | State-aware primary CTA                       | Working       | Assign / Fleetbase / Money / Exception   |
| D12 | PC↔FB status chip      | `status_sync` aligned/drift                   | Working       | Situation strip                          |

### 5.3 Full page tabs (`OrderDetailView`)

| #   | Tab                                    | Pass if                            | Likely status                             |
| --- | -------------------------------------- | ---------------------------------- | ----------------------------------------- |
| F1  | Overview                               | Shipment + financial summary       | Working                                   |
| F2  | Timeline                               | Same as drawer                     | Working                                   |
| F3  | Tracking                               | Live / waypoints                   | Partial — webhook/GPS dependent           |
| F4  | Packages                               | Package list                       | Partial — data shape dependent            |
| F5  | Pickup / Stops / Delivery              | Addresses render                   | Working if order has structured addresses |
| F6  | Merchant / Customer / Driver / Vehicle | 360 cards                          | Partial — linked entities                 |
| F7  | Pricing                                | Quote breakdown                    | Partial                                   |
| F8  | Payments                               | Payment rows + receipt links       | Working when payments exist               |
| F9  | Invoices                               | Invoice #, amount, receipt/PDF     | Working when invoice exists               |
| F10 | Documents                              | invoice_pdf / receipt docs         | Working when URLs set                     |
| F11 | POD                                    | Proof payload                      | Partial                                   |
| F12 | Claims / Support                       | Lists or empty                     | Partial                                   |
| F13 | Communications                         | NotificationRecord + delivery logs | Working when notifies exist               |
| F14 | Automation                             | Rules / hooks                      | Likely thin / empty                       |
| F15 | API Activity                           | Gateway logs                       | Partial                                   |
| F16 | Audit Log                              | Admin + domain audit               | Partial                                   |

### 5.4 Full page quick actions

| #   | Action                   | Implementation today                            | Audit result to record               |
| --- | ------------------------ | ----------------------------------------------- | ------------------------------------ |
| A1  | Assign / Reassign driver | Shared `AssignDriverModal` (ranked suggestions) | Working                              |
| A2  | Cancel order             | Bulk cancel API                                 | Verify state → CANCELLED             |
| A3  | Duplicate order          | Alert + booking-draft redirect                  | Partial                              |
| A4  | Rebook                   | Redirect to booking                             | Partial                              |
| A5  | Create return            | Redirect to claims                              | Partial (not true reverse logistics) |
| A6  | Generate invoice         | `POST .../invoice` + auto on POD                | Working                              |
| A6b | Resend receipt           | `POST .../resend-receipt` → HTML mail           | Working                              |
| A7  | Refund                   | Alert → Finance                                 | Not in-360                           |
| A8  | Open claim / support     | Query-param navigate                            | Partial                              |
| A9  | Share tracking           | Copy `/track/{tn}`                              | Working                              |
| A10 | Print labels / manifest  | `GET .../label.pdf` · `manifest.pdf`            | Working (PC PDF docs)                |

### 5.5 Audit protocol (run every release)

1. **Seed:** 1 assigned in-flight order, 1 `POD_COMPLETED`/`INVOICED`, 1 exception (FAILED).
2. **IDs:** Confirm `fleetbase_order_id` is `order_*` (never `fb-123`).
3. **Walk §5.1–5.4** and fill a scorecard: Pass / Fail / Partial + 1-line note.
4. **Money path:** After POD, wait for auto-invoice; check Money tab + Mailpit HTML receipt.
5. **Sync path:** Assign in 360 → Fleetbase console shows same driver + dispatched.
6. **File scorecard** under `docs/` or release notes (date, env, auditor).

---

## 6. Gaps still needed (board + 360)

**Done (P0):** drop confirm modals · mandatory reason · ranked assign on full page · next-best-action strip.

**Done (P1 / evidence):**

1. `POST /orders/{id}/invoice` + `POST /orders/{id}/resend-receipt` wired to Order 360 actions.
2. `GET /orders/{id}/label.pdf` + `manifest.pdf` (stdlib PDF; replaces `window.print`).
3. POD gallery from Fleetbase proofs (`normalize_pod`) on drawer + full page.
4. Communications tab from `NotificationRecord` + delivery logs.
5. `status_sync` PC↔FB chip (aligned / drift / truth label).
6. Placeholder `example.local` receipt/PDF URLs nulled + filtered by `public_document_url`.
7. Scoped **Assist** tab (propose → Confirm) + playbooks (retry / notify / escalate / invoice / resend).
8. **Invoice PDF** via `GET /orders/{id}/invoice.pdf` when Stripe PDF absent.

**Still open:**

1. Formal **§5 audit scorecard** filled on a release (manual QA) — template: `infrastructure/ORDER_360_AUDIT_SCORECARD.md`.

---

## 7. Modern · agentic-ready · professional Order 360

Goal: Order 360 becomes the **ops cockpit** — situation awareness + one-click actions + agent-assist — without rebuilding Fleetbase execution.

### 7.1 Product principles

1. **One situation strip** — state, SLA, driver, ETA, money, risk score (always visible).
2. **One primary next action** — not 14 equal buttons (Assign / Mark failed / Open Fleetbase / Contact).
3. **Truth labels** — “Live from Fleetbase”, “PC commercial”, “Estimated” (never mix silently).
4. **Agent proposes · human confirms** — for assign, exception, refund, rebook.
5. **Evidence over forms** — timeline + map + POD + money in one scroll before tabs.

### 7.2 Intelligence layer (what to add)

| Capability              | Approach                                                                                                              | Why                                 |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| **Next-best-action**    | Ranked actions from state + SLA + exceptions + driver availability                                                    | Cuts cognitive load                 |
| **Assign copilot**      | Existing dispatch suggestions (Valhalla matrix + filters) in 360 footer                                               | Already on queue — promote into 360 |
| **Exception coach**     | LLM/rules: suggest Failed vs Return vs Lost from notes + stop history                                                 | Fewer wrong board drops             |
| **ETA / risk**          | Adapter tracking + SLA hours → “at risk / breach” chip                                                                | Ops prioritization                  |
| **Money health**        | Paid / invoiced / overdue / receipt missing                                                                           | Finance without leaving 360         |
| **Agent chat (scoped)** | “Why is this late?”, “Who should take this?”, “Draft customer SMS” — tools: read order, suggest assign, draft message | Agentic ready; no silent writes     |
| **Playbooks**           | One-click: Retry dispatch, Notify customer, Escalate claim                                                            | Professional ops consistency        |
| **Diff view**           | PC state vs Fleetbase status side-by-side                                                                             | Debug sync drift                    |

### 7.3 Agentic contract (safe)

- Agent may **read** `get_detail_360`, tracking, suggestions, invoice.
- Agent may **propose** assign / exception / message (show preview).
- Agent may **write** only after explicit Confirm (same APIs as UI).
- Never let agent advance Accept→Delivered (Fleetbase-owned).
- Log every agent suggestion + accept/reject in audit tab.

### 7.4 UX modernization (professional)

| Now                   | Target                                                                |
| --------------------- | --------------------------------------------------------------------- |
| Many equal tabs       | **Workspace:** Overview (default) · Execution · Money · Care · System |
| Prompt() assign       | Modal with ranked drivers + map                                       |
| Empty POD/comms       | Evidence panels with empty-state CTAs (“Capture in driver app”)       |
| Print = browser print | PDF labels via API                                                    |
| Flat action list      | Primary CTA + overflow “More”                                         |
| No confidence         | Show data freshness (“Updated 12s ago · Fleetbase”)                   |

### 7.5 Suggested build order (P0→P2)

| Priority | Item                                                                            | Status                                                       |
| -------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **P0**   | Shared Assign modal (drawer + full page); exception reason modal on board + 360 | **Done**                                                     |
| **P0**   | Situation strip + primary next action on drawer                                 | **Done**                                                     |
| **P1**   | Promote dispatch suggestions into 360; PC↔FB status diff                        | **Done** (suggestions in Assign modal; `status_sync` on 360) |
| **P1**   | Wire Generate invoice / Resend receipt to real APIs + HTML mail                 | **Done**                                                     |
| **P2**   | Communications from notification logs                                           | **Done**                                                     |
| **P2**   | Label/manifest PDF; POD media gallery                                           | **Done** (PC PDF docs + Fleetbase proof URLs)                |
| **P2**   | Scoped agent panel (propose-only); playbooks                                    | **Done** (`OrderAssistPanel` + playbooks API)                |
| **P2**   | Invoice PDF when no Stripe file                                                 | **Done** (`GET .../invoice.pdf`)                             |

---

## 8. How to open real execution UI (cheat sheet)

| Need                            | Go here                                                               |
| ------------------------------- | --------------------------------------------------------------------- |
| Assign only                     | Operations **Dispatch Queue** or Order 360 **Assign**                 |
| Accept → deliver → POD          | **Driver portal** or **Open Fleetbase**                               |
| Watch live                      | Order 360 map/tracking; Fleetbase console                             |
| Failed / return / lost / damage | Admin board / Order 360 exception                                     |
| Invoice / receipt               | Auto after pay (retail) or POD (merchant); Money tab; Mailpit locally |

Admin never calls Fleetbase HTTP from the browser — SSO console or API → `fleetbase-adapter` only.

---

## 9. Board popup policy (implemented)

| Drop type                            | Behavior                                  | Status                       |
| ------------------------------------ | ----------------------------------------- | ---------------------------- |
| → Assigned                           | Popup: ranked drivers → Assign            | **Done**                     |
| → Accepted…Delivered                 | Do **not** fake; message + Open Fleetbase | **Done** (blocked + message) |
| → Failed / Returned / Lost / Damaged | Popup: mandatory reason → transition      | **Done**                     |
| Skip ahead (Waiting → Delivered)     | Reject via API / transition path          | **Done** (API)               |

---

## 10. Related paths

| Piece                     | Path                                                                                         |
| ------------------------- | -------------------------------------------------------------------------------------------- |
| Order 360 drawer          | `apps/admin/src/components/orders/Order360Drawer.tsx`                                        |
| Assign / Exception modals | `AssignDriverModal.tsx` · `ExceptionReasonModal.tsx`                                         |
| Full Order 360            | `apps/admin/src/components/orders/OrderDetailView.tsx` · `app/(ops)/orders/[id]/page.tsx`    |
| Board move API            | `apps/api/.../admin_engine/control_tower/service.py`                                         |
| Auto-invoice / resend     | `apps/api/.../booking_engine/invoice_service.py` · `POST .../invoice` · `.../resend-receipt` |
| Label / manifest PDF      | `apps/api/.../reporting/order_documents.py`                                                  |
| POD normalize             | `apps/api/.../fleetbase_engine/pod_normalize.py`                                             |
| Order assist / playbooks  | `apps/api/.../admin_engine/order_assist_service.py` · `OrderAssistPanel.tsx`                 |
| HTML email shell          | `apps/api/.../notification_engine/email_layout.py`                                           |
| §5 scorecard template     | `infrastructure/ORDER_360_AUDIT_SCORECARD.md`                                                |
| E2E canvas                | Cursor canvas `clean-e2e-network-validation`                                                 |
| Charter / Fleetbase-first | `.cursor/rules/fleetbase-first-policy.mdc` · `docs/PORTERCHAIN_CHARTER.md`                   |

---

## 11. Done vs not (quick answer)

| Layer                                                         | Done?                                     |
| ------------------------------------------------------------- | ----------------------------------------- |
| **P0 board + 360 modals + next action**                       | **Yes**                                   |
| **Money auto-invoice + HTML receipt mail**                    | **Yes**                                   |
| **Fleetbase-first execution lock**                            | **Yes** (by design)                       |
| **P1** (invoice/resend APIs, FB diff, URL hygiene)            | **Yes**                                   |
| **P2 evidence** (comms logs, label/manifest PDF, POD gallery) | **Yes**                                   |
| **P2 agent panel + playbooks + invoice PDF**                  | **Yes**                                   |
| **Full §5 manual audit scorecard filed**                      | **No** (template ready — fill on release) |

**Bottom line:** Orders module code backlog is complete. Remaining is a human-signed §5 audit pass using the scorecard template.
