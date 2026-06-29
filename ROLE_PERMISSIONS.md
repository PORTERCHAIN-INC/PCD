# Porterchain — Role Permissions

**Document version:** 1.0  
**Date:** June 29, 2026

---

## Identity providers

| Surface                    | Provider                    | Identity type           |
| -------------------------- | --------------------------- | ----------------------- |
| Website (retail dashboard) | Clerk                       | `customer`              |
| Merchant portal            | Clerk Organizations         | `merchant_user`         |
| Admin (Porterchain ops)    | Clerk                       | `admin_user`            |
| Driver app                 | Porterchain JWT             | `driver`                |
| Merchant API               | API key + optional OAuth    | `integration`           |
| Fleetbase console          | Fleetbase session / API key | `dispatcher` (ops only) |

---

## Role hierarchy

### Porterchain platform roles (admin)

| Role            | Description                            |
| --------------- | -------------------------------------- |
| `super_admin`   | Full system access                     |
| `admin`         | Operations leadership                  |
| `dispatcher`    | Dispatch + fleet assignment            |
| `support`       | Tickets, exceptions, refunds (limited) |
| `support_lead`  | Refunds, claims, escalations           |
| `sales`         | CRM, leads, merchant approval initiate |
| `sales_manager` | Approve merchant + pricing overrides   |
| `finance`       | Invoices, payouts, refunds, reports    |
| `compliance`    | Merchant/driver document review        |
| `developer`     | API keys, webhooks, sandbox            |
| `marketing`     | Campaigns, abandoned checkout (read)   |
| `read_only`     | Audit / reporting view                 |

### Merchant organization roles

| Role                | Description                   |
| ------------------- | ----------------------------- |
| `merchant_owner`    | Full merchant account         |
| `merchant_admin`    | Users, settings, billing view |
| `merchant_ops`      | Book, track, CSV, API         |
| `merchant_finance`  | Invoices, statements, pay     |
| `merchant_readonly` | Track + reports only          |

### Driver role

| Role     | Description                              |
| -------- | ---------------------------------------- |
| `driver` | App execution only; own jobs + documents |

### Customer role

| Role       | Description                 |
| ---------- | --------------------------- |
| `customer` | Own orders, profile, rebook |

---

## Permission matrix — admin modules

| Module      | super_admin | admin | dispatcher | support | support_lead | sales | finance | compliance |
| ----------- | :---------: | :---: | :--------: | :-----: | :----------: | :---: | :-----: | :--------: |
| Dashboard   |      ✓      |   ✓   |     ✓      |    ✓    |      ✓       |   ✓   |    ✓    |     ✓      |
| CRM / Leads |      ✓      |   ✓   |     —      |    R    |      R       |   ✓   |    —    |     —      |
| Quotes      |      ✓      |   ✓   |     R      |    R    |      R       |   ✓   |    —    |     —      |
| Bookings    |      ✓      |   ✓   |     ✓      |    ✓    |      ✓       |   R   |    R    |     —      |
| Merchants   |      ✓      |   ✓   |     R      |    R    |      R       |   ✓   |    R    |     ✓      |
| Drivers     |      ✓      |   ✓   |     ✓      |    R    |      R       |   —   |    —    |     ✓      |
| Vehicles    |      ✓      |   ✓   |     ✓      |    —    |      —       |   —   |    —    |     ✓      |
| Dispatch    |      ✓      |   ✓   |     ✓      |    R    |      R       |   —   |    —    |     —      |
| Fleet       |      ✓      |   ✓   |     ✓      |    —    |      —       |   —   |    —    |     R      |
| Orders      |      ✓      |   ✓   |     ✓      |    ✓    |      ✓       |   R   |    R    |     R      |
| Tracking    |      ✓      |   ✓   |     ✓      |    ✓    |      ✓       |   —   |    —    |     —      |
| Pricing     |      ✓      |   ✓   |     R      |    —    |      —       |   R   |    —    |     —      |
| Invoices    |      ✓      |   ✓   |     —      |    R    |      R       |   —   |    ✓    |     —      |
| Billing     |      ✓      |   ✓   |     —      |    —    |      R       |   —   |    ✓    |     —      |
| Claims      |      ✓      |   ✓   |     R      |    R    |      ✓       |   —   |    ✓    |     —      |
| Support     |      ✓      |   ✓   |     ✓      |    ✓    |      ✓       |   —   |    —    |     —      |
| Marketing   |      ✓      |   ✓   |     —      |    —    |      —       |   ✓   |    —    |     —      |
| Contracts   |      ✓      |   ✓   |     —      |    —    |      —       |   ✓   |    R    |     ✓      |
| Reports     |      ✓      |   ✓   |     ✓      |    R    |      ✓       |   ✓   |    ✓    |     ✓      |
| Settings    |      ✓      |   ✓   |     —      |    —    |      —       |   —   |    —    |     —      |
| Developers  |      ✓      |   ✓   |     —      |    —    |      —       |   —   |    —    |     —      |

