# Fleetbase APIs — Route Reference

**Last verified:** 2026-07-04  
**Base URLs (local):** API `http://localhost:8000` | Console uses `int/v1`  
**Versions analyzed:** core-api 1.6.47, fleetops-api 0.6.48  
**Auth:** See authentication section below

> **Porterchain usage:** [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) · **Adapter:** [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md)

---

## Authentication

### Internal API (`/int/v1/*`)

| Method     | Mechanism                                   |
| ---------- | ------------------------------------------- |
| Session    | Laravel Sanctum — cookie from console login |
| Middleware | `fleetbase.protected`                       |
| Bootstrap  | `GET int/v1/auth/bootstrap`                 |

### Consumable API (`/v1/*`)

| Method            | Mechanism                                              |
| ----------------- | ------------------------------------------------------ |
| Bearer token      | `Authorization: Bearer flb_live_xxx` or `flb_test_xxx` |
| Middleware        | `fleetbase.api`                                        |
| Credentials admin | `int/v1/api-credentials`                               |

### Driver mobile (`/v1/drivers/*`)

| Endpoint                                    | Auth                 |
| ------------------------------------------- | -------------------- |
| `login`, `login-with-sms`, `verify-code`    | Public               |
| `register-device`, `track`, `toggle-online` | Driver session token |

### Porterchain bridge

| Endpoint                                                | Auth                    | Status                                                     |
| ------------------------------------------------------- | ----------------------- | ---------------------------------------------------------- |
| `POST /v1/orders` (+ drivers, vehicles, dispatch)       | `flb_live_*` API key    | ✅ **Production** — used by `fleetbase-adapter`            |
| `POST /int/v1/porterchain/sso/exchange`                 | Service key / extension | ⚠️ SSO — requires `porterchain-bridge` Fleetbase extension |
| `POST /int/v1/porterchain/sso/users/{uuid}/permissions` | Service key             | ⚠️ SSO permission sync                                     |
| `POST /int/v1/porterchain/orders`                       | Service key             | Optional — tailored payloads; v1 API used today            |

**Porterchain inbound:** `POST http://localhost:8001/webhooks/fleetbase` (Fleetbase → Porterchain status sync)

---

## Health

| Method | Path      | Auth | Description                                               |
| ------ | --------- | ---- | --------------------------------------------------------- |
| GET    | `/health` | None | Load balancer health (local shell `RouteServiceProvider`) |

---

## Core API — Consumable (`/v1`)

| Resource                | Methods                       | Notes                   |
| ----------------------- | ----------------------------- | ----------------------- |
| `organizations/current` | GET                           | Current org for API key |
| `files`                 | CRUD + `base64`, `download`   | File storage            |
| `chat-channels`         | CRUD + messages, participants | Chat API                |
| `comments`              | CRUD                          | Polymorphic comments    |

---

## Core API — Internal (`/int/v1`)

### Public / pre-auth

| Prefix                        | Key endpoints                                      |
| ----------------------------- | -------------------------------------------------- |
| `installer/*`                 | `initialize`, `createdb`, `migrate`, `seed`        |
| `onboard/*`                   | `should-onboard`, `create-account`, `verify-email` |
| `lookup/*`                    | `timezones`, `countries`, `currencies`             |
| `two-fa/*`                    | `check`, `validate`, `verify`, `resend`            |
| `settings/branding`           | GET branding                                       |
| `users/accept-company-invite` | POST                                               |

### Protected (`fleetbase.protected`)

