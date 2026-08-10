# Authentication Architecture

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Version:** 1.1  
**Status:** APPROVED  
**Authority:** [masterrule.md](./masterrule.md) §15

---

## Principle

**Clerk is the only authentication provider** for Porterchain end users. No Supabase, Twilio Verify, custom OTP, or alternate IdP handles signup, login, MFA, email/phone verification, OAuth, sessions, or logout.

---

## Locked topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PORTERCHAIN SURFACES                             │
├──────────────┬──────────────┬──────────────┬───────────────────────────┤
│   Website    │   Merchant   │    Admin     │ Customer │ Driver (web + mobile)   │
│   :3000      │   :3001      │   :3002      │ :3004    │ :3003 / Expo ×2         │
└──────┬───────┴──────┬───────┴──────┬───────┴─────────────┬─────────────┘
       │              │              │                     │
       └──────────────┴──────────────┴─────────────────────┘
                              │
                    Clerk (IdP — sessions, MFA, OAuth)
                              │
                              ▼
              ┌───────────────────────────────┐
              │     Porterchain API :8001      │
              │  auth/clerk.py — JWKS verify   │
              │  RBAC — admin + merchant       │
              └───────────────┬───────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   Booking engine      Merchant engine       Driver engine
   (retail drafts)     (B2B portal)          (Clerk → session JWT)
```

### Not in this diagram (execution / integration only)

```
Porterchain API ──dispatcher key──► Fleetbase :8000  (dispatch, GPS, POD)
Porterchain API ──SSO JWT────────► Fleetbase :4200  (admin console)
```

Fleetbase Sanctum is **not** a Porterchain user login path.

---

## Clerk scope (exclusive)

| Capability                  | Provider |
| --------------------------- | -------- |
| Signup                      | Clerk    |
| Login                       | Clerk    |
| Password reset              | Clerk    |
| MFA                         | Clerk    |
| Email verification          | Clerk    |
| Phone verification          | Clerk    |
| OAuth (Google, Apple, etc.) | Clerk    |
| Session management          | Clerk    |
| Logout                      | Clerk    |

Porterchain must **not** implement parallel verification for any of the above.

---

## API authentication layers

### Layer 1 — Clerk JWT (all portal users)

```python
# apps/api/src/porterchain_api/auth/clerk.py
claims = await verify_clerk_token(bearer_token, settings)
# → clerk_user_id, email, org_id, metadata
```

Used by: merchant routes, admin routes, customer routes, driver login.

### Layer 2 — RBAC (authorization, not authentication)

| Package                   | Scope                                |
| ------------------------- | ------------------------------------ |
| `admin_engine/rbac.py`    | Admin roles (ops, finance, sales, …) |
| `merchant_engine/rbac.py` | Merchant org permissions             |
| `packages/auth/`          | Shared TS role helpers               |

### Layer 3 — Driver session bridge

After Clerk verifies identity, `DriverAuthService.login()` issues Porterchain session tokens for mobile API calls and offline sync. These are **API session tokens**, not a second identity provider.

```
Driver app → Clerk sign-in → POST /auth/login { email, clerk_bearer_token }
         → Porterchain access + refresh tokens → driver API routes
```

### Layer 4 — Machine auth (not user auth)

| Mechanism                        | Use                       |
| -------------------------------- | ------------------------- |
| Merchant API keys                | B2B integrations          |
| `PORTERCHAIN_DISPATCHER_API_KEY` | Fleetbase dispatch bridge |
| Stripe webhook signatures        | Payment events            |
| Fleetbase webhook secret         | Inbound logistics events  |

---

## Per-surface flows

### Website retail booking (masterrule §10.1)

```
Visitor → Quote → Booking Draft (server-persisted)
       → Clerk authentication
       → Session merge → draft restore
       → Stripe Checkout → webhook → BOOKING_CONFIRMED
```

No OTP step. Clerk handles identity before payment.

### Merchant portal

```
Clerk sign-up → onboarding state machine → Porterchain API (JWT)
             → merchant_engine RBAC → dashboard
```

### Customer portal

```
Clerk sign-in → apps/customer/ (:3004) → Porterchain API (JWT)
             → customer routes + support
```

### Admin portal

```
Clerk sign-in → AdminAccessGate → Porterchain API
             → admin_engine RBAC → ops modules
