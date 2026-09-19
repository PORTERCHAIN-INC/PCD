# Customer persona + Admin Customers — development test cases

**Status:** living catalog for local/CI development (not prod Doppler validation).  
**Entry SSOT:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).  
**Parent index (full stack):** [DEV_TEST_CASES_FULL_STACK.md](DEV_TEST_CASES_FULL_STACK.md).  
**Companion (Fleetbase + all integrations):** [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md).  
**Mapped:** 2026-09-17 via Graphify (`graphify query` / `explain` / `god-nodes`) + `ARCHITECTURE.md` leaf personas.  
**Sensor note:** This session used **Graphify only** (one sensor / session). Follow-ups:

| Next moment | Tool                                       | Use for                                                                                  |
| ----------- | ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| B           | CodeGraph MCP `codegraph_explore`          | Pydantic/ORM for `Customer`, `Quote`, `Order`, `Payment`, privacy DSR fields             |
| C           | Ripwire `--for` / `--callers` / `--impact` | Thin routers `customers.py`, `customers_admin.py`, Clerk/Stripe adapters, portal `lib/*` |

**Existing coverage seed:** `apps/api/tests/test_wave2_customers.py` (RBAC modules, detail 404, email-mismatch upsert, orphan merge). Expand from there; do not duplicate.

**Charter gate:** Prefer cases that protect revenue, trust, identity integrity, and the retail booking loop. Mobile customer depth beyond Sign-in + Track is an intentional skip (`docs/PCD_INTENTIONAL_SKIPS.md`).

---

## 0. ID scheme & layers

| Prefix    | Layer                                                   |
| --------- | ------------------------------------------------------- |
| `C-UI-*`  | Customer web portal `:3004`                             |
| `C-MOB-*` | Customer Expo shell                                     |
| `A-UI-*`  | Admin Customers UI `:3002`                              |
| `API-C-*` | `/v1/customers/*`                                       |
| `API-A-*` | `/v1/admin/customers/*`                                 |
| `API-B-*` | Booking loop `/v1/quotes` `/v1/bookings` `/v1/orders/*` |
| `ENG-*`   | Engine/service unit                                     |
| `AUTH-*`  | Clerk / onboarding / RBAC / IDOR                        |
| `SPA-*`   | Valhalla / OSRM / Google Places (places only)           |
| `FB-*`    | Fleetbase adapter handshake                             |
| `PAY-*`   | Stripe Checkout / webhooks / invoices                   |
| `NOTIF-*` | Inbox / FCM / email / Mailpit                           |
| `INT-*`   | Shopify / ERP / website visitor handoff                 |
| `DB-*`    | Postgres models / migrations / constraints              |
| `DOC-*`   | Docker / compose / ports / health                       |
| `ARCH-*`  | Architecture contracts / OpenAPI census / ownership     |

**Priority:** P0 = ship-blocker · P1 = trust/money · P2 = polish/regression · P3 = future/mobile depth.

Each case: **Precondition → Steps → Expected → Layer tags**.

---

## 1. Surface inventory (SSOT for “every page”)

### 1.1 Customer web (`apps/customer`)

| Route                     | Primary files                                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `/`                       | `app/page.tsx`, `components/welcome/CustomerWelcomeHome.tsx`                                                 |
| `/sign-in/[[...sign-in]]` | `app/sign-in/...`, `components/auth/CustomerAuthScreen.tsx`                                                  |
| `/sign-up/[[...sign-up]]` | `app/sign-up/...`, `CustomerAuthScreen.tsx`                                                                  |
| `/onboarding`             | `app/onboarding/page.tsx`, `PortalOnboardingView.tsx`, `hooks/useCustomerOnboarding.ts`, `lib/onboarding.ts` |
| `/dashboard`              | `app/dashboard/page.tsx` + layout, `CustomerShell.tsx`, `CustomerAccessGate.tsx`                             |
| `/book`                   | `app/book/page.tsx` + layout, `CustomerBookDelivery.tsx`, `lib/booking.ts`                                   |
| `/book/success`           | `app/book/success/page.tsx`                                                                                  |
| `/track`                  | `app/track/page.tsx`                                                                                         |
| `/track/[trackingNumber]` | `app/track/[trackingNumber]/page.tsx`, `CustomerLiveTrack.tsx`                                               |
| `/account`                | `app/account/page.tsx` (privacy export/delete)                                                               |
| `/notifications`          | `app/notifications/page.tsx`, `lib/notifications.ts`, `NotificationBell.tsx`                                 |
| Cross-cutting             | `middleware.ts`, `lib/api.ts`, `lib/env.ts`, `lib/visitor-session.ts`, `HeaderDropdown.tsx`                  |