| Resource                                                                   | Notable actions                                            |
| -------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `auth/*`                                                                   | `bootstrap`, `organizations`, `impersonate`                |
| `users`                                                                    | `me`, `invite-user`, `activate`, `deactivate`, 2FA, locale |
| `companies`                                                                | `users`, `transfer-ownership`, `leave`, 2FA settings       |
| `roles`, `permissions`, `policies`, `groups`                               | IAM CRUD                                                   |
| `api-credentials`                                                          | `roll`, `export`, `bulk-delete`                            |
| `api-events`                                                               | Event audit log                                            |
| `api-request-logs`                                                         | API access log                                             |
| `webhook-endpoints`                                                        | `enable`, `disable`, `events`, `versions`                  |
| `webhook-request-logs`                                                     | Delivery log                                               |
| `extensions`                                                               | Installed extensions                                       |
| `settings`                                                                 | Mail, queue, filesystem, services, branding, notifications |
| `files`                                                                    | `upload`, `uploadBase64`, `download`                       |
| `notifications`                                                            | `registry`, `mark-as-read`, `save-settings`                |
| `dashboards`, `dashboard-widgets`                                          | Custom dashboards                                          |
| `reports`                                                                  | SQL report builder, `execute`, `export`                    |
| `schedules`, `schedule-items`, `schedule-templates`, `schedule-exceptions` | Workforce scheduling                                       |
| `chat-*`                                                                   | Full chat admin                                            |
| `activities`                                                               | Activity log                                               |
| `metrics`                                                                  | `iam`, `iam-dashboard`                                     |
| `schedule-monitor`                                                         | Cron task monitoring                                       |
| `templates`, `template-queries`                                            | Notification/document templates                            |
| `transactions`                                                             | Payment transactions                                       |
| `custom-fields`, `custom-field-values`                                     | EAV fields                                                 |
| `categories`                                                               | Taxonomy                                                   |
| `comments`                                                                 | CRUD                                                       |

Standard REST pattern for each resource:

```
GET    /{resource}           → query (list)
POST   /{resource}           → create
GET    /{resource}/{id}      → find
PUT    /{resource}/{id}      → update
DELETE /{resource}/{id}      → delete
```

---

## FleetOps API — Consumable (`/v1`)

Middleware: `fleetbase.api` + `TransformLocationMiddleware`

### Drivers

| Method | Path                                   | Description     |
| ------ | -------------------------------------- | --------------- |
| POST   | `/v1/drivers`                          | Create driver   |
| GET    | `/v1/drivers`                          | List/query      |
| GET    | `/v1/drivers/{id}`                     | Get driver      |
| PUT    | `/v1/drivers/{id}`                     | Update          |
| DELETE | `/v1/drivers/{id}`                     | Delete          |
| POST   | `/v1/drivers/login`                    | Password login  |
| POST   | `/v1/drivers/login-with-sms`           | SMS login       |
| POST   | `/v1/drivers/verify-code`              | Verify SMS      |
| POST   | `/v1/drivers/register-device`          | FCM device      |
| POST   | `/v1/drivers/{id}/track`               | GPS ping        |
| POST   | `/v1/drivers/{id}/toggle-online`       | Online/offline  |
| POST   | `/v1/drivers/{id}/switch-organization` | Multi-org       |
| POST   | `/v1/drivers/{id}/simulate`            | Simulation mode |

### Orders

| Method     | Path                                             | Description        |
| ---------- | ------------------------------------------------ | ------------------ |
| POST       | `/v1/orders`                                     | Create order       |
| GET        | `/v1/orders`                                     | List/query         |
| GET        | `/v1/orders/{id}`                                | Get order          |
| PUT        | `/v1/orders/{id}`                                | Update             |
| DELETE     | `/v1/orders/{id}`                                | Delete             |
| POST/PATCH | `/v1/orders/{id}/schedule`                       | Schedule           |
| POST/PATCH | `/v1/orders/{id}/dispatch`                       | Dispatch           |
| POST       | `/v1/orders/{id}/start`                          | Start execution    |
| POST/PATCH | `/v1/orders/{id}/update-activity`                | Workflow activity  |
| POST       | `/v1/orders/{id}/complete`                       | Complete           |
| DELETE     | `/v1/orders/{id}/cancel`                         | Cancel             |
| GET        | `/v1/orders/{id}/tracker`                        | Tracking data      |
| GET        | `/v1/orders/{id}/eta`                            | ETA                |
| GET        | `/v1/orders/{id}/distance-and-time`              | Distance matrix    |
| GET        | `/v1/orders/{id}/next-activity`                  | Next workflow step |
| GET        | `/v1/orders/{id}/comments`                       | Order comments     |
| POST/PATCH | `/v1/orders/{id}/set-destination/{placeId}`      | Change destination |
| POST       | `/v1/orders/{id}/capture-signature/{subjectId?}` | POD signature      |
| POST       | `/v1/orders/{id}/capture-photo/{subjectId?}`     | POD photo          |
| POST       | `/v1/orders/{id}/capture-qr/{subjectId?}`        | POD QR             |
| GET        | `/v1/orders/{id}/proofs/{subjectId?}`            | List proofs        |

