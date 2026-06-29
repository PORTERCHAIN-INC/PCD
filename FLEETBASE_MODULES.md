# Fleetbase Modules — Porterchain Integration Guide

**Fleetbase:** v0.7.40 | **Packages:** core-api 1.6.47, fleetops-api 0.6.48  
For each module: purpose, Porterchain fit, and recommended action.

**Legend**

| Column | Meaning |
|--------|---------|
| **Use directly** | Call Fleetbase APIs or use console as-is |
| **Unchanged** | Do not fork or patch upstream Fleetbase |
| **Extend** | Add Porterchain bridge, webhooks, or Fleetbase extension |
| **Replace** | Porterchain owns this for customer/merchant surfaces |

---

## Authentication

**What it does**

- **Console auth:** Laravel Sanctum cookie sessions + `ember-simple-auth` in Ember console
- **API auth:** Bearer tokens from `fleetbase_api_credentials` (`flb_test_*` / `flb_live_*`)
- **Driver auth:** SMS/verify/login on `v1/drivers/*` (Navigator mobile app)
- **2FA:** `int/v1/two-fa/*`, per-company and system settings
- **IAM:** Spatie Permission integrated with Fleetbase policies

**Key tables:** `fleetbase_users`, `fleetbase_personal_access_tokens`, `fleetbase_login_attempts`, `fleetbase_verification_codes`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Partially** — API keys for bridge; Sanctum for ops console login only |
| Remain unchanged? | **Yes** — Fleetbase auth stays for console and Navigator |
| Extend? | **Yes** — `FLEETBASE_API_KEY` on Porterchain bridge; `PORTERCHAIN_DISPATCHER_API_KEY` for reverse calls |
| Replace? | **Yes** — Clerk for website, merchant portal, admin portal; Porterchain JWT for driver app |

---

## Users

**What it does**

- Platform users: ops staff, admins, invited team members
- `CompanyUser` pivot links users to organizations (companies)
- Invites, devices, locale, password, impersonation (console)
- **Not** the same as FleetOps drivers (separate model)

**Models:** `Fleetbase\Models\User`, `CompanyUser`, `Invite`, `UserDevice`  
**Console:** `@fleetbase/iam-engine`, `console/app/models/user.js`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **No** for merchants/customers |
| Remain unchanged? | **Yes** for Fleetbase console operators |
| Extend? | Optional: provision Fleetbase ops users when Porterchain admin staff need console access |
| Replace? | **Yes** — Porterchain `AdminUser`, Clerk org members, merchant team |

---

## Drivers

**What it does**

- Operational driver entity: GPS `location` (GEOMETRY), online status, assigned vehicle
- Auth token for Navigator app; link to optional `user_uuid`
- Scheduling: shift items, HOS status, availabilities (v0.6.48+)
- Track endpoint: `POST v1/drivers/{id}/track` for GPS pings

**Models:** `Fleetbase\FleetOps\Models\Driver`  
**Table:** `fleetbase_drivers` (uuid, company_uuid, vehicle_uuid, location, online, status, meta)

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — execution layer after Porterchain onboarding approval |
| Remain unchanged? | **Yes** |
| Extend? | **Yes** — `sync_driver()` bridge; map `porterchain_driver_id` in `meta` |
| Replace? | **Partial** — application, documents, approval UX in Porterchain; Fleetbase holds ops record |

---

## Vehicles

**What it does**

- Fleet vehicle registry: type, plate, capacity, telematics linkage
- `VehicleDevice` / `VehicleDeviceEvent` for hardware integration
- Track endpoint: `POST v1/vehicles/{id}/track`
- Assigned to drivers and fleets

**Models:** `Vehicle`, `VehicleDevice`, `VehicleDeviceEvent`  
**Tables:** `fleetbase_vehicles`, `fleetbase_vehicle_devices`, `fleetbase_vehicle_device_events`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** |
| Remain unchanged? | **Yes** |
| Extend? | **Yes** — sync on admin vehicle approval |
| Replace? | **No** — Fleetbase is system of record for dispatch |

---

## Fleet

**What it does**

- Hierarchical fleet groupings
- Assign/remove drivers and vehicles to fleets
- Used for dispatch filtering, orchestration input, live map layers

