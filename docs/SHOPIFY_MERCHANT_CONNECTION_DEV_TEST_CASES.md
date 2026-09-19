# Shopify ↔ Merchant ↔ Fleetbase ↔ PorterChain — development test cases

**Status:** living catalog for local/CI development (not prod Doppler / Partners sandbox E2E).  
**Mapped:** 2026-09-17 via Graphify → CodeGraph CLI `explore` → Ripwire (`--for` / `--expand` / `--callers` / `--impact`).  
**Architecture SSOT:** [ARCHITECTURE.md](../ARCHITECTURE.md) · charter: capacity network, not a courier SKU.  
**Adjacent matrices:** [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md) (portal-wide) · [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md) (carrier distance ≠ VROOM) · intentional skips: [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) § Shopify Quote≡Book.

### Sensor trail (this pass)

| Moment | Tool          | What it named                                                                                                                                                                                                                                     |
| ------ | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A      | Graphify      | `shopify_service.py`, `routers/merchant/shopify.py`, `routers/shopify.py`, `Shopify HMAC`, `BookingSyncService`, `FleetbaseClient`, `WebhookProcessor`, god nodes `Merchant` / `MerchantContext` / `Order`                                        |
| B      | CodeGraph CLI | `ShopifyShop` ORM · `ShopifyConnectRequest` · `carrier_service_rates` → HMAC + rate card · `resolve_route_distance` → `MapsService` Valhalla/OSRM · blast: `merchant360_board`, `test_shopify_*`                                                  |
| C      | Ripwire       | Worker `process_webhook` → `_shopify_ingress` / `_shopify_fulfillment` · `connect_custom_app` · `push_fulfillment` callers · `ingest_webhook` impact · UI `ShopifyConnectCard` / `ShopifyAppClient` · `ERP_READINESS` · NetSuite adapter neighbor |

**Pipeline (dev):**

```
Shopify Admin / Checkout / Webhooks
        │ HMAC + OAuth
   FastAPI :8001  /v1/integrations/shopify/*  +  /v1/merchant/shopify*
        │
   merchant_engine/shopify_service  +  integrations/shopify_*
        │ book / cancel / quote
   booking_engine + pricing_engine + MapsService (Valhalla→OSRM)
        │ DomainEvent + RetryQueue
   fleetbase_engine → FleetbaseAdapter :8000 (+ VROOM behind Fleetbase only)
        │
   worker webhooks.py  ↔  EventBus shopify_fulfillment
        │
   merchant :3001 /shopify + /api   ·   admin :3002 merchants/[id] Shopify card
```

---

## 0. ID scheme & layers

| Prefix    | Layer                                                                 |
| --------- | --------------------------------------------------------------------- |
| `M-UI-*`  | Merchant portal pages / Shopify UX `:3001`                            |
| `A-UI-*`  | Admin Merchant 360 / settings / diagnostics `:3002`                   |
| `API-M-*` | Authenticated `/v1/merchant/shopify*` (+ integrations neighbors)      |
| `API-S-*` | Public `/v1/integrations/shopify/*`                                   |
| `API-P-*` | Partner `/v1/merchant-api/*` (ERP substitute path)                    |
| `ENG-*`   | `shopify_service`, carrier rates, order map, booking                  |
| `MAP-*`   | MapsService Valhalla → OSRM (carrier + book geocode)                  |
| `FB-*`    | Fleetbase adapter + booking/merchant sync + RetryQueue                |
| `VRM-*`   | VROOM **only** via Fleetbase orchestrator (negative for Shopify path) |
| `AUTH-*`  | Clerk merchant session / `require_module("api_keys")` / OAuth state   |
| `SEC-*`   | HMAC, secrets encryption, rate limits, hijack blocks                  |
| `EVT-*`   | EventBus / DomainEventType / fulfillment fan-out                      |
| `WRK-*`   | Worker `processors/webhooks.py` ingress + fulfillment                 |
| `NOTIF-*` | Email (Mailpit) / FCM / merchant realtime WS / admin push             |
| `BILL-*`  | Quote≡Book · `ShopifyRateQuote` · AR channel · COD capture            |
| `DB-*`    | `ShopifyShop` · `ShopifyRateQuote` · Order source SHOPIFY             |
| `DOC-*`   | Docker / tunnel / compose / env pins                                  |
| `ARCH-*`  | Ownership laws · no Fleetbase from browser · no Google routing        |
| `ERP-*`   | NetSuite / WooCommerce / custom ERP readiness (mostly _not_offered_)  |
| `DIAG-*`  | Readiness · Prometheus commerce metrics · e2e validation              |
| `UX-*`    | Copy, empty states, confirm dialogs, embedded app flow                |
| `NEG-*`   | Explicit non-goals / intentional skips as automated guards            |

**Priority:** P0 = ship-blocker · P1 = trust/money/utilization · P2 = polish/regression · P3 = chaos/soak/future.

Each case: **Precondition → Steps → Expected → Layer tags**.

---

## 1. Surface inventory (SSOT for every page / file)

### 1.1 Merchant portal (`apps/merchant-portal`)

