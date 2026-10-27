# Shopify admin control plane (ops)

PorterChain capacity for Shopify is gated by admin — not by rebuilding Shopify Admin.

## Per shop (Merchant → Integrations)

| Control           | Meaning                                                     |
| ----------------- | ----------------------------------------------------------- |
| Pause ingress     | Accept webhooks; do not book capacity                       |
| Booking policy    | Default vehicle + package (else cargoVan / looseParcel)     |
| Re-register hooks | Re-push Shopify webhooks + CarrierService (+ FO if flag on) |
| Ingress DLQ       | Failed/held books with reason codes; **Replay** after fix   |
| Force-disconnect  | Nuclear — clears token (elevated roles)                     |

New shops default to **auto_dispatch=false** (hold for ops) until onboarding is green.

## Order 360 (Shopify source)

- Fulfillment id / last push / last error
- **Re-push fulfillment** when tracking sync fails

## Control Tower → Attention

Open Shopify ingress DLQ rows and fulfillment errors appear in the exception center (`shopify.ingress.*`, `shopify.fulfillment.*`). Resolve discards DLQ / clears fulfillment error. Replay and re-push stay on merchant Integrations / Order 360.