### 1.2 Admin Customers (`apps/admin`)

| Route / sub-surface | Files                                                                                               |
| ------------------- | --------------------------------------------------------------------------------------------------- |
| `/customers` list   | `app/(ops)/customers/page.tsx`, `lib/customers.ts`                                                  |
| `/customers/[id]`   | `app/(ops)/customers/[id]/page.tsx`                                                                 |
| Tabs on detail      | `overview` · `orders` · `care` · `billing` · `trust` · `activity` · `tasks`                         |
| Add order modal     | `components/customers/CustomerAddOrderModal.tsx`                                                    |
| Related             | `/booking-drafts`, `/booking-drafts/[id]`, Settings → Users → customer tab, `/support?customer_id=` |

### 1.3 API / engines (Graphify god-path neighbors)

| Area                   | Path                                                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Customer portal router | `routers/customers.py`                                                                                              |
| Admin customers router | `routers/customers_admin.py`                                                                                        |
| Services               | `booking_engine/customer_service.py`, `admin_engine/customer_admin_service.py`, `customer_booking_admin_service.py` |
| Auth                   | `auth/customer.py`, `auth/customer_onboarding.py`, `auth/persona_bundle.py`, `clerk_*`                              |
| Booking loop           | `booking_engine/{booking,confirmation,payment,tracking,draft_*}*.py`                                                |
| Privacy                | `compliance_engine/privacy_service.py`                                                                              |
| Notifications          | `notification_engine/*`, `routers/notifications.py`                                                                 |
| Models                 | `booking_models.py` (`Customer`, `Booking`, quotes/orders/payments)                                                 |
| Mobile shell           | `apps/mobile-customer` (SignIn + Track)                                                                             |

### 1.4 Integrations in scope for retail customer

Clerk (customer triad) · Stripe Checkout · Mailpit/email · notification inbox + FCM (web/mobile) · Valhalla/OSRM (quote distance) · Google **Places** (address UX only) · Fleetbase (post-pay order sync / tracking) · website `:3000` visitor session handoff · public track · (Shopify is merchant channel; assert retail customer path does **not** require Shopify).

---

## 2. Customer portal UI / UX (`C-UI-*`)

### 2.1 Welcome & shell

| ID       | P   | Case                                                                                           |
| -------- | --- | ---------------------------------------------------------------------------------------------- |
| C-UI-001 | P0  | Unauthenticated `/` renders welcome; CTAs to sign-in, book/track as designed                   |
| C-UI-002 | P0  | `CustomerAccessGate` blocks dashboard/account when session missing; allows public track        |
| C-UI-003 | P1  | `CustomerShell` nav: Dashboard, Book, Track, Notifications, Account; active route highlighted  |
| C-UI-004 | P2  | Header dropdown + notification bell do not crash when Clerk/API temporarily down (error state) |

### 2.2 Auth screens

| ID       | P   | Case                                                                                             |
| -------- | --- | ------------------------------------------------------------------------------------------------ |
| C-UI-010 | P0  | Sign-in with valid Clerk test user lands on onboarding or dashboard per ready state              |
| C-UI-011 | P0  | Sign-up creates Clerk user; portal calls onboarding status                                       |
| C-UI-012 | P0  | Invalid credentials show Clerk error; no API call with empty Bearer                              |
| C-UI-013 | P1  | Dev bypass (`NEXT_PUBLIC_CLERK_DEV_BYPASS`) only when intended; production build must not enable |
| C-UI-014 | P1  | Middleware redirects pending-onboarding users away from dashboard to `/onboarding`               |

### 2.3 Onboarding

| ID       | P   | Case                                                                                             |
| -------- | --- | ------------------------------------------------------------------------------------------------ |
| C-UI-020 | P0  | `/onboarding` loads `GET /v1/auth/customer/onboarding` with Bearer                               |
| C-UI-021 | P0  | Incomplete onboarding shows required fields; submit provisions customer row                      |
| C-UI-022 | P0  | Completed onboarding redirects to `/dashboard`                                                   |
| C-UI-023 | P1  | Phone/email validation matches API errors (surface `detail`, not opaque 500)                     |
| C-UI-024 | P1  | Visitor session handoff (`visitor-session.ts`) attaches prior website quote context when present |

### 2.4 Dashboard

