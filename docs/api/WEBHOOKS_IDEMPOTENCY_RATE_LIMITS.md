# Partner API — webhooks, idempotency, and rate limits

**Type:** CANONICAL (developer authority)  
**Related:** [PARTNER_GUIDE.md](./PARTNER_GUIDE.md) · [CHANGELOG.md](./CHANGELOG.md) · OpenAPI live at `/docs`

## Webhooks

Outbound webhooks notify partner systems when order status changes (e.g. booked, in transit, delivered, exception).

| Topic        | Guidance                                                              |
| ------------ | --------------------------------------------------------------------- |
| Delivery     | HMAC-signed payloads from merchant webhook settings                   |
| Verification | Validate signature before processing; reject unsigned or stale events |
| Retries      | Treat deliveries as at-least-once — make handlers idempotent          |
| Secrets      | Rotate webhook secrets via merchant settings; never log raw secrets   |

Machine-readable integration bundle (scopes + webhook HMAC notes):  
`GET /v1/merchant/integrations/documentation` (Clerk merchant session).

## Idempotency

| Surface                           | Behavior                                                            |
| --------------------------------- | ------------------------------------------------------------------- |
| Partner bookings                  | Prefer client-supplied idempotency keys where documented in OpenAPI |
| Stripe webhooks                   | Server-side idempotency table prevents double-processing            |
| Partner webhooks (inbound to you) | Deduplicate by event id / delivery id before side effects           |

Do not assume at-most-once delivery. Design handlers so duplicate events are safe.

## Rate limits

| Environment            | Expectation                                                  |
| ---------------------- | ------------------------------------------------------------ |
| Production partner API | Rate limits enforced per API key; HTTP **429** when exceeded |
| Sandbox / local        | Soft limits; do not load-test production                     |

When limited:

1. Back off with jitter (exponential)
2. Reduce burst concurrency
3. Prefer batch-friendly workflows (CSV/recurring) over chatty polling

Exact numeric limits may change — check OpenAPI descriptions and `Retry-After` when present.

## Status and health

| Endpoint      | Purpose  |
| ------------- | -------- |
| `GET /health` | Liveness |

Public marketing status UI (`status.porterchain.com`) is Phase 2. Until then, use health endpoints and ops escalation via contact.

## SDK guidance

| Language          | Status                                                        |
| ----------------- | ------------------------------------------------------------- |
| Official SDKs     | Not required for Phase 1 — use OpenAPI + Postman              |
| Generated clients | Generate from `docs/api/openapi.json` or live `/openapi.json` |
| Recommended       | OpenAPI Generator / Speakeasy / hand-rolled thin client       |

Keep SDK versions aligned with CHANGELOG breaking-change windows (30-day notice).

## Sandbox checklist

1. Create a merchant API key with least-privilege scopes
2. Call quote → booking → track against local or staging base URL
3. Configure a webhook receiver and verify HMAC
4. Confirm 429 backoff behavior under burst traffic
5. Review [CHANGELOG.md](./CHANGELOG.md) before production cutover