| Surface              | Route / file                                                                                       | Shopify role                                                   |
| -------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Shopify app home** | `/shopify` · `app/(portal)/shopify/page.tsx` · `ShopifyAppClient.tsx`                              | Embedded/partner return; Clerk gate; `?shop=` / `?connected=1` |
| **Integrations hub** | `/api` · `IntegrationsClient.tsx` · embeds `ShopifyConnectCard`                                    | Connect OAuth + custom Admin API token                         |
| Connect card         | `components/integrations/ShopifyConnectCard.tsx`                                                   | GET/POST/PUT/DELETE shopify; pickup select; disconnect confirm |
| Client types/API     | `lib/integrations.ts` (`ShopifyConnection`, `shopify*`)                                            | Contract with `/v1/merchant/shopify*`                          |
| Route import parse   | `lib/route-module/shopifyParser.ts` · `types.ts` (`ShopifyParseSuccess`, `ShopifyFulfillmentPush`) | CSV/bulk adjacent to Shopify feeds                             |
| Settings / locations | `/settings` (linked from Shopify page)                                                             | Default pickup `SavedAddress` prerequisite                     |
| Orders               | `/orders`                                                                                          | Source=SHOPIFY rows appear after webhook book                  |
| Book / bulk / routes | `/book`, `/bulk`, `/routes`                                                                        | Manual capacity vs Shopify-ingested                            |
| Billing              | `/billing`                                                                                         | Channel spend / invoice lines with `shopify`                   |
| Notifications        | `/notifications`                                                                                   | Prefs for booking/fulfillment alerts                           |
| Team                 | `/team`                                                                                            | `api_keys` module RBAC for connect                             |
| Auth                 | Clerk sign-in → redirect `/shopify?shop=`                                                          | Install without session                                        |
| Realtime             | `hooks/useMerchantRealtime.ts`                                                                     | Refresh after Shopify book events                              |
| Headers              | `next.config.ts` Shopify embed headers                                                             | iframe / CSP for App Bridge hosts                              |
| Verify script        | `scripts/verify_integration_marketplace.py` (`SHOPIFY_APP`)                                        | Marketplace file presence                                      |

### 1.2 Admin portal (`apps/admin`)

| Surface               | File                                                  | Shopify role                                           |
| --------------------- | ----------------------------------------------------- | ------------------------------------------------------ |
| Merchant 360          | `app/(ops)/merchants/[id]/page.tsx` · section Shopify | Read-only shop list; **no mint** (merchant creates)    |
| Client types          | `lib/merchants.ts` `shopify_shops?`                   | Board payload                                          |
| Board compose         | `admin_engine/merchant360_board.py`                   | Queries `ShopifyShop`                                  |
| Orders                | `lib/orders.ts` `shopifyAdminUrl`                     | Deep-link to Shopify Admin                             |
| Integrations settings | `IntegrationPanel.tsx`                                | Platform Shopify env readiness (not merchant install)  |
| Diagnostics           | `SystemCenter` / readiness                            | Fleetbase + Firebase + routing + clerk                 |
| Operations            | `/operations`                                         | Post-book Fleetbase sync / dispatch (not Shopify HTTP) |
| Finance               | `/finance`                                            | AR channel attribution for Shopify                     |

### 1.3 FastAPI thin routers

| Family                | File                               | Handlers                                                                     |
| --------------------- | ---------------------------------- | ---------------------------------------------------------------------------- |
| Merchant Shopify      | `routers/merchant/shopify.py`      | `GET/POST /shopify`, `GET install-url`, `PUT …/pickup`, `DELETE …/{shop_id}` |
| Public Shopify        | `routers/shopify.py`               | `GET install`, `GET callback`, `POST webhooks`, `POST carrier-service/rates` |
| Merchant integrations | `routers/merchant/integrations.py` | ERP list, OAuth providers, webhooks, sandbox (neighbors)                     |
| OAuth (PorterChain)   | `routers/oauth.py`                 | Partner OAuth — **not** Shopify App OAuth (separate)                         |
| Admin merchants       | `routers/merchants.py`             | 360 payload includes shops; revoke/disable only                              |

### 1.4 Engines / integrations / models

| Module              | Path                                                                               | Responsibility                                                              |
| ------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Shopify service     | `merchant_engine/shopify_service.py`                                               | Connect, OAuth, ingest, book/cancel, fulfillment, carrier register, secrets |
| Carrier rates       | `integrations/shopify_carrier_rates.py`                                            | HMAC → quote → `ShopifyRateQuote` persist · Quote≡Book                      |
| Order map           | `integrations/shopify_orders.py`                                                   | Payload → addresses/ids/weight                                              |
| HMAC                | `integrations/shopify_hmac.py`                                                     | Webhook + OAuth query HMAC                                                  |
| Booking             | `merchant_engine/booking_service.py`                                               | Creates Order from Shopify book                                             |
| Activation          | `merchant_engine/activation_service.py`                                            | `SIGNUP_SOURCE_SHOPIFY` policy                                              |
| Secrets             | `merchant_engine/secrets.py`                                                       | Encrypt/decrypt tokens                                                      |
| Geocode             | `merchant_engine/import_geocode.py`                                                | Nominatim/Google Places fallback for coords                                 |
| Service area        | `merchant_engine/service_area.py`                                                  | Ontario / GTA gate                                                          |
| Fleetbase book sync | `fleetbase_engine/booking_sync_service.py`                                         | Order → Fleetbase                                                           |
| Merchant sync       | `fleetbase_engine/merchant_sync_service.py`                                        | Profile mirror; `BookingValidationError`                                    |
| Webhook processor   | `fleetbase_engine/webhook_processor.py`                                            | Fleetbase → PC status (downstream of Shopify book)                          |
| Retry queue         | `fleetbase_engine/retry_queue.py`                                                  | Adapter blips                                                               |
| Status translator   | `fleetbase_engine/status_translator.py`                                            | FB status → PC                                                              |
| Tracking façade     | `fleetbase_engine/tracking_facade.py`                                              | Tracking for fulfillment push                                               |
| Stripe COD          | `merchant_engine` `capture_cod_transaction`                                        | Optional COD after delivery                                                 |
| ORM                 | `merchant_models.py`                                                               | `ShopifyShop`, `ShopifyRateQuote`                                           |
| Schemas             | `schemas_merchant.py`                                                              | `ShopifyConnectRequest`, `ShopifyPickupRequest`                             |
| Domain              | `domain/states.py`                                                                 | `OrderSource.SHOPIFY`                                                       |
| Gateway ERP         | `gateway_engine/merchant_api.py`                                                   | `ERP_READINESS`, `OAUTH_PROVIDERS`, channel map                             |
| NetSuite adapter    | `integrations/netsuite_adapter.py`                                                 | **not_offered** neighbor                                                    |
| Base adapter        | `integrations/base_adapter.py`                                                     | Pattern for future ERPs                                                     |
| Migrations          | `alembic/.../l4m5n6o7p8q9_shopify_shops.py`, `b0c1d2e3f4a5_shopify_rate_quotes.py` | Schema                                                                      |

