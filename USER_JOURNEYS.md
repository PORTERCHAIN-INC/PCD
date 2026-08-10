# Porterchain — User Journeys

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

---

## Personas

| Persona    | Role                            | Primary surface                              |
| ---------- | ------------------------------- | -------------------------------------------- |
| **Alex**   | Individual customer             | Website + `apps/customer/` + mobile customer |
| **Morgan** | Business owner / merchant admin | Merchant portal                              |
| **Jordan** | Merchant ops user               | Merchant portal                              |
| **Sam**    | Dispatcher                      | Admin / Fleetbase console                    |
| **Riley**  | Driver partner                  | `apps/mobile-driver/` + driver web portal    |
| **Casey**  | Support agent                   | Admin support module                         |
| **Taylor** | Sales rep                       | Admin CRM                                    |
| **Admin**  | Porterchain operations lead     | Admin (all modules)                          |

---

## Journey 1 — Alex (retail): instant delivery

### Goal

Ship a furniture item across the GTA today without creating a business account.

| Step | Touchpoint                                                       | Emotion        | System                  |
| ---- | ---------------------------------------------------------------- | -------------- | ----------------------- |
| 1    | Lands on homepage                                                | Curious        | Marketing site          |
| 2    | Fills booking widget (pickup, dropoff, van, weight, schedule)    | Hopeful        | Quote API → `QUOTE`     |
| 3    | Sees $89 estimate in 2 seconds                                   | Delighted      | No login required       |
| 4    | Clicks **Continue Booking**                                      | Committed      | —                       |
| 5    | Enters email + phone                                             | Mild friction  | Lead capture            |
| 6    | Clerk sign-up (Google or email)                                  | Acceptable     | Account created         |
| 7    | Stripe payment                                                   | Trust-critical | `PAYMENT_PENDING`       |
| 8    | Confirmation + dashboard redirect                                | Relieved       | `BOOKED`                |
| 9    | Tracks shipment on dashboard (`apps/customer/` or website track) | In control     | Porterchain API polling |
| 10   | Receives delivery + POD photo                                    | Satisfied      | `DELIVERED` → `CLOSED`  |
| 11   | Downloads receipt                                                | Done           | Invoice PDF             |

**Pain points to design for:** Quote clarity, payment trust badges, proactive SMS on delays.

**Abandoned path:** Alex leaves at step 7 → remarketing email with resume link within 24h.

---

## Journey 2 — Alex (retail): rebook

| Step | Action                                                                |
| ---- | --------------------------------------------------------------------- |
| 1    | Logs into customer dashboard (Clerk)                                  |
| 2    | Views order history                                                   |
| 3    | Clicks **Rebook** on past order                                       |
| 4    | Widget pre-filled; adjusts schedule                                   |
| 5    | New quote → faster checkout (saved payment method if Stripe Customer) |

---

## Journey 3 — Morgan (merchant): from lead to first shipment

| Step | Touchpoint                             | Owner     |
| ---- | -------------------------------------- | --------- |
| 1    | Submits for-business form on website   | Marketing |
| 2    | Sales calls within 1 business day      | Taylor    |
| 3    | Commercial proposal sent               | Sales     |
| 4    | Sales approves → merchant invite email | Admin     |
| 5    | Morgan completes onboarding wizard     | Morgan    |
| 6    | Uploads COI + business registration    | Morgan    |
| 7    | Signs merchant agreement               | Morgan    |
| 8    | Admin compliance approves → `ACTIVE`   | Admin     |
| 9    | Morgan invites Jordan (ops user)       | Morgan    |
| 10   | First delivery booked (saved address)  | Jordan    |
| 11   | Order tracked; invoice on Net 30       | System    |

**Success criteria:** Time from lead to ACTIVE &lt; 5 business days (target).

---

## Journey 4 — Jordan (merchant ops): CSV bulk upload

| Step | Action                                      |
| ---- | ------------------------------------------- |
| 1    | Logs into merchant portal                   |
| 2    | Book Delivery → CSV Upload                  |
| 3    | Downloads template; fills 50 rows           |
| 4    | Upload → validation report (errors per row) |
| 5    | Confirms valid rows → 50 orders `BOOKED`    |
| 6    | Bulk tracking view; exports status EOD      |

