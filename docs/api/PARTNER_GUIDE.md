# Partner API guide

**Type:** CANONICAL  
**Checklist:** §7.1 · §0.6.7 · E.4  
**OpenAPI:** `/docs` on API (`http://localhost:8001/docs` local)

## Base URL

| Environment | URL                           |
| ----------- | ----------------------------- |
| Local       | `http://localhost:8001`       |
| Production  | `https://api.porterchain.com` |

## Authentication

- **Merchant portal:** Clerk JWT on `/v1/merchant/*` (organization context via `X-Merchant-Org-Id`)
- **Partner integrations:** API key on `/v1/merchant-api/*` — header `X-Api-Key`, scoped permissions
- **Partner webhooks:** HMAC-signed outbound from merchant settings

## Merchant API scopes (`/v1/merchant-api/*`)

Phase 1 exposes two scopes. Each API key stores a subset; routes call `require_scope()` and return **403** `api_key_missing_scope:{scope}` when missing.

| Scope             | Grants                                                            |
| ----------------- | ----------------------------------------------------------------- |
| `shipments:read`  | `GET /orders`, `GET /orders/{id}`, `GET /track/{tracking_number}` |
| `shipments:write` | `POST /bookings`, `POST /orders/{order_id}/cancel`                |

New keys default to **both** scopes. Trim scopes per integration (read-only trackers vs full booking).

Machine-readable bundle (includes scope map + webhook HMAC): `GET /v1/merchant/integrations/documentation` (Clerk merchant session).

## Core endpoints (Phase 1)

| Flow            | Method | Path                                 |
| --------------- | ------ | ------------------------------------ |
| Quote           | POST   | `/v1/quotes`                         |
| Booking draft   | POST   | `/v1/booking-drafts`                 |
| Create booking  | POST   | `/v1/bookings`                       |
| Track (public)  | GET    | `/v1/orders/{tracking_number}/track` |
| Merchant orders | GET    | `/v1/merchant/orders`                |

## Versioning

See [CHANGELOG.md](./CHANGELOG.md). Breaking changes require ADR + 30-day notice.

## Postman

- **Collection:** [`porterchain.postman.json`](./porterchain.postman.json) — import into Postman (v2.1). Folders cover the Phase 1 core loop (quote → booking → track → POD) plus merchant, driver, admin ops, and webhooks.
- **OpenAPI snapshot:** [`openapi.json`](./openapi.json) — regenerate with `pnpm docs:openapi`. Live truth stays at `{{base_url}}/openapi.json` and `/docs`.

Set collection variables before running:

| Variable   | Purpose                                                     | Local default           |
| ---------- | ----------------------------------------------------------- | ----------------------- |
| `base_url` | API host                                                    | `http://localhost:8001` |
| `token`    | Clerk JWT (Bearer). With `CLERK_DEV_BYPASS=true`, use `dev` | `dev`                   |
| `api_key`  | Partner `X-Api-Key` for `/v1/merchant-api/*`                | _(set per key)_         |