### 1.5 Worker / EventBus / notifications

| Surface           | File                                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| Webhook processor | `apps/worker/processors/webhooks.py` — `shopify_orders_create` / `cancelled` / `shopify_fulfillment` |
| EventBus handler  | `services/event-bus/.../handlers` `_handle_shopify_fulfillment`                                      |
| Event catalog     | `shared/python/porterchain_shared/events/catalog.py`                                                 |
| Merchant fanout   | `merchant_engine/webhook_delivery_service.py`                                                        |
| Preference sync   | `notification_engine/preference_service.py`                                                          |
| FCM / email       | `services/python/.../notifications/service.py` · Mailpit in compose                                  |
| Admin WS          | `useAdminNotificationRealtime.ts`                                                                    |
| Merchant WS       | `useMerchantRealtime.ts`                                                                             |

### 1.6 Spatial / Fleetbase / Docker

| Box               | Role for Shopify                                                                     |
| ----------------- | ------------------------------------------------------------------------------------ |
| Valhalla `:8002`  | Primary road distance for carrier + book pricing                                     |
| OSRM `:5000`      | Fallback ETA/distance                                                                |
| Google            | Places/geocode assist only — **never** Distance Matrix for rates                     |
| Fleetbase `:8000` | Dispatch SoT after book; VROOM behind adapter                                        |
| VROOM             | Optimize multi-stop **after** Shopify order is a PC+FB job — not in carrier callback |
| Redis             | Shopify rate-limit buckets; OAuth state TTL; EventBus                                |
| Postgres 18       | `shopify_shops`, `shopify_rate_quotes`, orders                                       |
| Tunnel            | `scripts/shopify-dev-tunnel.sh` for local webhook/carrier                            |

### 1.7 Existing test seeds (extend, do not blindly duplicate)

| File                                        | Focus                                                       |
| ------------------------------------------- | ----------------------------------------------------------- |
| `test_shopify_ingest.py`                    | Domain normalize, HMAC, OAuth HMAC, order map               |
| `test_shopify_urls.py`                      | Partner app URLs + scopes include shipping                  |
| `test_shopify_phase4.py`                    | Ingest enqueue, 401/503/200 router, cancel, idempotent book |
| `test_shopify_carrier_rates_p44.py`         | Same-day rate shape                                         |
| `test_shopify_carrier_pricing_handshake.py` | Quote≡engine, HMAC reject, out-of-area, spoof shop          |
| `test_shopify_billing_wave_remaining.py`    | Install hijack blocks, invoice channel, Prometheus          |
| `test_merchant_integrations.py`             | Integrations hub neighbors                                  |
| `test_routing.py`                           | Valhalla/OSRM distance sources                              |

---

## 2. Merchant UI / UX cases

| ID       | P   | Kind     | Precondition → Steps → Expected                                                                                                  |
| -------- | --- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| M-UI-001 | P0  | e2e      | Signed-in merchant with `api_keys` → open `/api` → Shopify card loads `webhook_url` + `carrier_rates_url` + shops[]              |
| M-UI-002 | P0  | e2e      | OAuth configured → enter `shop.myshopify.com` → Install → redirects Shopify authorize → callback → `/shopify?connected=1` banner |
| M-UI-003 | P0  | e2e      | Custom app: shop + Admin API token + webhook secret + pickup → Connect → shop row `connected:true`, token fields cleared         |
| M-UI-004 | P0  | ui       | No saved addresses → Connect disabled / error `pickup_address_required` surfaced as human copy                                   |
| M-UI-005 | P0  | ui       | Change default pickup via select → `PUT …/pickup` → card shows new default                                                       |
| M-UI-006 | P0  | ui       | Disconnect confirm → DELETE 204 → shop uninstalled or removed from active list                                                   |
| M-UI-007 | P0  | e2e      | Unsigned `/shopify?shop=acme` → CTA Sign in with redirect back + optional public Install link                                    |
| M-UI-008 | P1  | ux       | Copy webhook URL control → clipboard feedback (`copied`)                                                                         |
| M-UI-009 | P1  | ux       | Invalid shop domain → inline error (not raw stack) via `integration_error_message`                                               |
| M-UI-010 | P1  | ui       | Links to `/settings` (locations) and `/api` (full integrations) from Shopify page                                                |
| M-UI-011 | P1  | ui       | Role without `api_keys` module → 403 / gate on connect actions                                                                   |
| M-UI-012 | P1  | e2e      | After webhook book → `/orders` shows order with Shopify source / external id                                                     |
| M-UI-013 | P2  | ux       | Embedded headers allow Shopify admin iframe host without CSP break                                                               |
| M-UI-014 | P2  | ui       | Sandbox banner + Shopify connect: sandbox preference does not dry-run CarrierService                                             |
| M-UI-015 | P2  | contract | `ShopifyConnection` TS type matches `connection_payload` keys                                                                    |
| M-UI-016 | P2  | ui       | `shopifyParser` on bulk import: valid Shopify export → parse success; bad CSV → actionable errors                                |
| M-UI-017 | P3  | a11y     | Connect form labels, confirm dialog keyboard, focus after error                                                                  |
| M-UI-018 | P1  | realtime | Merchant WS connected → Shopify book → board/orders refresh without full reload                                                  |