**Models:** `Fleet`, `FleetDriver`, `FleetVehicle`  
**Tables:** `fleetbase_fleets`, `fleetbase_fleet_drivers`, `fleetbase_fleet_vehicles`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — via console or `v1/fleets` |
| Remain unchanged? | **Yes** |
| Extend? | Optional: auto-assign new drivers to default Porterchain fleet |
| Replace? | **No** |

---

## Orders

**What it does**

- Core operational order: payload (pickup/dropoff), route, driver/vehicle assignment
- Workflow via `OrderConfig` — activities, automation, custom fields
- States: scheduled → dispatched → started → completed; `pod_required`, `tracking_number_uuid`
- Links: `payload_uuid`, `route_uuid`, `driver_assigned_uuid`, `customer_uuid` (polymorphic)

**Models:** `Order`, `OrderConfig`, `Payload`, `Entity`, `Waypoint`  
**Table:** `fleetbase_orders` (dispatched, started, scheduled_at, status, meta, options)

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — after commercial booking confirmed in Porterchain |
| Remain unchanged? | **Yes** |
| Extend? | **Yes** — bridge on `DISPATCH_READY`; store `porterchain_order_id` in `meta` |
| Replace? | **Yes** for commercial order (pricing, Stripe, Net terms) — Fleetbase mirrors execution |

---

## Dispatch

**What it does**

- Manual dispatch: `PATCH int/v1/orders/dispatch`, `bulk-dispatch`, `bulk-assign-driver`
- Schedule without dispatch: `PATCH schedule`
- Orchestrator: VROOM + native capacity engine (`orchestrator/run`, `commit`, `preview`)
- Auto-dispatch rules via order config flows
- Ping driver, cancel, start, activity updates

**Controllers:** `OrderController`, `OrchestrationController`  
**Events:** `OrderDispatched`, `OrderDispatchFailed`, `OrderDriverAssigned`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — primary reason to run Fleetbase |
| Remain unchanged? | **Yes** |
| Extend? | Webhook consumer updates Porterchain order status |
| Replace? | **No** — do not rebuild dispatch in Porterchain |

---

## Tracking

**What it does**

- `TrackingNumber` + `TrackingStatus` history
- Live GPS: `Position` model, driver `track` endpoint
- Order tracker: `GET v1/orders/{id}/tracker`, `eta`
- Tracking providers: OSRM, Google Routes, calculated (company settings)
- Public tracking via tracking number (configurable)

**Tables:** `fleetbase_tracking_numbers`, `fleetbase_tracking_statuses`, `fleetbase_positions`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — `fetch_tracking()` bridge + `v1` tracker API |
| Remain unchanged? | **Yes** |
| Extend? | Map Fleetbase statuses → Porterchain `ORDER_LIFECYCLE` states |
| Replace? | **Yes** for customer-facing tracking UI (website/merchant portal) |

---

## POD (Proof of Delivery)

**What it does**

- Capture signature, photo, QR scan on order: `capture-signature`, `capture-photo`, `capture-qr`
- `Proof` model stores artifacts linked to order/entity
- `pod_required`, `pod_method` on order
- Completion triggers `OrderCompleted` event

**Table:** `fleetbase_proofs`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — via Navigator or `v1/orders/{id}/capture-*` |
| Remain unchanged? | **Yes** |
| Extend? | Porterchain driver app proxies to Fleetbase or duplicates capture → sync |
| Replace? | **No** for storage; Porterchain may add compliance rules on top |

---

## Maps

**What it does**

- **Console:** Leaflet + `@fleetbase/leaflet-routing-machine`, live map (`int/v1/fleet-ops/live/*`)
- **Settings:** `fleet-ops/settings/map`, `admin-map` — tile providers, defaults
- **Geocoder:** `int/v1/geocoder/reverse`, `query`
- Real-time: SocketCluster channels for company, order, driver

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** for ops (Fleetbase console) |
| Remain unchanged? | **Yes** |
| Extend? | Admin portal map snapshot can pull Fleetbase live API |
| Replace? | **Yes** — Google Maps for retail quote, merchant booking, driver nav UX |

---

## Routing

**What it does**

