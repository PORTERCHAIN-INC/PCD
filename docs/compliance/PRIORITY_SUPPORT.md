# Priority support tier (§11.3.3)

**Type:** CANONICAL  
**Checklist:** §11.3.3  
**Last verified:** 2026-07-09

## Tiers

| Tier           | First response | Channels                  | Eligibility                 |
| -------------- | -------------- | ------------------------- | --------------------------- |
| **standard**   | <24h business  | Email, in-app ticket      | All merchants (default)     |
| **priority**   | <4h business   | + dedicated Slack Connect | ≥$50k ARR or admin approval |
| **enterprise** | <1h business   | + named CSM, phone bridge | Enterprise contract + SAML  |

## Configuration

Admin sets tier on merchant record:

```http
PATCH /v1/admin/merchants/{id}
{ "support_tier": "priority" }
```

Stored in `merchant.profile.enterprise.support_tier`. Visible in Merchant 360 detail.

## API behavior

- `POST /v1/merchant/support/tickets` — tags ticket with merchant tier for ops queue sort
- Admin support dashboard surfaces tier badge (portal UI Phase 2)
- SLA clock starts at ticket creation; business hours **Mon–Fri 9am–6pm ET**

## Related

- [SLA.md](./SLA.md)
- `support_engine/support_service.py`