| ID       | P   | Case                                                                                      |
| -------- | --- | ----------------------------------------------------------------------------------------- |
| C-UI-030 | P0  | Dashboard calls `GET /v1/customers/me/dashboard` and renders recent orders / next actions |
| C-UI-031 | P0  | Empty state when no orders (copy + CTA to Book)                                           |
| C-UI-032 | P0  | 403 portal-not-ready → redirect/onboarding message (not blank page)                       |
| C-UI-033 | P1  | Rebook action posts `POST /v1/customers/me/rebook/{order_id}` and pre-fills book flow     |
| C-UI-034 | P1  | Support ticket create from dashboard (if exposed) posts subject/description/order_id      |
| C-UI-035 | P1  | Order row links to `/track/{trackingNumber}`                                              |

### 2.5 Book delivery

| ID       | P   | Case                                                                                             |
| -------- | --- | ------------------------------------------------------------------------------------------------ |
| C-UI-040 | P0  | Places autocomplete (Google) fills pickup/dropoff with lat/lng/place_id when Maps key set        |
| C-UI-041 | P0  | Without Maps key, manual address path still quotes if API accepts coords/formatted               |
| C-UI-042 | P0  | Quote → `POST /v1/quotes`; UI shows amount CAD + vehicle class                                   |
| C-UI-043 | P0  | Start booking → `POST /v1/bookings` → Stripe Checkout URL or mock-complete in dev                |
| C-UI-044 | P0  | Success page syncs checkout (`sync-checkout` / mock-complete) and shows tracking number          |
| C-UI-045 | P1  | Quote expiry / stale quote_id shows recoverable error; no double-charge UX                       |
| C-UI-046 | P1  | Schedule mode + scheduled_at validation (past time rejected)                                     |
| C-UI-047 | P1  | Weight/dimensions/package_type affect quote when engine requires them                            |
| C-UI-048 | P0  | **Assert Google is never used for distance/price** (network stub: Valhalla/OSRM only for matrix) |

### 2.6 Track

| ID       | P   | Case                                                                                          |
| -------- | --- | --------------------------------------------------------------------------------------------- |
| C-UI-050 | P0  | `/track` form navigates to `/track/{n}`                                                       |
| C-UI-051 | P0  | Public `GET /v1/orders/{n}` renders state timeline without auth                               |
| C-UI-052 | P0  | Live map/`GET .../tracking` updates driver position when Fleetbase/adapter provides it        |
| C-UI-053 | P1  | Unknown tracking → empty/404 friendly state                                                   |
| C-UI-054 | P1  | Authenticated owner sees same track; non-owner still limited to public snapshot (no PII leak) |

### 2.7 Account / privacy

| ID       | P   | Case                                                                                  |
| -------- | --- | ------------------------------------------------------------------------------------- |
| C-UI-060 | P0  | Privacy export downloads/shows `GET /v1/customers/me/privacy/export`                  |
| C-UI-061 | P0  | Delete request `POST .../privacy/delete-request` confirms and sets DSR hold messaging |
| C-UI-062 | P1  | After DSR hold, booking CTA disabled or API 403 explained in UI                       |

### 2.8 Notifications

| ID       | P   | Case                                      |
| -------- | --- | ----------------------------------------- |
| C-UI-070 | P0  | Inbox lists `GET /v1/notifications/inbox` |
| C-UI-071 | P0  | Mark one read + mark-all-read             |
| C-UI-072 | P1  | Bell badge count updates after read       |
| C-UI-073 | P1  | Empty inbox state                         |

### 2.9 UX / a11y / responsive (cross-page)

| ID       | P   | Case                                                        |
| -------- | --- | ----------------------------------------------------------- |
| C-UI-080 | P2  | Mobile viewport: book form usable; no horizontal overflow   |
| C-UI-081 | P2  | Focus order on book CTA; buttons have accessible names      |
| C-UI-082 | P2  | Loading spinners vs stale data (no flash of wrong customer) |

---

## 3. Admin Customers UI (`A-UI-*`)

### 3.1 List `/customers`

| ID       | P   | Case                                                                     |
| -------- | --- | ------------------------------------------------------------------------ |
| A-UI-001 | P0  | Page requires admin auth; unauthenticated redirected                     |
| A-UI-002 | P0  | Stats tiles: total, clerk_linked, orphan, dsr_hold, revenue_30d          |
| A-UI-003 | P0  | Search filters list via `customersApi.list`                              |
| A-UI-004 | P0  | Chips: linked / orphan / dsr map to `clerk_linked` / `privacy_status`    |
| A-UI-005 | P0  | Copy states Admin **cannot** create/invite customers (self SignUp only)  |
| A-UI-006 | P1  | Row click → `/customers/[id]`                                            |
| A-UI-007 | P1  | Link “Open in Settings → Users” → `/settings?section=users&tab=customer` |
| A-UI-008 | P1  | RBAC: role without `customers_read` sees 403 / empty gated UI            |
| A-UI-009 | P2  | Empty search results EmptyState                                          |