---

## 3. Admin UI cases

| ID       | P   | Kind     | Precondition → Steps → Expected                                                                  |
| -------- | --- | -------- | ------------------------------------------------------------------------------------------------ |
| A-UI-001 | P0  | e2e      | Merchant with 1 shop → Merchant 360 Shopify section lists domain + installed_at                  |
| A-UI-002 | P0  | security | Admin UI has **no** “Connect Shopify” mint control (merchant-owned)                              |
| A-UI-003 | P1  | ui       | Suspended merchant shops still visible read-only; ops cannot re-OAuth as merchant                |
| A-UI-004 | P1  | ui       | Order detail shows Shopify Admin deep-link when metadata present                                 |
| A-UI-005 | P1  | e2e      | Shopify-origin order appears on Operations board after Fleetbase sync                            |
| A-UI-006 | P1  | diag     | Integration / readiness shows Clerk + Fleetbase + Firebase + routing; Shopify secrets not leaked |
| A-UI-007 | P2  | finance  | Finance AR / spend by channel includes `shopify`                                                 |
| A-UI-008 | P2  | ui       | Suggestion copy “Offer API/Shopify…” only when volume low (360 board)                            |

---

## 4. Authenticated merchant API (`/v1/merchant/shopify*`)

| ID        | P   | Kind     | Endpoint / assert                                                                                       |
| --------- | --- | -------- | ------------------------------------------------------------------------------------------------------- |
| API-M-001 | P0  | api      | `GET /v1/merchant/shopify` — 200 payload: `oauth_configured`, urls, `shops[]`; Bearer + `X-Merchant-Id` |
| API-M-002 | P0  | api      | Missing auth → 401; wrong merchant id → 403/404 per portal guard                                        |
| API-M-003 | P0  | api      | `GET …/install-url?shop=` — returns Shopify authorize URL with signed state                             |
| API-M-004 | P0  | api      | install-url invalid domain → 400 `shop_domain_invalid`                                                  |
| API-M-005 | P0  | api      | `POST /shopify` custom connect — persists encrypted token; returns `connected_shop_id`                  |
| API-M-006 | P0  | api      | POST missing pickup → 400; pickup other merchant → 404                                                  |
| API-M-007 | P0  | api      | POST shop already bound to other merchant → 400 `shop_already_connected`                                |
| API-M-008 | P0  | api      | `PUT /shopify/{id}/pickup` — updates FK; wrong shop → 404                                               |
| API-M-009 | P0  | api      | `DELETE /shopify/{id}` — 204; idempotent second delete → 404                                            |
| API-M-010 | P0  | authz    | `require_module(ctx, "api_keys")` on all five handlers                                                  |
| API-M-011 | P1  | contract | Response never includes plaintext access token or webhook secret                                        |
| API-M-012 | P1  | api      | Reconnect same shop clears `uninstalled_at`, refreshes `installed_at`                                   |
| API-M-013 | P2  | api      | Integrations neighbors still work with Shopify connected (`/integrations/erp` lists shopify ready)      |

---

## 5. Public Shopify ingress (`/v1/integrations/shopify`)

| ID        | P   | Kind     | Endpoint / assert                                                                                               |
| --------- | --- | -------- | --------------------------------------------------------------------------------------------------------------- |
| API-S-001 | P0  | api      | `GET /install?shop=` → 302 to Shopify OAuth; optional `merchant_id` in state                                    |
| API-S-002 | P0  | api      | `GET /callback` valid HMAC+code → exchanges token → redirect `app_home_url`                                     |
| API-S-003 | P0  | security | callback bad HMAC → 400                                                                                         |
| API-S-004 | P0  | security | callback state merchant hijack blocked (`_merchant_for_install` tests)                                          |
| API-S-005 | P0  | api      | `POST /webhooks` orders/create valid HMAC → 200 `{queued:true}` (or ok) + worker enqueue                        |
| API-S-006 | P0  | security | webhooks bad HMAC → 401                                                                                         |
| API-S-007 | P0  | api      | enqueue failure → 503 so Shopify retries                                                                        |
| API-S-008 | P0  | api      | merchant inactive / BookingValidationError → structured `{ok:false,code}` (not 500)                             |
| API-S-009 | P0  | api      | orders/cancelled → enqueue cancel path                                                                          |
| API-S-010 | P0  | api      | `app/uninstalled` → marks shop uninstalled; tokens inert                                                        |
| API-S-011 | P0  | security | GDPR topics `customers/redact`, `shop/redact`, `customers/data_request` → acknowledged without PII leak in logs |
| API-S-012 | P0  | api      | `POST /carrier-service/rates` valid → `rates[]` with service name, price, currency CAD                          |
| API-S-013 | P0  | security | carrier missing/invalid HMAC → 401                                                                              |
| API-S-014 | P0  | api      | unknown shop after HMAC → 404                                                                                   |
| API-S-015 | P0  | api      | out-of-area / inactive / no pickup → empty `rates[]` (Shopify-compatible)                                       |
| API-S-016 | P0  | rate     | webhook > `SHOPIFY_WEBHOOK_RATE_LIMIT_PER_MINUTE` → 429 + headers                                               |
| API-S-017 | P0  | rate     | carrier > `SHOPIFY_CARRIER_RATE_LIMIT_PER_MINUTE` → 429                                                         |
| API-S-018 | P1  | chaos    | Redis down → rate limiter **fail-open** (HMAC still required)                                                   |
| API-S-019 | P1  | api      | invalid JSON body on carrier → 400 `invalid_json`                                                               |
| API-S-020 | P1  | contract | OpenAPI paths for all four public + five merchant Shopify ops present                                           |