### Fleet resources

| Resource          | Path prefix             | CRUD           |
| ----------------- | ----------------------- | -------------- |
| Contacts          | `/v1/contacts`          | ✅             |
| Vendors           | `/v1/vendors`           | ✅             |
| Vehicles          | `/v1/vehicles`          | ✅ + `track`   |
| Fleets            | `/v1/fleets`            | ✅             |
| Places            | `/v1/places`            | ✅ + `search`  |
| Zones             | `/v1/zones`             | ✅             |
| Service areas     | `/v1/service-areas`     | ✅             |
| Service rates     | `/v1/service-rates`     | ✅             |
| Service quotes    | `/v1/service-quotes`    | ✅ (read)      |
| Payloads          | `/v1/payloads`          | ✅             |
| Entities          | `/v1/entities`          | ✅             |
| Tracking numbers  | `/v1/tracking-numbers`  | ✅ + `from-qr` |
| Tracking statuses | `/v1/tracking-statuses` | ✅             |
| Fuel reports      | `/v1/fuel-reports`      | ✅             |
| Issues            | `/v1/issues`            | ✅             |
| Labels            | `/v1/labels/{id}`       | GET label PDF  |
| Purchase rates    | `/v1/purchase-rates`    | Create/read    |

### Orchestration

| Method | Path                      | Description             |
| ------ | ------------------------- | ----------------------- |
| POST   | `/v1/orchestrator/run`    | Run optimization        |
| POST   | `/v1/orchestrator/commit` | Commit optimized routes |

### Geofences (read-only API)

| Method | Path                                        |
| ------ | ------------------------------------------- |
| GET    | `/v1/geofences/events`                      |
| GET    | `/v1/geofences/inventory`                   |
| GET    | `/v1/geofences/dwell-report`                |
| GET    | `/v1/geofences/driver/{driverUuid}/history` |

### Public (no API key)

| Method | Path                                              |
| ------ | ------------------------------------------------- |
| GET    | `/v1/organizations`                               |
| GET    | `/v1/onboard/driver-onboard-settings/{companyId}` |

---

## FleetOps API — Internal (`/int/v1`)

Middleware: `fleetbase.protected` + location transform + optional driver session

### Standard CRUD resources

`contacts`, `drivers`, `vehicles`, `fleets`, `orders`, `order-configs`, `payloads`, `entities`, `places`, `routes`, `positions`, `proofs`, `purchase-rates`, `service-areas`, `zones`, `service-rates`, `service-quotes`, `tracking-numbers`, `tracking-statuses`, `vendors`, `integrated-vendors`, `fuel-reports`, `issues`, `vehicle-devices`, `devices`, `device-events`, `sensors`, `telematics`, `maintenance-schedules`, `work-orders`, `maintenances`, `equipment`, `parts`, `warranties`

### Orders — dispatch-specific (internal)

| Method | Path                          | Description               |
| ------ | ----------------------------- | ------------------------- |
| PATCH  | `orders/dispatch`             | Dispatch order            |
| PATCH  | `orders/bulk-dispatch`        | Bulk dispatch             |
| PATCH  | `orders/bulk-assign-driver`   | Bulk assign               |
| PATCH  | `orders/schedule`             | Schedule without dispatch |
| PATCH  | `orders/start`                | Start                     |
| PATCH  | `orders/cancel`               | Cancel                    |
| PATCH  | `orders/bulk-cancel`          | Bulk cancel               |
| POST   | `orders/{id}/ping-driver`     | Notify driver             |
| PATCH  | `orders/route/{id}`           | Edit route                |
| PATCH  | `orders/update-activity/{id}` | Activity update           |
| GET    | `orders/{id}/tracker`         | Tracker info              |
| GET    | `orders/{id}/eta`             | Waypoint ETAs             |

### Live map (`/int/v1/fleet-ops/live`)

| Method | Path          | Returns              |
| ------ | ------------- | -------------------- |
| GET    | `coordinates` | Live GPS coordinates |
| GET    | `routes`      | Active routes        |
| GET    | `orders`      | Active orders        |
| GET    | `drivers`     | Driver positions     |
| GET    | `vehicles`    | Vehicle positions    |
| GET    | `places`      | Place markers        |