---

## Journey 5 — Riley (driver): single job day

| Step | Action                       | State                                        |
| ---- | ---------------------------- | -------------------------------------------- |
| 1    | Opens app; sees Today's Jobs | —                                            |
| 2    | New assignment notification  | `DRIVER_ASSIGNED` (push when FCM configured) |
| 3    | Accepts job                  | `DRIVER_ACCEPTED`                            |
| 4    | Navigates to pickup          | `DRIVER_EN_ROUTE`                            |
| 5    | Arrives; confirms pickup     | `AT_PICKUP` → `PICKED_UP`                    |
| 6    | Drives to dropoff            | `IN_TRANSIT`                                 |
| 7    | Arrives at destination       | `AT_DESTINATION`                             |
| 8    | Customer signs; photo taken  | POD capture                                  |
| 9    | Marks delivered              | `DELIVERED` → `POD_COMPLETED`                |
| 10   | Views earnings in wallet     | Payout pending                               |

**Exception branch:** Customer unavailable → Riley reports exception → Support contacts Alex → reschedule or `FAILED`.

---

## Journey 6 — Sam (dispatcher): morning dispatch

| Step | Action                                                 |
| ---- | ------------------------------------------------------ |
| 1    | Opens admin dispatch dashboard                         |
| 2    | Reviews overnight bookings (`DISPATCH_READY` queue)    |
| 3    | Checks driver availability + vehicle classes           |
| 4    | Auto-assign runs for standard jobs; manual for flagged |
| 5    | Monitors live map during peak window                   |
| 6    | Reassigns job when Riley rejects                       |
| 7    | Escalates delayed SLA to support                       |

---

## Journey 7 — Casey (support): wrong address

| Step | Action                                               |
| ---- | ---------------------------------------------------- |
| 1    | Ticket from Alex: "driver went to wrong building"    |
| 2    | Views order timeline + GPS + POD attempt             |
| 3    | Confirms geocode error vs customer error             |
| 4    | Updates address; re-dispatches or refunds per policy |
| 5    | Exception closed; customer notified                  |
| 6    | Audit log complete for compliance                    |

---

## Journey 8 — Taylor (sales): lead conversion

| Step | Action                                               |
| ---- | ---------------------------------------------------- |
| 1    | New lead from website for-business                   |
| 2    | CRM: qualify (volume, lanes, industry)               |
| 3    | Schedule discovery call                              |
| 4    | Send rate card + SLA proposal                        |
| 5    | Mark opportunity won → trigger merchant provisioning |
| 6    | Hand off to onboarding team                          |

---

## Journey 9 — Merchant API integrator

| Step | Action                                                   |
| ---- | -------------------------------------------------------- |
| 1    | Morgan requests API access (Developers module)           |
| 2    | Admin issues API keys + webhook URL                      |
| 3    | ERP posts `POST /v1/merchant-api/shipments` with API key |
| 4    | Porterchain creates order → Fleetbase                    |
| 5    | Webhook `shipment.delivered` → ERP updates               |

---

## Journey comparison: Uber Direct vs Porter.in vs Porterchain

| Aspect        | Uber Direct–style      | Porter.in–style     | Porterchain                          |
| ------------- | ---------------------- | ------------------- | ------------------------------------ |
| Entry         | Instant quote, pay now | Sales-led B2B       | **Both**                             |
| Auth at quote | No                     | N/A (sales first)   | **No** for estimate                  |
| Payment       | Upfront Stripe         | Net terms / invoice | **Stripe retail** / **Net merchant** |
| Dispatch      | Platform automated     | Ops-assisted        | **Fleetbase + dispatcher**           |
| Compliance    | Light                  | Heavy (B2B)         | **WSIB, insured, audit POD**         |

---

## Related documents

- [PORTERCHAIN_CHARTER.md](./docs/PORTERCHAIN_CHARTER.md)
- [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)
- [ORDER_LIFECYCLE.md](./ORDER_LIFECYCLE.md)
- [README.md](docs/architecture/README.md)

---