### 3.2 Detail `/customers/[id]` — shell

| ID       | P   | Case                                                                        |
| -------- | --- | --------------------------------------------------------------------------- |
| A-UI-010 | P0  | Loads detail; shows display_name, email, phone, ref, Stripe id, Clerk badge |
| A-UI-011 | P0  | Missing id → EmptyState “Customer not found”                                |
| A-UI-012 | P0  | DSR hold badge; **Add order** disabled                                      |
| A-UI-013 | P0  | Tabs switch without full remount losing banner state incorrectly            |
| A-UI-014 | P1  | Support tickets link includes `?customer_id=`                               |

### 3.3 Tab: Overview

| ID       | P   | Case                                                 |
| -------- | --- | ---------------------------------------------------- |
| A-UI-020 | P0  | Lifetime orders/revenue, last order, identity status |
| A-UI-021 | P1  | Recent orders snippet matches detail payload         |
| A-UI-022 | P1  | settings_users_href navigates when present           |

### 3.4 Tab: Orders + Add order

| ID       | P   | Case                                                                        |
| -------- | --- | --------------------------------------------------------------------------- |
| A-UI-030 | P0  | Orders list from `GET .../orders`; state filter if UI exposes               |
| A-UI-031 | P0  | Add order modal: Places pickup/dropoff + vehicle + schedule                 |
| A-UI-032 | P0  | Submit creates booking draft + optional Stripe payment link                 |
| A-UI-033 | P0  | Success banner shows draft_number / checkout_url; link opens                |
| A-UI-034 | P1  | Resend payment link for existing draft                                      |
| A-UI-035 | P1  | Validation errors (400) shown; no silent fail                               |
| A-UI-036 | P0  | Role with only `customers_read` cannot submit Add order (needs `customers`) |

### 3.5 Tab: Care

| ID       | P   | Case                                                       |
| -------- | --- | ---------------------------------------------------------- |
| A-UI-040 | P0  | Care panel shows support tickets + claims counts and lists |
| A-UI-041 | P1  | Open ticket deep-link to support module                    |

### 3.6 Tab: Billing

| ID       | P   | Case                                                     |
| -------- | --- | -------------------------------------------------------- |
| A-UI-050 | P0  | Invoices + payments tables load                          |
| A-UI-051 | P1  | Receipt / PDF URLs open when present                     |
| A-UI-052 | P1  | Amounts in cents formatted CAD consistently with Finance |

### 3.7 Tab: Trust / Activity / Tasks

| ID       | P   | Case                                               |
| -------- | --- | -------------------------------------------------- |
| A-UI-060 | P1  | Trust: EntityAlertsPanel for customer entity       |
| A-UI-061 | P1  | Activity timeline loads CRM activity for customer  |
| A-UI-062 | P1  | Tasks CRUD (EntityTasks) scoped to customer entity |
| A-UI-063 | P2  | Empty states for no alerts/activity/tasks          |

### 3.8 Related admin surfaces

| ID       | P   | Case                                                                             |
| -------- | --- | -------------------------------------------------------------------------------- |
| A-UI-070 | P1  | Booking draft created from customer appears on `/booking-drafts`                 |
| A-UI-071 | P1  | Clerk directory customer tab lists linked users; orphan not inventable as invite |
| A-UI-072 | P2  | Finance invoice detail for customer-owned order consistent with Billing tab      |

---

## 4. Customer API (`API-C-*`) — `/v1/customers`

| ID        | P   | Endpoint                                                               | Case                                                                                   |
| --------- | --- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| API-C-001 | P0  | `GET /me/dashboard`                                                    | 200 with auth + portal ready                                                           |
| API-C-002 | P0  | same                                                                   | 401 without Bearer                                                                     |
| API-C-003 | P0  | same                                                                   | 403 when onboarding incomplete (`require_customer_portal_ready`)                       |
| API-C-004 | P0  | `GET /me/support`                                                      | lists only caller’s tickets                                                            |
| API-C-005 | P0  | `POST /me/support`                                                     | creates ticket; Idempotency-Key replay returns same ticket                             |
| API-C-006 | P1  | `POST /me/support`                                                     | foreign `order_id` → 403                                                               |
| API-C-007 | P0  | `POST /me/rebook/{order_id}`                                           | returns quote-ready payload for owned order                                            |
| API-C-008 | P0  | same                                                                   | unknown/other-user order → 404 `order_not_found` (no existence leak beyond 404 policy) |
| API-C-009 | P0  | `GET /me/privacy/export`                                               | JSON includes customer PII fields under policy                                         |
| API-C-010 | P0  | `POST /me/privacy/delete-request`                                      | sets deletion_hold; subsequent booking blocked                                         |
| API-C-011 | P1  | Cross-portal token (merchant/driver Clerk) rejected on customer routes |