---

## 6. Engine / booking / Quote≡Book

| ID      | P   | Kind      | Assert                                                                                            |
| ------- | --- | --------- | ------------------------------------------------------------------------------------------------- |
| ENG-001 | P0  | unit      | `normalize_shop_domain` / `is_shop_domain` edge cases (http prefix, bare name → `.myshopify.com`) |
| ENG-002 | P0  | unit      | `verify_webhook_hmac` / `verify_oauth_hmac` accept match, reject tamper                           |
| ENG-003 | P0  | unit      | `map_shopify_order` requires shipping address; copies postal + weight                             |
| ENG-004 | P0  | unit      | `_book_from_shopify_payload` creates Order `source=SHOPIFY`, external ids set                     |
| ENG-005 | P0  | unit      | book idempotent replay same Shopify order id → same PC order (no double book)                     |
| ENG-006 | P0  | unit      | `_cancel_from_shopify_payload` cancels when policy allows; skips missing order                    |
| ENG-007 | P0  | handshake | book uses default pickup SavedAddress + destination from Shopify                                  |
| ENG-008 | P0  | handshake | book price matches persisted `ShopifyRateQuote` for same `request_hash` (Quote≡Book)              |
| ENG-009 | P0  | unit      | `find_quote_for_book` expires stale quotes; refuses foreign shop                                  |
| ENG-010 | P0  | unit      | `connect_custom_app` encrypts token/secret; calls `_post_install_hooks`                           |
| ENG-011 | P0  | unit      | `_register_webhooks` registers create/cancel/uninstall/GDPR topics                                |
| ENG-012 | P0  | unit      | `_register_carrier_service` posts CarrierService callback URL                                     |
| ENG-013 | P1  | unit      | `_ensure_coords` geocodes when lat/lng missing                                                    |
| ENG-014 | P1  | unit      | service area reject outside Ontario/GTA policy                                                    |
| ENG-015 | P1  | unit      | `apply_signup_policy(..., SIGNUP_SOURCE_SHOPIFY)` on connect                                      |
| ENG-016 | P1  | unit      | `push_fulfillment` posts fulfillment_orders; stores `fulfillment_id` in meta                      |
| ENG-017 | P1  | unit      | `capture_cod_transaction` no-ops when not COD; captures when configured                           |
| ENG-018 | P1  | unit      | `process_queued_webhook` routes create vs cancel actions                                          |
| ENG-019 | P2  | unit      | `_actor` ensures merchant seat for system actor                                                   |
| ENG-020 | P2  | chaos     | Shopify Admin API 5xx during post-install → logged; shop still connected for retry                |

---

## 7. Maps / Valhalla / OSRM / Google (carrier + book)

| ID      | P   | Kind      | Assert                                                                           |
| ------- | --- | --------- | -------------------------------------------------------------------------------- |
| MAP-001 | P0  | handshake | Carrier quote distance source ∈ {valhalla, osrm} when routers up                 |
| MAP-002 | P0  | handshake | Valhalla down → OSRM fallback; metrics `note_routing_source`                     |
| MAP-003 | P0  | handshake | Both down → labeled haversine only; never invent ETA as distance/500             |
| MAP-004 | P0  | contract  | Carrier path never calls Google Distance Matrix / Directions                     |
| MAP-005 | P1  | unit      | Destination postal change changes quote (pricing_engine call)                    |
| MAP-006 | P1  | unit      | Two merchants different rate cards → different cents (handshake suite)           |
| MAP-007 | P1  | contract  | Google Places used only for incomplete address geocode assist                    |
| MAP-008 | P2  | chaos     | Public OSRM demo last-resort remains gated off by default                        |
| MAP-009 | P2  | contract  | `scripts/verify_no_ops_spatial_math.py` still bans hand-rolled matrix in engines |

---

## 8. Fleetbase + VROOM handshakes

| ID      | P   | Kind      | Assert                                                                                 |
| ------- | --- | --------- | -------------------------------------------------------------------------------------- |
| FB-001  | P0  | handshake | Shopify-booked Order enqueues Fleetbase booking sync                                   |
| FB-002  | P0  | handshake | Adapter creates/updates Fleetbase order; PC stores fleetbase ids                       |
| FB-003  | P0  | handshake | Adapter timeout → RetryQueue job; worker drains to success                             |
| FB-004  | P0  | handshake | Fleetbase status webhook → `WebhookProcessor` → PC OrderState advances                 |
| FB-005  | P0  | handshake | Tracking URL available for `push_fulfillment` notify_customer                          |
| FB-006  | P1  | handshake | Merchant profile fields mirrored via `merchant_sync_service` when required             |
| FB-007  | P1  | chaos     | Fleetbase 500 storm → queue depth visible in ops diagnostics; no portal→Fleetbase HTTP |
| FB-008  | P0  | contract  | Merchant/admin browsers never import SocketCluster or call Fleetbase URL               |
| VRM-001 | P0  | NEG       | Carrier callback does **not** import/call VROOM                                        |
| VRM-002 | P1  | handshake | Multi-stop optimize of Shopify-origin jobs only via Fleetbase orchestrator             |
| VRM-003 | P1  | contract  | No `*_engine` VROOM client (architecture census)                                       |

