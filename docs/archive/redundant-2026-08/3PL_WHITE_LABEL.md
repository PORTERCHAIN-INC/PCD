# 3PL white-label (§9.2.2)

**Checklist:** §9.2.2  
**Status:** Dev MVP — merchant branding on tracking + portal surfaces

## Capability

3PL partners and enterprise merchants can white-label customer-facing tracking without a separate courier brand:

- **Logo + colors** — `PATCH /v1/merchant/settings/branding`
- **Tracking message** — custom copy on public track page
- **Optional tracking domain** — CNAME to Porterchain track host (prod DNS step deferred)

## API fields

| Field                            | Purpose                                          |
| -------------------------------- | ------------------------------------------------ |
| `logo_url`                       | HTTPS logo on track page + emails                |
| `primary_color` / `accent_color` | CSS tokens for embedded track widget             |
| `tracking_page_message`          | Footer / hero message on `/track/{id}`           |
| `tracking_domain`                | Planned custom domain (e.g. `track.partner.com`) |
| `white_label_enabled`            | Feature flag for ops reporting                   |

## Reporting

- `GET /v1/admin/monopoly-metrics` → `white_label` adoption block
- Merchant settings overview includes current branding bucket

## Boundaries

- Drivers remain Porterchain-vetted ICs (see [CARRIER_POOL_MODEL.md](./legal/CARRIER_POOL_MODEL.md))
- White-label is **merchant→customer** UX only; dispatch execution stays on Porterchain + Fleetbase adapter