---

## 5. Admin Customers API (`API-A-*`) — `/v1/admin/customers`

| ID        | P   | Endpoint                                                                      | Case                                                        |
| --------- | --- | ----------------------------------------------------------------------------- | ----------------------------------------------------------- |
| API-A-001 | P0  | `GET /stats`                                                                  | requires `customers_read`                                   |
| API-A-002 | P0  | `GET /`                                                                       | search, clerk_linked, privacy_status, limit clamps          |
| API-A-003 | P0  | `GET /{id}`                                                                   | 200 detail; 404 `customer_not_found`                        |
| API-A-004 | P0  | `GET /{id}/orders`                                                            | filter `state`; limit bounds                                |
| API-A-005 | P0  | `GET /{id}/invoices`                                                          | customer-scoped only                                        |
| API-A-006 | P0  | `GET /{id}/payments`                                                          | customer-scoped only                                        |
| API-A-007 | P0  | `GET /{id}/care`                                                              | tickets + claims                                            |
| API-A-008 | P0  | `POST /{id}/booking-drafts`                                                   | requires `customers` module; creates quote+draft            |
| API-A-009 | P0  | same                                                                          | `send_payment_link=true` returns checkout_url (Stripe test) |
| API-A-010 | P0  | same                                                                          | DSR hold / invalid address → 400                            |
| API-A-011 | P0  | `POST .../booking-drafts/{draft_id}/send-payment-link`                        | 200 link; wrong customer → 404                              |
| API-A-012 | P0  | Staff without module → 403                                                    |
| API-A-013 | P1  | Pagination defaults match `DEFAULT_LIST_LIMIT` / `MAX_LIST_LIMIT`             |
| API-A-014 | P1  | Admin **cannot** POST create-customer identity (no endpoint) — assert OpenAPI |

---

## 6. Booking / quote / order / track loop (`API-B-*`)

| ID        | P   | Case                                                              |
| --------- | --- | ----------------------------------------------------------------- |
| API-B-001 | P0  | `POST /v1/quotes` retail path returns amount_cents + quote_id     |
| API-B-002 | P0  | `GET /v1/quotes/{id}` matches create                              |
| API-B-003 | P0  | `POST /v1/bookings` with quote_id starts Stripe session (or mock) |
| API-B-004 | P0  | `POST /v1/bookings/mock-complete` only in non-prod / flag-gated   |
| API-B-005 | P0  | `POST /v1/bookings/sync-checkout` idempotent after paid           |
| API-B-006 | P0  | Paid booking creates Order + tracking_number                      |
| API-B-007 | P0  | `GET /v1/orders/{tracking}` public snapshot                       |
| API-B-008 | P0  | `GET /v1/orders/{tracking}/tracking` live payload shape stable    |
| API-B-009 | P1  | Quote≡Book amount (cents) invariant                               |
| API-B-010 | P1  | Concurrent double-submit booking does not create two paid orders  |
| API-B-011 | P1  | Visitor session id on quote attaches to Customer upsert on signup |

---

## 7. Engine / models (`ENG-*`, `DB-*`)

### 7.1 CustomerService / admin services

| ID      | P   | Case                                                                            |
| ------- | --- | ------------------------------------------------------------------------------- |
| ENG-001 | P0  | Upsert rejects email mismatch when Clerk already bound (`EMAIL_CLERK_MISMATCH`) |
| ENG-002 | P0  | Upsert merges orphan `pending:email` by email (case-insensitive)                |
| ENG-003 | P0  | `get_dashboard` only aggregates caller customer_id                              |
| ENG-004 | P0  | Rebook payload copies addresses/vehicle from prior order                        |
| ENG-005 | P0  | CustomerAdminService.detail 404                                                 |
| ENG-006 | P0  | CustomerBookingAdminService creates draft owned by customer_id                  |
| ENG-007 | P1  | PrivacyService export/delete-request side effects                               |
| ENG-008 | P1  | Support ticket idempotency store                                                |
| ENG-009 | P1  | Authz tuple sync after persona mutation (`sync_authz_after_persona_mutation`)   |

### 7.2 Database