---

## 9. Clerk / auth / RBAC

| ID       | P   | Kind     | Assert                                                                               |
| -------- | --- | -------- | ------------------------------------------------------------------------------------ |
| AUTH-001 | P0  | e2e      | Clerk merchant session required for `/v1/merchant/shopify*`                          |
| AUTH-002 | P0  | e2e      | Dev bypass Bearer `dev` works locally only when `CLERK_DEV_BYPASS`                   |
| AUTH-003 | P0  | security | OAuth `state` signed + TTL; expired state rejected                                   |
| AUTH-004 | P0  | security | Install email cannot bind shop onto unrelated live merchant (hijack suite)           |
| AUTH-005 | P1  | authz    | Staff/admin Clerk cannot mint Shopify connect for merchant                           |
| AUTH-006 | P1  | e2e      | New Shopify install can create/activate merchant seat per signup policy              |
| AUTH-007 | P1  | contract | Portal uses `CLERK_MERCHANT_*` env names — never ad-hoc `ADMIN_CLERK_*` for merchant |

---

## 10. Security / secrets / rate limits

| ID      | P   | Kind     | Assert                                                                  |
| ------- | --- | -------- | ----------------------------------------------------------------------- |
| SEC-001 | P0  | security | Access token + webhook secret encrypted at rest (`encrypted_*` columns) |
| SEC-002 | P0  | security | Spoofed `X-Shopify-Shop-Domain` cannot use another shop’s secret        |
| SEC-003 | P0  | security | App secret alone insufficient without shop membership after HMAC        |
| SEC-004 | P0  | security | Shop-level webhook secret accepted when app secret absent (custom app)  |
| SEC-005 | P0  | security | Logs redact tokens; GDPR payloads not dumped raw                        |
| SEC-006 | P1  | security | Disconnect / uninstall stops Admin API calls (no token use)             |
| SEC-007 | P1  | rate     | Distinct Redis buckets `shopify_webhook` vs `shopify_carrier`           |
| SEC-008 | P2  | security | Timing-safe HMAC compare                                                |

---

## 11. Worker / EventBus / fulfillment loop

| ID      | P   | Kind      | Assert                                                                    |
| ------- | --- | --------- | ------------------------------------------------------------------------- |
| WRK-001 | P0  | handshake | `action=shopify_orders_create` → `process_queued_webhook` → book          |
| WRK-002 | P0  | handshake | `action=shopify_orders_cancelled` → cancel path                           |
| WRK-003 | P0  | handshake | `action=shopify_fulfillment` → `push_fulfillment`                         |
| WRK-004 | P0  | unit      | Missing `order_id` on fulfillment → warn, no crash                        |
| WRK-005 | P1  | handshake | EventBus `_handle_shopify_fulfillment` enqueues worker payload            |
| WRK-006 | P1  | chaos     | Worker exception rolls back DB session; job retryable                     |
| WRK-007 | P1  | EVT       | Domain events for book/cancel include channel/source shopify              |
| WRK-008 | P2  | unit      | Non-shopify webhook actions (`merchant_fanout`, `lead_ingest`) unaffected |

---

## 12. Notifications / email / Firebase / realtime

| ID        | P   | Kind      | Assert                                                                                                            |
| --------- | --- | --------- | ----------------------------------------------------------------------------------------------------------------- |
| NOTIF-001 | P0  | handshake | Merchant email prefs: new Shopify booking → Mailpit message in local                                              |
| NOTIF-002 | P1  | handshake | FCM device registered → optional push on book/delivered (feature-flagged)                                         |
| NOTIF-003 | P1  | handshake | Admin notification WS / bell receives ops-relevant Shopify volume events if configured                            |
| NOTIF-004 | P1  | unit      | `sync_merchant_portal_prefs` does not drop Shopify-related event keys                                             |
| NOTIF-005 | P1  | e2e       | Merchant realtime WS refresh after book                                                                           |
| NOTIF-006 | P2  | diag      | `firebase_sdk_available` / `firebase_production_ready` in readiness; Shopify path degrades gracefully if FCM down |
| NOTIF-007 | P2  | handshake | Invoice remind email Pay link still works for Shopify-channel invoices                                            |
| NOTIF-008 | P3  | chaos     | Mailpit down → booking still succeeds; delivery logged failed                                                     |

---

## 13. Billing / Stripe / channel attribution

| ID       | P   | Kind      | Assert                                                           |
| -------- | --- | --------- | ---------------------------------------------------------------- |
| BILL-001 | P0  | handshake | Checkout carrier cents ≡ book cents ≡ invoice line for same hash |
| BILL-002 | P0  | unit      | AR cycle creates `InvoiceLine` with channel `shopify`            |
| BILL-003 | P1  | api       | Merchant invoice GET exposes channel / pricing_model / quote id  |
| BILL-004 | P1  | handshake | Stripe Checkout / Connect pay settles Shopify-channel invoice    |
| BILL-005 | P1  | unit      | COD capture after delivery when Shopify order is COD             |
| BILL-006 | P1  | metrics   | Prometheus: `shopify_quote`, related commerce metrics increment  |
| BILL-007 | P2  | report    | Spend by channel / FSA                                           | distance bands include Shopify |
| BILL-008 | P2  | contract  | Retail website Stripe Checkout path untouched by Shopify carrier |

