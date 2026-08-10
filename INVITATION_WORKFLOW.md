# Invitation Workflow

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Authority:** [masterrule.md](./masterrule.md) §15  
**Related:** [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md), [auth-clerk-spicedb.md](./docs/architecture/auth-clerk-spicedb.md)

---

## Policy

| Access type                                    | Signup                                               | Invitation            |
| ---------------------------------------------- | ---------------------------------------------------- | --------------------- |
| **Customer** (retail)                          | Allowed — website, `apps/customer/`, mobile-customer | Not required          |
| **Merchant**                                   | Blocked                                              | Required              |
| **Driver**                                     | Blocked                                              | Required              |
| **Admin staff**                                | Blocked                                              | Required              |
| **Dispatcher**                                 | Blocked                                              | Required (admin role) |
| **Support**                                    | Blocked                                              | Required (admin role) |
| **Finance**                                    | Blocked                                              | Required (admin role) |
| **Manager** (`fleet_manager`, `sales_manager`) | Blocked                                              | Required (admin role) |
| **Super Admin**                                | Blocked                                              | Required (admin role) |

Clerk owns credentials. Porterchain **never stores passwords**. Invitations are sent through the **Clerk Invitations API**.

---

## Architecture

```
Admin / Merchant owner                Porterchain API                    Clerk
        │                                  │                              │
        │  POST invite (email, role)       │                              │
        ├─────────────────────────────────►│  InvitationService           │
        │                                  │  ├─ provision pending row    │
        │                                  │  └─ POST /v1/invitations ───►│
        │                                  │                              │ email
        │                                  │                              ▼
        │                                  │                         Invitee
        │                                  │                              │
        │                                  │◄── JWT on first sign-in ─────┤
        │                                  │  UserSyncService             │
        │                                  │  ├─ link clerk_user_id       │
        │                                  │  ├─ porterchain_users        │
        │                                  │  └─ mark invitation accepted │
```

### Components

| Layer               | Module                             | Responsibility                           |
| ------------------- | ---------------------------------- | ---------------------------------------- |
| Adapter             | `auth/clerk_client.py`             | Clerk Users + Invitations HTTP API       |
| Application Service | `auth/invitation_service.py`       | Invite workflows + domain provisioning   |
| Persistence         | `invitation_models.UserInvitation` | Audit trail                              |
| Sync                | `auth/user_sync_service.py`        | Activate invitation on first Clerk login |

---

## Workflows

### 1. Admin staff enroll (staff IdP — no Clerk)

**Who can enroll:** Super admin / settings module (`settings` RBAC)

**API:** `POST /v1/admin/settings/staff/enroll` · reissue `POST …/staff/{id}/enroll-reissue`  
**Login:** `POST /v1/auth/staff/login-request` → `/activate-staff?token=…`

Clerk `invite_admin_staff` / `POST /settings/staff/invite` are **deleted**.

**Steps:**

1. Admin enrolls from **Settings → Users → Staff → Add staff**
2. `StaffIdpService.enroll()` provisions `admin_users` + SpiceDB subject `staff:{id}` + one-time token
3. Staff opens activate link (or requests login from `/sign-in`) → Redis `pc_staff_sid` session
4. Admin API auth is staff session only (`admin_clerk_retired_use_staff_idp`)

---

### 2. Driver invite

**Who can invite:** Admin with `drivers` module

**Triggers:**

- `POST /v1/admin/drivers` — auto-invite on driver creation
- `POST /v1/admin/drivers/{id}/invite` — resend invitation

**Steps:**

1. Admin creates driver (email, profile, vehicle)
2. `AdminDriverService.create_driver()` → `InvitationService.invite_driver()`
3. Clerk invitation with `redirect_url = {DRIVER_PORTAL_URL}/login`
4. Driver activates via Clerk email
5. Driver portal: Clerk sign-in → `POST /driver-api/v1/auth/login` (session bridge)
6. Sync links `drivers.clerk_user_id` + `porterchain_users`

---

### 3. Merchant invite

**Who can invite:**

- **Admin** — CRM company conversion (`POST /v1/admin/crm/companies/{id}/convert-merchant`)
- **Merchant owner / teammate** — email seat reserve (`POST /v1/merchant/team/seats`, admin `…/owner-seat`) — no Clerk Invitation API; teammate self SignUp on Platform