```

Admin opens Fleetbase console via **SSO JWT** (`sso_service.py`) — separate from user auth.

### Driver mobile / web

```
Clerk sign-in → /auth/login → session tokens → driver_engine routes
Invite flow: /auth/driver-invite → Clerk password → ACTIVE
```

Mobile: `apps/mobile-driver/` and `apps/mobile-customer/` are blank Expo shells — `@clerk/clerk-expo` is not wired yet (`pnpm clerk:sync` clears unused `EXPO_PUBLIC_CLERK_*`).

---

## Enterprise Clerk apps (production)

| Clerk app              | User class       | Frontend(s)                                        |
| ---------------------- | ---------------- | -------------------------------------------------- |
| `porterchain-customer` | Retail customers | Website, `apps/customer/`, `apps/mobile-customer/` |
| `porterchain-merchant` | B2B merchants    | Merchant portal                                    |
| `porterchain-admin`    | Internal staff   | Admin portal                                       |
| `porterchain-driver`   | Drivers          | Driver portal, `apps/mobile-driver/`               |

Per-class `CLERK_{CLASS}_SECRET_KEY` + `CLERK_{CLASS}_JWKS_URL` in API; frontends use matching publishable keys. Local dev may use legacy single `CLERK_*` vars for all classes.

### Portal access gates

| Portal     | Middleware    | API gate                                       |
| ---------- | ------------- | ---------------------------------------------- |
| Admin      | Clerk session | `GET /v1/auth/session-context` + SpiceDB Check |
| Merchant   | Clerk session | `GET /v1/auth/session-context` + SpiceDB Check |
| Customer   | Clerk session | `GET /v1/auth/session-context` + SpiceDB Check |
| Driver web | Clerk session | `GET /v1/auth/session-context` + SpiceDB Check |

Authorization uses **SpiceDB** (relationship Checks). Persona rows (`admin_users`, `merchant_users`, `customers`, `drivers`) are **data** that feed tuples — not the Check engine. See [auth-clerk-spicedb.md](docs/architecture/auth-clerk-spicedb.md).

> Removed (2026-07): `GET /v1/auth/{admin,merchant,customer,driver}/access` — do not resurrect.

### Public order tracking

`GET /v1/orders/{tracking_number}` is intentionally unauthenticated — tracking number only.

---

## Delivery OTP (operational — not auth)

Recipient codes at dropoff (`otp_required`, `verify_otp` in `pod.py`) verify **delivery completion**, not user identity. This is outside Clerk scope and remains in the driver platform.

---

## Transactional email (not auth)

SMTP configuration (`MAIL_*`, `SMTP_*` in platform settings) supports the **notification engine** — invoices, ops alerts, driver invites. Email is not used for login verification.

| Channel               | Auth? | Provider                         |
| --------------------- | ----- | -------------------------------- |
| Email (transactional) | No    | SMTP (Zoho or other)             |
| SMS (notifications)   | No    | Log-only until provider selected |
| Push                  | No    | Firebase FCM                     |

---

## Environment variables

### Required — Clerk

| Variable                            | Surface              |
| ----------------------------------- | -------------------- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | All Next.js apps     |
| `CLERK_SECRET_KEY`                  | API + Next.js server |
| `CLERK_JWKS_URL`                    | API JWT verification |

### Public contact (not auth)

| Variable                    | Default                |
| --------------------------- | ---------------------- |
| `NEXT_PUBLIC_CONTACT_EMAIL` | `ravi@porterchain.com` |

### Removed (do not use)

- `NEXT_PUBLIC_SUPABASE_*`
- `PORTERCHAIN_WEBSITE_OTP_KEY`
- `BOOKING_OTP_*`
- `BOOKING_OTP_SMTP_*`
- `TWILIO_*` (for auth or OTP)

---

## Security requirements

| Requirement      | Implementation                                |
| ---------------- | --------------------------------------------- |
| HTTPS everywhere | Production TLS 1.2+                           |
| JWT verification | Clerk JWKS — no shared secret for user tokens |
| Clerk MFA        | Recommended for merchant admins               |
| Dev bypass       | `CLERK_DEV_BYPASS` — local only               |
| Secret rotation  | Clerk keys quarterly                          |
| Audit            | Booking draft transitions, admin actions      |

---

## Golden rules

1. **Never** add a second user authentication provider.
2. **Never** use SMS or email OTP for login — Clerk owns verification.
3. Controllers authenticate via Clerk; services enforce business rules (§3).
4. Fleetbase auth is for **execution integration** only.
5. Update this document before any intentional auth architecture change (masterrule §20).

---

## Related documents

| Document                                                                               | Purpose                            |
| -------------------------------------------------------------------------------------- | ---------------------------------- |
| [docs/architecture/AUTHENTICATION_FLOW.md](./docs/architecture/AUTHENTICATION_FLOW.md) | Flow diagrams + code map           |
| [RBAC.md](./RBAC.md)                                                                   | Role matrix                        |
| [SSO.md](./SSO.md)                                                                     | Fleetbase console SSO              |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)                                 | Env var reference                  |
| [AUTHENTICATION_ARCHITECTURE.md](AUTHENTICATION_ARCHITECTURE.md)                       | Historical pre-cleanup inventory   |
| [AUTHENTICATION_ARCHITECTURE.md](AUTHENTICATION_ARCHITECTURE.md)                       | Historical cleanup log             |
| [docs/archive/CLERK_INTEGRATION_REPORT.md](./docs/archive/CLERK_INTEGRATION_REPORT.md) | Historical Clerk integration audit |

---

_Architecture locked per masterrule.md §15. Violations should be fixed in refactor, not extended._
---