**Legend:** ✓ full · R read-only · — no access

---

## Permission matrix — merchant portal

| Module          | owner | admin | ops | finance | readonly |
| --------------- | :---: | :---: | :-: | :-----: | :------: |
| Dashboard       |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| Book Delivery   |   ✓   |   ✓   |  ✓  |    —    |    —     |
| CSV Upload      |   ✓   |   ✓   |  ✓  |    —    |    —     |
| API keys        |   ✓   |   ✓   |  —  |    —    |    —     |
| Orders          |   ✓   |   ✓   |  ✓  |    R    |    ✓     |
| Tracking        |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| Recipients      |   ✓   |   ✓   |  ✓  |    —    |    R     |
| Saved Addresses |   ✓   |   ✓   |  ✓  |    —    |    R     |
| Invoices        |   ✓   |   ✓   |  R  |    ✓    |    R     |
| Statements      |   ✓   |   ✓   |  —  |    ✓    |    R     |
| Reports         |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |
| Billing / pay   |   ✓   |   ✓   |  —  |    ✓    |    —     |
| Users           |   ✓   |   ✓   |  —  |    —    |    —     |
| Settings        |   ✓   |   ✓   |  R  |    R    |    —     |
| Support         |   ✓   |   ✓   |  ✓  |    ✓    |    ✓     |

---

## Permission matrix — driver app

| Action                       | driver |
| ---------------------------- | :----: |
| View assigned jobs           |   ✓    |
| Accept / reject job          |   ✓    |
| Update location              |   ✓    |
| Pickup / deliver / exception |   ✓    |
| Upload POD                   |   ✓    |
| View own wallet / payouts    |   ✓    |
| Upload own documents         |   ✓    |
| View other drivers' jobs     |   —    |
| Change pricing               |   —    |
| Cancel order (unilateral)    |   —    |

---

## Permission matrix — customer dashboard

| Action                       | customer |
| ---------------------------- | :------: |
| View own orders              |    ✓     |
| Track active shipment        |    ✓     |
| Download invoice             |    ✓     |
| Rebook                       |    ✓     |
| Edit profile (Clerk)         |    ✓     |
| Cancel order (policy window) |    ✓     |
| View other customers' data   |    —     |

---

## Fleetbase console access

| User                                 | Access                                  |
| ------------------------------------ | --------------------------------------- |
| `dispatcher`, `admin`, `super_admin` | Full Fleetbase console                  |
| `support`                            | Read-only map + order status (optional) |
| Merchants, customers, drivers        | **No access**                           |

Fleetbase uses `PORTERCHAIN_DISPATCHER_API_KEY` or Sanctum token for bridge automation.

---

## Data scope rules

| Role         | Data scope                                       |
| ------------ | ------------------------------------------------ |
| `customer`   | `customer_id = self`                             |
| `merchant_*` | `merchant_id = org`                              |
| `driver`     | `driver_id = self`                               |
| `sales`      | Leads + merchants in territory (optional)        |
| `support`    | Order lookup by reference; PII masked for tier-1 |
| `finance`    | All billing entities; no dispatch write          |

---

## Clerk organization mapping

```
Clerk User
  ├── publicMetadata.role = customer | admin_user | ...
  └── organizationMemberships[]
        └── merchant org → merchant_owner | merchant_ops | ...
```

Porterchain API validates JWT on every request; enforces RBAC server-side (never client-only).

---

## API key scopes (merchant integrations)

| Scope             | Allows            |
| ----------------- | ----------------- |
| `shipments:read`  | GET shipments     |
| `shipments:write` | Create shipments  |
| `tracking:read`   | Tracking events   |
| `webhooks:manage` | Register webhooks |
| `invoices:read`   | Billing read      |

---

## Audit requirements

| Action                     | Logged |
| -------------------------- | ------ |
| Role assignment            | ✓      |
| Refund approval            | ✓      |
| Merchant ACTIVE toggle     | ✓      |
| Pricing override           | ✓      |
| API key create/revoke      | ✓      |
| Dispatcher assign override | ✓      |

---

## Related documents

- [MODULE_BREAKDOWN.md](./MODULE_BREAKDOWN.md)
- [AUTHENTICATION.md](./AUTHENTICATION.md)
- [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md)