| ID     | P   | Case                                                                  |
| ------ | --- | --------------------------------------------------------------------- |
| DB-001 | P0  | `Customer` unique constraints on clerk_user_id / email as designed    |
| DB-002 | P0  | FK integrity Order→Customer (migration `t2u3…` style integrity)       |
| DB-003 | P0  | privacy_status / hold_reference columns persist                       |
| DB-004 | P1  | Soft-delete / DSR hold does not hard-delete financial history         |
| DB-005 | P1  | Alembic upgrade/downgrade smoke for latest customer-related revisions |
| DB-006 | P2  | Seed scripts create retail customer usable in local E2E               |

---

## 8. Auth / Clerk / RBAC / IDOR (`AUTH-*`)

| ID       | P   | Case                                                                                |
| -------- | --- | ----------------------------------------------------------------------------------- |
| AUTH-001 | P0  | Customer Clerk JWKS validates `CLERK_CUSTOMER_*` triad only                         |
| AUTH-002 | P0  | `require_customer` creates/links row via onboarding provision path                  |
| AUTH-003 | P0  | Staff admin uses staff session / admin context — not customer Clerk                 |
| AUTH-004 | P0  | MODULE_PERMISSIONS: `customers` ⊇ `customers_read`                                  |
| AUTH-005 | P0  | IDOR: customer A cannot rebook/support on customer B orders (`test_idor` extension) |
| AUTH-006 | P0  | Admin IDOR: path customer_id must match draft ownership on payment-link             |
| AUTH-007 | P1  | Persona bundle load for customer portal                                             |
| AUTH-008 | P1  | Clerk webhook/user sync does not attach staff portal ids to Customer                |
| AUTH-009 | P1  | Local `CLERK_DEV_BYPASS` Bearer `dev` works only when env true                      |

---

## 9. Spatial stack (`SPA-*`) — Valhalla / OSRM / Google / VROOM

| ID      | P   | Case                                                                                  |
| ------- | --- | ------------------------------------------------------------------------------------- |
| SPA-001 | P0  | Retail quote distance uses Valhalla (primary)                                         |
| SPA-002 | P0  | Valhalla down → OSRM fallback for ETA/distance                                        |
| SPA-003 | P0  | Google Places autocomplete only; **no** Google Distance Matrix / Directions for price |
| SPA-004 | P1  | Invalid coords → quote 400 with clear detail                                          |
| SPA-005 | P1  | Isochrone/coverage rejection when outside service area (if engine enforces)           |
| SPA-006 | P2  | VROOM **not** called from customer quote path (Fleetbase/orchestrator only)           |
| SPA-007 | P1  | Admin phone-book draft uses same pricing distance path as retail                      |

---

## 10. Fleetbase handshake (`FB-*`)

| ID     | P   | Case                                                                                               |
| ------ | --- | -------------------------------------------------------------------------------------------------- |
| FB-001 | P0  | After paid confirmation, order syncs via `services/fleetbase-adapter` (not direct PHP from portal) |
| FB-002 | P0  | Tracking live feed reads adapter/Fleetbase ids; customer UI never imports SocketCluster            |
| FB-003 | P1  | Fleetbase down: confirmation still records payment; sync retry/job observable                      |
| FB-004 | P1  | Replay script / worker path for failed sync does not duplicate customer charge                     |
| FB-005 | P2  | Diagnostics probe includes Fleetbase health relevant to retail track                               |
| FB-006 | P0  | CI guard: no `fleetbase` HTTP from `apps/customer` / `apps/mobile-customer/src`                    |

---

## 11. Payments / Stripe / invoices (`PAY-*`)

| ID      | P   | Case                                                                   |
| ------- | --- | ---------------------------------------------------------------------- |
| PAY-001 | P0  | Checkout session success_url / cancel_url channel = customer portal    |
| PAY-002 | P0  | Webhook settles Payment + confirms booking (idempotent event id)       |
| PAY-003 | P0  | Admin send-payment-link creates Checkout for draft (no cash)           |
| PAY-004 | P1  | Stripe customer id stored on Customer when created                     |
| PAY-005 | P1  | Invoice/receipt URLs visible on admin Billing tab                      |
| PAY-006 | P1  | Failed card: order not created; draft remains payable                  |
| PAY-007 | P2  | COD Connect path **not** default for retail prepaid (Checkout remains) |
| PAY-008 | P1  | Tax/fees cents on invoice match confirmation breakdown                 |

---

## 12. Notifications / email / FCM (`NOTIF-*`)