---

## 14. Database / migrations / ORM

| ID     | P   | Kind     | Assert                                                                     |
| ------ | --- | -------- | -------------------------------------------------------------------------- |
| DB-001 | P0  | unit     | `shopify_shops.shop_domain` UNIQUE                                         |
| DB-002 | P0  | unit     | FK `merchant_id` → merchants; FK pickup → saved_addresses                  |
| DB-003 | P0  | unit     | `ShopifyRateQuote` indexes: shop_id, merchant_id, request_hash, expires_at |
| DB-004 | P0  | migrate  | Alembic upgrade/downgrade both Shopify migrations clean                    |
| DB-005 | P1  | unit     | Order.metadata retains shopify order id + fulfillment id                   |
| DB-006 | P1  | unit     | Soft uninstall sets `uninstalled_at` without deleting history quotes       |
| DB-007 | P2  | unit     | Purge scripts list Shopify tables only when intentionally wiping ops data  |
| DB-008 | P2  | contract | `validate_postgres_modules` includes Shopify tables if module-mapped       |

---

## 15. Docker / env / tunnel / compose

| ID      | P   | Kind | Assert                                                                               |
| ------- | --- | ---- | ------------------------------------------------------------------------------------ |
| DOC-001 | P0  | dx   | `SHOPIFY_API_KEY/SECRET/VERSION` only on API env — **not** portal Next public env    |
| DOC-002 | P0  | dx   | Local `scripts/shopify-dev-tunnel.sh` exposes `/webhooks` + `/carrier-service/rates` |
| DOC-003 | P0  | dx   | Compose pins Postgres 18, Redis 8.8, Valhalla digest, OSRM, Fleetbase — no `:latest` |
| DOC-004 | P1  | dx   | Worker container shares API package for `process_queued_webhook`                     |
| DOC-005 | P1  | dx   | Mailpit reachable for Shopify booking email tests                                    |
| DOC-006 | P2  | dx   | Doppler prod notes: Shopify secrets in API project only                              |
| DOC-007 | P2  | dx   | `SHOPIFY_API_VERSION=2026-07` matches Admin API calls in service                     |

---

## 16. Architecture / OpenAPI / ownership guards

| ID       | P   | Kind     | Assert                                                                      |
| -------- | --- | -------- | --------------------------------------------------------------------------- |
| ARCH-001 | P0  | contract | Routers stay thin: merchant/shopify + public shopify only `_invoke`/service |
| ARCH-002 | P0  | NEG      | Do not vanity-split `shopify_service.py` (fat-but-coherent)                 |
| ARCH-003 | P0  | NEG      | Portal never calls Fleetbase HTTP / SocketCluster                           |
| ARCH-004 | P0  | NEG      | No PorterChain VROOM client for Shopify                                     |
| ARCH-005 | P0  | NEG      | No Google routing for Shopify rates                                         |
| ARCH-006 | P1  | contract | OpenAPI census includes Shopify paths; TS clients match                     |
| ARCH-007 | P1  | contract | Channel map `CHANNEL_ORDER_SOURCES["shopify"] == OrderSource.SHOPIFY`       |
| ARCH-008 | P2  | contract | Graphify/CodeGraph/Ripwire CI guards remain; sensors not dual-MCP’d         |

---

## 17. ERP / other connectors (sold vs not)

| ID      | P   | Kind     | Assert                                                                                |
| ------- | --- | -------- | ------------------------------------------------------------------------------------- |
| ERP-001 | P0  | contract | `ERP_READINESS` shopify `status=ready` with oauth/webhooks/order/fulfillment/tracking |
| ERP-002 | P0  | contract | woocommerce / netsuite / custom_erp = `not_offered` — UI must not sell as live        |
| ERP-003 | P0  | api      | Partner path `/v1/merchant-api/bookings` works as ERP substitute with API key         |
| ERP-004 | P1  | api      | NetSuite connect endpoints return not-offered / setup stub without inventing sync     |
| ERP-005 | P1  | api      | OAuth providers list includes Shopify OAuth URL `/v1/integrations/shopify/install`    |
| ERP-006 | P1  | api      | Merchant outbound webhooks deliver booking events for Shopify-origin orders           |
| ERP-007 | P2  | contract | Zapier templates / CSV templates remain available without implying WooCommerce        |
| ERP-008 | P2  | NEG      | Do not build WooCommerce plugin in this wave (intentional skip)                       |
| ERP-009 | P3  | future   | Custom ERP adapter interface (`base_adapter`) documented for partners                 |

---

## 18. Diagnostics / e2e validation / metrics

| ID       | P   | Kind  | Assert                                                                 |
| -------- | --- | ----- | ---------------------------------------------------------------------- |
| DIAG-001 | P0  | diag  | `/ready` includes routing + Fleetbase sync + clerk + firebase checks   |
| DIAG-002 | P1  | diag  | Commerce Prometheus metrics scrape includes shopify_quote counters     |
| DIAG-003 | P1  | e2e   | Admin e2e validation catalog can exercise Shopify webhook HMAC fixture |
| DIAG-004 | P1  | diag  | Execution metrics dashboard counts Shopify-channel orders              |
| DIAG-005 | P2  | chaos | Kill Valhalla mid-carrier → empty or OSRM rates; no 500                |
| DIAG-006 | P2  | chaos | Kill Fleetbase after book → RetryQueue grows; PC order remains         |
| DIAG-007 | P3  | soak  | 1k webhooks/hour under rate limit; no duplicate books (idempotency)    |