- **Valhalla** (`fleetbase/valhalla-api`, `VALHALLA_BASE_URI`) — primary engine in Porterchain env
- **VROOM** (`fleetbase/vroom-api`) — multi-vehicle route optimization
- **OSRM** — fallback/public router (`OSRM_HOST`)
- **Google Routes** — tracking ETA provider (v0.6.48+)
- Distance matrix on orders; route geometry in `fleetbase_routes`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — share Valhalla :8002 with Porterchain routing stack |
| Remain unchanged? | **Yes** |
| Extend? | Porterchain quote engine may call Valhalla independently for pricing |
| Replace? | **No** for dispatch optimization; Porterchain owns quote-time routing policy |

---

## Notifications

**What it does**

- In-app: `fleetbase_notifications` + SocketCluster broadcast
- Channels: FCM, APN, Twilio SMS, email (configurable per company)
- FleetOps order event notifications via `NotifyOrderEvent` listener
- Registry: `fleet-ops/settings/notification-settings`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Partial** — driver push via FCM path |
| Remain unchanged? | **Yes** for ops/driver alerts inside Fleetbase |
| Extend? | Fleetbase webhooks trigger Porterchain emails (customer/merchant) |
| Replace? | **Yes** — `porterchain_services/notifications` for retail/merchant comms |

---

## Places

**What it does**

- Normalized address + `GEOMETRY location`
- Geocoding search/lookup; import/export
- Used as pickup/dropoff on payloads and waypoints

**Model:** `Place` → `fleetbase_places`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** when creating Fleetbase orders from Porterchain addresses |
| Remain unchanged? | **Yes** |
| Extend? | Transform Porterchain pickup/dropoff JSON → Fleetbase Place on sync |
| Replace? | **No** at booking — Google Places on Porterchain website |

---

## Contacts

**What it does**

- Customers and facilitators for orders (polymorphic `customer_uuid` / `customer_type`)
- Import/export, bulk delete
- Distinct from Fleetbase `User` — business contact records

**Table:** `fleetbase_contacts`

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Optional** — as order customer reference |
| Remain unchanged? | **Yes** |
| Extend? | Create Fleetbase contact from merchant org on first order |
| Replace? | **Yes** — Porterchain CRM (`AdminCrmService`, merchant records) is authoritative |

---

## Locations

**What it does**

- **Driver location:** `fleetbase_drivers.location` (GEOMETRY), updated via track API
- **Position history:** `fleetbase_positions` with replay/metrics endpoints
- **Live coordinates:** `int/v1/fleet-ops/live/coordinates`
- **Geofences:** enter/exit/dwell events

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** |
| Remain unchanged? | **Yes** |
| Extend? | Admin map + merchant tracking poll Fleetbase positions |
| Replace? | **No** |

---

## Webhooks

**What it does**

- **Outbound:** Company-configured endpoints fire on resource lifecycle events
- **Inbound:** Telematics provider callbacks (`webhooks/telematics/*`)
- Admin: `int/v1/webhook-endpoints`, logs at `webhook-request-logs`
- Signed payloads with API secret

See [FLEETBASE_WEBHOOKS.md](./FLEETBASE_WEBHOOKS.md).

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — subscribe Porterchain API to Fleetbase events |
| Remain unchanged? | **Yes** |
| Extend? | **Yes** — Porterchain `/v1/webhooks/fleetbase` handler (to build) |
| Replace? | **No** |

---

## API

**What it does**

- Dual surface: `int/v1` (console) + `v1` (integrations)
- `fleetbaseRoutes()` macro: standard REST CRUD
- API credentials, request logs, sandbox DB (`fleetbase_sandbox`)
- Throttling, response caching (configurable)

See [FLEETBASE_APIS.md](./FLEETBASE_APIS.md).

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — sole integration surface |
| Remain unchanged? | **Yes** |
| Extend? | **Yes** — `int/v1/porterchain/*` extension routes |
| Replace? | **No** |

---

## Extensions

**What it does**

- Composer packages (PHP) + Ember engines (JS) registered via `fleetbase_extensions`
- Registry at `https://registry.fleetbase.io` — install via `registry-bridge`
- Extension manager in console loads engines dynamically
- Submodule source: `packages/core-api`, `packages/fleetops`, etc.