| ID        | P   | Case                                                                     |
| --------- | --- | ------------------------------------------------------------------------ |
| NOTIF-001 | P0  | Booking confirmed → inbox row for customer principal                     |
| NOTIF-002 | P0  | Email via Mailpit in local: confirmation + payment link                  |
| NOTIF-003 | P1  | Mark read updates delivery state                                         |
| NOTIF-004 | P1  | FCM register device token (mobile/web) for customer app id               |
| NOTIF-005 | P1  | Zero-device fallback to email (if policy)                                |
| NOTIF-006 | P1  | Admin payment-link send triggers email to customer.email                 |
| NOTIF-007 | P2  | Notification preferences (if any) respected                              |
| NOTIF-008 | P0  | Cross-tenant: merchant notification principal cannot read customer inbox |

---

## 13. Website / Shopify / ERP / other connections (`INT-*`)

| ID      | P   | Case                                                                                 |
| ------- | --- | ------------------------------------------------------------------------------------ |
| INT-001 | P0  | Website `:3000` quote/book handoff sets visitor session; customer portal captures it |
| INT-002 | P1  | Portal links from website (`portal-links.ts`) hit `:3004` correct paths              |
| INT-003 | P1  | Shopify carrier/rate quotes are **merchant** channel — retail Customer 360 unchanged |
| INT-004 | P1  | Lead convert-to-customer (`leads` → CustomerService) creates orphan then Clerk link  |
| INT-005 | P2  | Public ingest / OAuth hijack blocks do not create Customer for attacker email        |
| INT-006 | P2  | No direct ERP write from customer portal; any ERP is admin/merchant integration only |
| INT-007 | P1  | Referral credits (if enabled migration) apply only to owning customer                |

---

## 14. Mobile customer (`C-MOB-*`)

| ID        | P   | Case                                                                    |
| --------- | --- | ----------------------------------------------------------------------- |
| C-MOB-001 | P0  | Sign-in screen with Clerk publishable key                               |
| C-MOB-002 | P0  | Track screen hits public `/v1/orders/{n}` on `:8001` (not `:8000`)      |
| C-MOB-003 | P1  | No Fleetbase / SocketCluster imports in `apps/mobile-customer/src`      |
| C-MOB-004 | P1  | FCM config files present for bundle `com.porterchain.customer`          |
| C-MOB-005 | P3  | Book/dashboard mobile depth — **intentional skip** until product unlock |

---

## 15. Docker / compose / architecture (`DOC-*`, `ARCH-*`)

| ID       | P   | Case                                                                                         |
| -------- | --- | -------------------------------------------------------------------------------------------- |
| DOC-001  | P0  | Customer app port **3004**; API **8001**; Valhalla **8002**; Mailpit up                      |
| DOC-002  | P0  | Postgres 18 + Redis reachable from API for customer sessions/inbox                           |
| DOC-003  | P1  | Exact image tags (no `:latest`) for services used by quote/track                             |
| DOC-004  | P1  | Worker processes booking confirmation / notification jobs                                    |
| ARCH-001 | P0  | OpenAPI census includes all `/v1/customers` and `/v1/admin/customers` ops                    |
| ARCH-002 | P0  | Thin-router law: routers stay thin; logic in `*_engine` / `auth/customer_onboarding`         |
| ARCH-003 | P0  | Model ownership: Customer writes in booking_engine (Wave 5)                                  |
| ARCH-004 | P1  | Graphify: CustomerService still connects to TrackingService / Support (no new mash-up edges) |
| ARCH-005 | P1  | `scripts/verify_model_ownership.py` green after customer changes                             |
| ARCH-006 | P2  | God-node discipline: do not grow Settings/Order coupling from customer UI                    |

---

## 16. Suggested automated harness mapping

| Suite                   | Cases                                                                                 | Location                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **P0 implemented**      | AUTH-004, API-C/A/B core, ENG privacy/rebook, UI arch smoke, Quote≡Book               | `apps/api/tests/test_customer_persona_p0.py`                             |
| **P0 integrations**     | PAY-001, API-A-008/009/011, SPA-001/002, FB-001, NOTIF-001/002/004, book UI contracts | `apps/api/tests/test_customer_persona_p0_integrations.py`                |
| Identity seed           | ENG-001/002, AUTH-004                                                                 | `apps/api/tests/test_wave2_customers.py`                                 |
| IDOR                    | AUTH-005, API-C-008                                                                   | `apps/api/tests/test_idor.py` (+ P0 HTTP rebook)                         |
| UI surface smoke        | C-UI/A-UI inventory, FB-006, Clerk book + payment-link wiring                         | `scripts/verify_customer_persona_surface.py` (no Playwright in monorepo) |
| Retail website boundary | INT-001 adjacent                                                                      | `scripts/verify_anonymous_retail_surface.py`                             |
| Booking loop            | API-B-*                                                                               | `apps/api/tests/integration/test_booking_loop.py`                        |
| Spatial / Stripe        | SPA-_, PAY-_                                                                          | existing quote + `test_stripe_checkout_urls.py`                          |