**Steps (owner / teammate seat):**

1. Admin or merchant owner reserves seat by email + role (seat-reserve — **no** Clerk Invitation API)
2. `merchant_users` row created (`pending:{email}` or linked if Clerk user already exists)
3. Invitee self SignUp / SignIn on **Platform Clerk** → merchant portal
4. `get_merchant_context` requires matching `merchant_users` row + active merchant

**Self-signup for merchant org creation:** Disabled for cold `/sign-up` without a reserved seat.

---

### 4. Customer (open signup)

**Where:** Customer portal (`apps/customer`) `/book` after Platform Clerk sign-up. Website marketing CTAs → `/sign-up?intent=quote` only (no website booking wizard).

**Provisioning:** `CustomerService.upsert()` on booking flow; `porterchain_users` synced on API auth.

No `user_invitations` row required.

---

## Invitation record schema

**Table:** `user_invitations`

| Column                | Description                                     |
| --------------------- | ----------------------------------------------- |
| `email`               | Invitee email                                   |
| `user_type`           | `admin`, `merchant`, `driver`                   |
| `role`                | RBAC role at invite time                        |
| `status`              | `pending`, `accepted`, `revoked`, `expired`     |
| `clerk_invitation_id` | Clerk invitation ID                             |
| `clerk_user_id`       | Set when user exists or accepts                 |
| `platform_user_id`    | `admin_users` / `merchant_users` / `drivers` id |
| `invited_by`          | Admin user id (when applicable)                 |
| `redirect_url`        | Portal sign-in URL                              |

---

## Portal configuration

| Variable              | Default                 | Used for                     |
| --------------------- | ----------------------- | ---------------------------- |
| `ADMIN_PORTAL_URL`    | `http://localhost:3002` | Admin invite redirect        |
| `MERCHANT_PORTAL_URL` | `http://localhost:3001` | Merchant invite redirect     |
| `DRIVER_PORTAL_URL`   | `http://localhost:3003` | Driver invite redirect       |
| `WEBSITE_URL`         | `http://localhost:3000` | Customer website flows       |
| `CUSTOMER_PORTAL_URL` | `http://localhost:3004` | Customer app invite redirect |
| `CLERK_SECRET_KEY`    | —                       | Required to send invitations |

---

## Enforcement

| Surface  | Self-signup blocked                          | Access gated by                        |
| -------- | -------------------------------------------- | -------------------------------------- |
| Admin    | Clerk footer hidden; no public sign-up route | `admin_users` + RBAC                   |
| Merchant | `/sign-up` informational only; middleware    | `merchant_users` + org                 |
| Driver   | Clerk sign-up disabled on login              | `drivers` + Clerk token                |
| Customer | Open on website + `apps/customer/`           | `customers` (auto-provision on access) |

Creating a Clerk account **alone does not grant Porterchain access** for staff, merchant, or driver roles. A pending domain record must exist from an invitation.

---

## CLI (bootstrap)

Existing script for first super admin:

```bash
cd apps/api && python ../../infrastructure/scripts/provision_admin.py ravi@porterchain.com --role super_admin
```

Uses the same Clerk Invitations API pattern as `InvitationService`.

---

## Migrations

| Revision       | Table               |
| -------------- | ------------------- |
| `j1k2l3m4n5o6` | `porterchain_users` |
| `k2l3m4n5o6p7` | `user_invitations`  |

```bash
cd apps/api && alembic upgrade head
```

---

## Clerk dashboard checklist

1. Disable public sign-up for staff-only Clerk applications (or rely on Porterchain provisioning gate)
2. Allow invitation-only mode in Clerk → Restrictions
3. Configure email templates for invitations
4. Add portal URLs to allowed redirect URLs

---

## Related documents

| Document                                                           | Purpose                   |
| ------------------------------------------------------------------ | ------------------------- |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) | Clerk-only policy         |
| [auth-clerk-spicedb.md](./docs/architecture/auth-clerk-spicedb.md) | Invitation policy by role |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)             | Portal URL env vars       |

---

_Violations: bypassing invitation for merchant/driver/admin provisioning is a security defect per masterrule §15._
---