### Settings (`/int/v1/fleet-ops/settings`)

| Endpoint group            | Purpose                    |
| ------------------------- | -------------------------- |
| `routing-settings`        | OSRM/Valhalla/VROOM config |
| `tracking-settings`       | Tracking provider config   |
| `map`, `admin-map`        | Map tile settings          |
| `orchestrator-settings`   | Optimization engine config |
| `notification-settings`   | FleetOps notifications     |
| `scheduling-settings`     | Dispatch scheduling        |
| `driver-onboard-settings` | Navigator onboarding       |

### Orchestrator (internal)

| Method | Path                                   |
| ------ | -------------------------------------- |
| GET    | `fleet-ops/orchestrator/orders`        |
| POST   | `fleet-ops/orchestrator/run`           |
| POST   | `fleet-ops/orchestrator/commit`        |
| GET    | `fleet-ops/orchestrator/preview`       |
| GET    | `fleet-ops/orchestrator/engines`       |
| POST   | `fleet-ops/orchestrator/import-orders` |

### Geocoder (`/int/v1/geocoder`)

| Method | Path      |
| ------ | --------- |
| GET    | `reverse` |
| GET    | `query`   |

### Metrics

| Method | Path                        |
| ------ | --------------------------- |
| GET    | `/int/v1/fleet-ops/metrics` |

### Manifests

| Method | Path                                      |
| ------ | ----------------------------------------- |
| GET    | `/int/v1/fleet-ops/manifests`             |
| GET    | `/int/v1/fleet-ops/manifests/{id}`        |
| POST   | `/int/v1/fleet-ops/manifests/{id}/cancel` |

---

## Inbound webhooks (Fleetbase receives)

| Method | Path                                 | Purpose                      |
| ------ | ------------------------------------ | ---------------------------- |
| ANY    | `/webhooks/telematics/{providerKey}` | Telematics provider callback |
| ANY    | `/webhooks/telematics/ingest/{id}`   | Device data ingest           |

---

## Porterchain → Fleetbase integration map

| Porterchain trigger     | Fleetbase API                                       |
| ----------------------- | --------------------------------------------------- |
| `ORDER_DISPATCH_READY`  | `POST /v1/orders`                                   |
| Admin approves driver   | `POST /v1/drivers`                                  |
| Admin approves vehicle  | `POST /v1/vehicles`                                 |
| Assign driver           | `PATCH /v1/orders/{id}/dispatch`                    |
| Customer tracking       | `GET /v1/orders/{id}/tracker`, `/eta`               |
| Driver GPS (via bridge) | `POST /v1/drivers/{id}/track`                       |
| POD complete            | `POST /v1/orders/{id}/complete` + capture endpoints |
| Ops console SSO         | `POST /int/v1/porterchain/sso/exchange` (extension) |

### Porterchain env vars

| Variable                         | Purpose                            |
| -------------------------------- | ---------------------------------- |
| `FLEETBASE_API_URL`              | Base URL (`http://localhost:8000`) |
| `FLEETBASE_API_KEY`              | Bearer token for bridge            |
| `FLEETBASE_DISPATCH_BRIDGE`      | Enable/disable sync                |
| `FLEETBASE_DEFAULT_COMPANY_UUID` | Target company                     |

---

## API conventions

| Concept         | Format                                                      |
| --------------- | ----------------------------------------------------------- |
| IDs             | `uuid` (internal), `public_id` (external, e.g. `order_xxx`) |
| Pagination      | `page`, `limit` query params (fast-paginate)                |
| Filtering       | Filter/query params per resource                            |
| Location fields | Transformed by `TransformLocationMiddleware`                |
| Sandbox         | Separate DB `fleetbase_sandbox` for test API keys           |
| Version header  | API version in webhook payload `api_version`                |

---

## Official documentation

- [Fleetbase API docs](https://www.fleetbase.io/docs/api)
- [Running locally](https://www.fleetbase.io/docs/platform/quickstart/running-locally)

---

## Discovering routes in a running stack

```bash
docker exec porterchain-fleetbase-application php artisan route:list --columns=method,uri,name
```

Use when submodules are empty and you need to verify deployed image routes.
