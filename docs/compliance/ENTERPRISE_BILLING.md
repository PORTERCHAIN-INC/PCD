# Enterprise billing terms (§11.2.4)

**Type:** CANONICAL  
**Checklist:** §11.2.4  
**Last verified:** 2026-07-09

## Supported payment terms

| Code        | Description                                          |
| ----------- | ---------------------------------------------------- |
| `IMMEDIATE` | Pay per booking (Stripe checkout)                    |
| `NET_7`     | Invoice due 7 days                                   |
| `NET_15`    | Invoice due 15 days                                  |
| `NET_30`    | Invoice due 30 days (default for approved merchants) |
| `NET_45`    | Enterprise approval required                         |
| `NET_60`    | Enterprise approval required                         |

## Admin API

```http
PATCH /v1/admin/merchants/{merchant_id}
Content-Type: application/json

{
  "payment_terms": "NET_30",
  "credit_limit_cents": 5000000
}
```

Default on merchant creation: **NET_30** (`admin_engine/merchant_service.py`).

## Merchant visibility

- Settings overview shows current terms (read-only for non-admin roles)
- Booking flow displays terms on quote preview
- Compliance dossier PDF includes payment terms

## Billing cycle

`billing_cycle` on Merchant: `MONTHLY` (default) or `WEEKLY` for high-volume accounts.

## Related

- `merchant_models.Merchant.payment_terms`
- Stripe invoicing (frozen — do not change webhook config)
