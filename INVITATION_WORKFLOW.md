# Invitation Workflow

**Date:** July 1, 2026  
**Authority:** [masterrule.md](./masterrule.md) §15  
**Related:** [CLERK_INTEGRATION_REPORT.md](./CLERK_INTEGRATION_REPORT.md), [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)

---

## Policy

| Access type | Signup | Invitation |
|-------------|--------|------------|
| **Customer** (retail) | Allowed — website booking / customer portal | Not required |
| **Merchant** | Blocked | Required |
| **Driver** | Blocked | Required |
| **Admin staff** | Blocked | Required |
| **Dispatcher** | Blocked | Required (admin role) |
| **Support** | Blocked | Required (admin role) |
| **Finance** | Blocked | Required (admin role) |
| **Manager** (`fleet_manager`, `sales_manager`) | Blocked | Required (admin role) |
| **Super Admin** | Blocked | Required (admin role) |

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

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Adapter | `auth/clerk_client.py` | Clerk Users + Invitations HTTP API |
| Application Service | `auth/invitation_service.py` | Invite workflows + domain provisioning |
| Persistence | `invitation_models.UserInvitation` | Audit trail |
| Sync | `auth/user_sync_service.py` | Activate invitation on first Clerk login |

---

## Workflows

### 1. Admin staff invite

**Who can invite:** Super admin / settings module (`settings` RBAC)

**API:** `POST /v1/admin/settings/staff/invite`

```json
{
  "email": "dispatcher@porterchain.com",
  "role": "dispatcher",
  "name": "Ops Dispatcher"
}
```

**Steps:**

1. Admin submits invite from **Settings → Staff → Invite staff**
2. `InvitationService.invite_admin_staff()`:
   - Validates role ∈ `{super_admin, admin, dispatcher, support, support_lead, finance, fleet_manager, sales_manager}`
   - Creates/updates `admin_users` with `clerk_user_id = pending:{email}`
   - Calls Clerk `POST /v1/invitations` with `redirect_url = {ADMIN_PORTAL_URL}/sign-in`
   - Records `user_invitations` row (`user_type=admin`, `status=pending`)
3. Clerk emails invitation link
4. User completes Clerk signup / password setup
5. User signs in at admin portal → `get_admin_context` verifies `admin_users` row
6. `UserSyncService` links `clerk_user_id`, upserts `porterchain_users`, marks invitation `accepted`

**Invitable admin roles:**

| Role key | Label |
|----------|-------|
| `super_admin` | Super Admin |
| `admin` | Admin |
| `dispatcher` | Dispatcher |
| `support` | Support |
| `support_lead` | Support Lead |
| `finance` | Finance |
| `fleet_manager` | Fleet / Operations Manager |
| `sales_manager` | Sales Manager |

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
- **Merchant owner** — team invite (`POST /v1/merchant/team/invite`)

**Steps (owner invite):**

1. Merchant owner invites teammate email + role
2. `InvitationService.invite_merchant_member()` provisions `merchant_users` (`pending:{email}`)
3. Clerk invitation → `{MERCHANT_PORTAL_URL}/sign-in`
4. Invitee activates Clerk account
5. `get_merchant_context` requires matching `merchant_users` row + active merchant

**Self-signup:** Disabled — `/sign-up` shows invitation-only message; Clerk `signUpUrl` removed from merchant provider.

---

### 4. Customer (open signup)

**Where:** Website `book/continue` — Clerk `<SignIn />` (includes sign-up for new retail customers)

**Provisioning:** `CustomerService.upsert()` on booking flow; `porterchain_users` synced on API auth.

No `user_invitations` row required.

---

## Invitation record schema

**Table:** `user_invitations`

| Column | Description |
|--------|-------------|
| `email` | Invitee email |
| `user_type` | `admin`, `merchant`, `driver` |
| `role` | RBAC role at invite time |
| `status` | `pending`, `accepted`, `revoked`, `expired` |
| `clerk_invitation_id` | Clerk invitation ID |
| `clerk_user_id` | Set when user exists or accepts |
| `platform_user_id` | `admin_users` / `merchant_users` / `drivers` id |
| `invited_by` | Admin user id (when applicable) |
| `redirect_url` | Portal sign-in URL |

---

## Portal configuration

| Variable | Default | Used for |
|----------|---------|----------|
| `ADMIN_PORTAL_URL` | `http://localhost:3002` | Admin invite redirect |
| `MERCHANT_PORTAL_URL` | `http://localhost:3001` | Merchant invite redirect |
| `DRIVER_PORTAL_URL` | `http://localhost:3003` | Driver invite redirect |
| `WEBSITE_URL` | `http://localhost:3000` | Customer flows |
| `CLERK_SECRET_KEY` | — | Required to send invitations |

---

## Enforcement

| Surface | Self-signup blocked | Access gated by |
|---------|---------------------|-----------------|
| Admin | Clerk footer hidden; no public sign-up route | `admin_users` + RBAC |
| Merchant | `/sign-up` informational only; middleware | `merchant_users` + org |
| Driver | Clerk sign-up disabled on login | `drivers` + Clerk token |
| Customer | Open on website | `customers` (optional until first booking) |

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

| Revision | Table |
|----------|-------|
| `j1k2l3m4n5o6` | `porterchain_users` |
| `k2l3m4n5o6p7` | `user_invitations` |

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

_Violations: bypassing invitation for merchant/driver/admin provisioning is a security defect per masterrule §15._
