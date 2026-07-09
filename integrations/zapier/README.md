# Zapier templates (§7.2.4)

**Checklist:** §7.2.4  
**Status:** Published template catalog — merchants import via Zapier + Porterchain API keys

## Templates

Canonical definitions live in [`templates.json`](./templates.json). The merchant API exposes them at:

`GET /v1/merchant/integrations/zapier/templates`

## Included zaps (MVP)

| ID                         | Trigger                                      | Action                                         |
| -------------------------- | -------------------------------------------- | ---------------------------------------------- |
| `new-shipment-webhook`     | Webhooks by Zapier catch hook                | POST `/v1/merchant-api/bookings`               |
| `delivered-slack`          | Porterchain webhook `order.delivered`        | Slack channel message                          |
| `netsuite-row-to-shipment` | Google Sheets / NetSuite row                 | POST `/v1/merchant/integrations/netsuite/sync` |
| `tracking-email`           | Porterchain webhook `order.tracking_updated` | Gmail send                                     |

## Merchant setup

1. Create a Porterchain API key (`shipments:read`, `shipments:write`).
2. In Zapier, use **Webhooks by Zapier** for inbound triggers.
3. For outbound events, register a Porterchain webhook in **Integrations → Webhooks**.
4. Copy the HMAC signing secret from the portal — Zapier **Webhooks** action can verify signatures.

See [PARTNER_GUIDE.md](../../docs/api/PARTNER_GUIDE.md) for authentication.