---

## 19. End-to-end golden paths (compose these)

| ID      | P   | Path                                                                                                                                                                       |
| ------- | --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E2E-001 | P0  | OAuth install → set pickup → CarrierService quote at checkout → orders/create webhook → PC Order → Fleetbase sync → driver complete → fulfillment push → Shopify fulfilled |
| E2E-002 | P0  | Custom Admin API token connect → same book loop                                                                                                                            |
| E2E-003 | P0  | Quote≡Book≡Invoice channel for one checkout                                                                                                                                |
| E2E-004 | P0  | orders/cancelled before dispatch → PC cancel + Fleetbase notified                                                                                                          |
| E2E-005 | P1  | app/uninstalled mid-flight → no new books; open orders still execute                                                                                                       |
| E2E-006 | P1  | GDPR redact topic → ack + privacy workflow hooks                                                                                                                           |
| E2E-007 | P1  | COD Shopify order → capture after delivery                                                                                                                                 |
| E2E-008 | P2  | Multi-shop same merchant (if product allows) or hard-block second domain                                                                                                   |
| E2E-009 | P2  | Sandbox vs live booking preference does not break HMAC ingress                                                                                                             |

**Explicitly out of local CI (ops / Partners secrets) — still checklist:**

| ID          | P   | Note                                             |
| ----------- | --- | ------------------------------------------------ |
| E2E-OPS-001 | P2  | Live Shopify Partners test shop + tunnel         |
| E2E-OPS-002 | P3  | App Store listing / `app.toml` client_id publish |

---

## 20. Things you asked for — coverage map

| You asked                                               | Covered by   |
| ------------------------------------------------------- | ------------ |
| Merchant Shopify pages/subpages                         | §1.1, §2     |
| Admin pages                                             | §1.2, §3     |
| Files/subfiles every level                              | §1 inventory |
| FastAPI / endpoints                                     | §4–5         |
| Microservices / worker / EventBus                       | §1.5, §11    |
| Fleetbase handshake                                     | §8           |
| Firebase / push                                         | §12          |
| Clerk                                                   | §9           |
| VROOM / Valhalla / OSRM / Google                        | §7, VRM-*    |
| Email / notification                                    | §12          |
| Backend / UI / UX / models / DB / Docker / architecture | §§2–6, 13–16 |
| Shopify                                                 | entire doc   |
| Other ERP / connections                                 | §17          |
| API + handshakes                                        | §§4–8, 19    |

### Gaps you did **not** name (added)

| Gap                                                    | Why it matters                                |
| ------------------------------------------------------ | --------------------------------------------- |
| Quote≡Book + `ShopifyRateQuote`                        | Money integrity at checkout                   |
| Carrier + webhook **rate limits** + Redis fail-open    | Shopify will ban flaky apps                   |
| GDPR mandatory webhooks                                | App review / compliance                       |
| `app/uninstalled`                                      | Token hygiene                                 |
| Install **hijack** / email bind                        | Security                                      |
| Fulfillment push-back loop                             | Merchant trust closure                        |
| COD capture                                            | Stripe Connect adjacency                      |
| Channel AR / Prometheus                                | Finance + observability                       |
| Intentional skips (App Store, WooCommerce, admin mint) | Prevent scope creep                           |
| Dev tunnel script                                      | Local realism                                 |
| Partner `/v1/merchant-api` as ERP substitute           | Sold alternative to Woo/NetSuite              |
| Embed CSP / App Bridge headers                         | Shopify admin iframe                          |
| Idempotent book + 503 retry contract                   | Exactly-once-ish under at-least-once webhooks |

---

## 21. Suggested execution order (dev layer)

1. **P0 security pack** — SEC-* + API-S HMAC/hijack + AUTH state
2. **P0 connect pack** — M-UI + API-M connect/pickup/disconnect + OAuth callback
3. **P0 money pack** — MAP + ENG Quote≡Book + BILL-001
4. **P0 ingress pack** — API-S webhooks + WRK + ENG book/cancel idempotency
5. **P0 Fleetbase pack** — FB-001…005 + ARCH browser isolation
6. **P1 notifications + admin 360 + fulfillment push**
7. **P2 chaos** — Redis/Valhalla/Fleetbase/Mailpit downs
8. **P3 soak + Partners live E2E (ops)**

Run existing suites first:

```bash
cd apps/api && pytest \
  tests/test_shopify_ingest.py \
  tests/test_shopify_urls.py \
  tests/test_shopify_phase4.py \
  tests/test_shopify_carrier_rates_p44.py \
  tests/test_shopify_carrier_pricing_handshake.py \
  tests/test_shopify_billing_wave_remaining.py \
  -q
```

Then add cases from this catalog as new `test_shopify_*` / portal Playwright only where unit gaps remain.

---

## 22. Sensor follow-ups (one moment per session)

| Next question                                            | Sensor                                    |
| -------------------------------------------------------- | ----------------------------------------- |
| “Where does X live / FastAPI↔PHP for Shopify orders?”    | Graphify `query` / `path` / `explain`     |
| Pydantic/ORM/`MapsService` extract before editing quotes | CodeGraph `explore`                       |
| Thin router / worker / UI edit blast radius              | Ripwire `--for` / `--expand` / `--impact` |

Do not run Graphify + CodeGraph + Ripwire hot in parallel; sequence Moments A→B→C.