Bundled extensions: FleetOps, Storefront, Ledger, Valhalla, VROOM, Registry Bridge.

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Yes** — install/disable via console |
| Remain unchanged? | **Yes** |
| Extend? | **Yes** — publish `porterchain-bridge` extension (recommended) |
| Replace? | **No** |

---

## Events

**What it does**

- Laravel domain events + listeners
- `ResourceLifecycleEvent` → webhooks + SocketCluster broadcast
- Activity log (Spatie) → `fleetbase_activity`
- API event audit → `fleetbase_api_events`

See [FLEETBASE_EVENTS.md](./FLEETBASE_EVENTS.md).

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Indirectly** via webhooks and polling |
| Remain unchanged? | **Yes** |
| Extend? | Map Fleetbase events → Porterchain `DomainEvents` catalog |
| Replace? | Porterchain event bus for commercial domain only |

---

## Jobs

**What it does**

- Laravel queued jobs in `fleetops/server/src/Jobs/` and `core-api`
- Processed by Docker `queue` service: `php artisan queue:work`
- Failed jobs → `fleetbase_failed_jobs`
- Examples: webhook delivery, notification sends, imports, orchestration commits

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **No** — internal to Fleetbase |
| Remain unchanged? | **Yes** |
| Extend? | — |
| Replace? | Porterchain `apps/worker` for commercial async work |

---

## Queues

**What it does**

- `QUEUE_CONNECTION=redis` (Docker `cache` service)
- Separate from Porterchain Redis (different Docker stack)
- Scheduler dispatches recurring tasks via `scheduler` container + crontab

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **No** |
| Remain unchanged? | **Yes** |
| Extend? | — |
| Replace? | Porterchain `packages/queue` (Redis) — keep separate instances |

---

## Permissions

**What it does**

- Spatie roles/permissions + Fleetbase policies and groups
- Permission format: `{extension} {action} {resource}` (e.g. `fleet-ops create order`)
- Console utils: `get-permission-action`, `get-permission-resource`
- Seeded via `php artisan fleetbase:create-permissions` in `deploy.sh`

**Tables:** `fleetbase_roles`, `fleetbase_permissions`, `fleetbase_policies`, `fleetbase_groups`, pivots

| Question | Answer |
|----------|--------|
| Can Porterchain use it directly? | **Console only** |
| Remain unchanged? | **Yes** |
| Extend? | — |
| Replace? | **Yes** — Porterchain RBAC (`ROLE_PERMISSIONS.md`, `admin_engine/rbac.py`) for portals |

---

## Bundled but non-critical modules (Porterchain)

| Module | Package | Porterchain stance |
|--------|---------|-------------------|
| Storefront | storefront-api 0.4.14 | **Ignore** — Porterchain has own merchant portal |
| Ledger | ledger-api 0.0.3 | **Replace** — Porterchain billing/invoicing |
| Registry | registry-bridge 0.1.9 | **Use** for extension installs only |
| Chat | core-api | **Optional** — ops internal chat in console |
| Dashboards/Reports | core-api | **Optional** — ops analytics; Porterchain admin has own reports |
| Maintenance | fleetops | **Future** — vehicle maintenance if needed |
| Telematics | fleetops | **Future** — hardware integrations |
| Manifests | fleetops | **Future** — multi-stop route manifests |

---

## Console engines (Ember)

| npm package | Version | UI domain |
|-------------|---------|-----------|
| `@fleetbase/fleetops-engine` | 0.6.48 | Orders, map, drivers, dispatch, orchestrator |
| `@fleetbase/iam-engine` | 0.1.9 | Users, roles, permissions |
| `@fleetbase/dev-engine` | 0.2.13 | API keys, webhooks |
| `@fleetbase/storefront-engine` | 0.4.14 | E-commerce admin |
| `@fleetbase/ledger-engine` | 0.0.3 | Accounting |
| `@fleetbase/valhalla-engine` | 0.0.4 | Routing settings |
| `@fleetbase/vroom-engine` | 0.0.4 | Optimization UI |

**Porterchain rule:** Merchants and retail customers **never** access `:4200`. Ops and dispatch staff only.