**Playwright:** not pinned in this repo (frontend freeze). Use the verify script + pytest HTTP until an explicit Playwright project is approved.

**Dev layer first** (`docs/PRIORITY_TODOS.md`): localhost + CI. Prod Doppler/`validate:*:prod` later.

---

## 17. Things you asked for that are in-scope vs adjacent

| You listed                          | Customer persona relevance                                               |
| ----------------------------------- | ------------------------------------------------------------------------ |
| FastAPI endpoints                   | Yes — §4–6                                                               |
| Microservices / adapters            | Fleetbase adapter, stripe service, driver-platform N/A for customer book |
| Fleetbase                           | Post-pay sync + track — §10                                              |
| Firebase / FCM                      | Inbox push — §12, mobile §14                                             |
| Clerk                               | §8, UI auth                                                              |
| VROOM                               | Out of customer quote path; assert absence — SPA-006                     |
| Valhalla / OSRM                     | Quote distance — §9                                                      |
| Google Maps                         | Places only — SPA-003 / C-UI-048                                         |
| Email / notifications               | §12                                                                      |
| UI/UX / pages                       | §2–3                                                                     |
| Models / DB / Docker / architecture | §7, §15                                                                  |
| Shopify / other ERP                 | Merchant/adjacent — §13; do not conflate with retail Customer 360        |
| Handshakes                          | Quote≡Book, Checkout URLs, Fleetbase sync, visitor session — §6/10/11/13 |

### Gaps you did not list (added here)

1. **Privacy DSR / PIPEDA-style delete-request hold** blocking admin Add order
2. **Orphan vs Clerk-linked identity** filters and merge-on-signup
3. **Idempotency-Key** on support tickets
4. **Visitor session** website → portal handoff
5. **RBAC split** `customers` vs `customers_read`
6. **Admin cannot mint customers** (product rule)
7. **IDOR** across customer and admin draft ownership
8. **Quote≡Book cents** invariant
9. **Mobile intentional thin shell** vs web full portal
10. **OpenAPI census / model ownership guards**
11. **Mailpit** as local email SSOT (not Mailhog)
12. **No SocketCluster in web/mobile customer**
13. **Lead → customer conversion** path
14. **Referral credits** (migration present)
15. **Settings → Users → customer** directory cross-link

---

## 18. Recommended next sensor passes (do not run in same session)

1. **CodeGraph:** extract `Customer`, `CustomerDashboardResponse`, admin detail dict schema, booking draft request models (for deeper contract tests).
2. **Ripwire:** already used for P0 implementation; re-run `--impact` before editing `customers.py` / `customers_admin.py`.
3. **Browser E2E:** Clerk book + admin Add-order Stripe click-path (manual or Playwright only if explicitly approved past frontend freeze).

---

## 19. P0 checklist (minimum green bar for retail)

**Automated now**

```bash
pytest apps/api/tests/test_customer_persona_p0.py \
       apps/api/tests/test_customer_persona_p0_integrations.py -q
python scripts/verify_customer_persona_surface.py
```

- [x] A-UI page/tab inventory + “self SignUp only” + Add-order Stripe wiring
- [x] C-UI book contract (Clerk + createQuote + mock/sync complete + `checkout_channel: customer`)
- [x] API-C-001/002/004/005/007/008/009/010 (HTTP + service)
- [x] API-A-001/002/003/008/009/011/012 (+ dispatcher cannot POST drafts)
- [x] API-B-007/009 (+ booking loop sibling for 001/006)
- [x] AUTH-004/005 · ENG-004/007 · SPA-001/002/003/006 · FB-001/006 · ARCH-001
- [x] PAY-001 (customer-channel Checkout URLs for phone-book + portal)
- [x] NOTIF-001/002/004 (event fan-out + Mailpit compose + FCM delivery stack)

**Still manual / live stack only**

- [ ] C-UI-010 full Clerk browser sign-in (needs test Clerk + headed browser)
- [ ] A-UI-032 click Stripe Checkout hosted page end-to-end
- [ ] SPA-001 against live Valhalla `:8002` (unit stubs cover path)
- [ ] FB-001 against live Fleetbase adapter (handler + dual-write covered)
- [ ] NOTIF-002 Mailpit UI message inspect after real booking

When automated P0 is green on localhost compose, customer persona + admin Customers are development-ready for the next hardening wave.
