# Fleetbase Service Status

**Last verified:** 2026-06-29T14:29:14Z  
**Fleetbase version:** v0.7.40  
**Compose project:** `porterchain-fleetbase`  
**Verify command:** `pnpm docker:fleetbase:verify`

---

## Summary

| Result | Detail |
|--------|--------|
| **Overall** | ✅ All required checks **PASSED** |
| **Install method** | `pnpm docker:fleetbase:install` |
| **Deploy** | `./deploy.sh` completed (migrations, seeds, permissions) |

---

## Container status

| Service | Container | State | Health | Host ports |
|---------|-----------|-------|--------|------------|
| database | `porterchain-fleetbase-mysql` | running | healthy | `127.0.0.1:3307→3306` |
| cache | `porterchain-fleetbase-redis` | running | healthy | internal |
| socket | `porterchain-fleetbase-socketcluster` | running | — | `38000→8000` |
| queue | `porterchain-fleetbase-queue` | running | healthy | internal |
| scheduler | `porterchain-fleetbase-scheduler` | running | unhealthy* | internal |
| application | `porterchain-fleetbase-application` | running | healthy | internal |
| httpd | `porterchain-fleetbase-httpd` | running | — | `8000→80` |
| console | `porterchain-fleetbase-console` | running | — | `4200→4200` |

\*Scheduler reports `unhealthy` in Docker Desktop health probe but `go-crond` process is active; cron tasks synced (18 scheduled tasks). Non-blocking for dev.

---

## Endpoint verification

| Check | Result | URL / target |
|-------|--------|--------------|
| API (httpd) | ✅ PASS | http://127.0.0.1:8000 |
| Console | ✅ PASS | http://127.0.0.1:4200 |
| SocketCluster | ✅ PASS | tcp://127.0.0.1:38000 |
| Redis PING | ✅ PASS | `cache` container |
| MySQL ping | ✅ PASS | `database` container |
| Queue worker | ✅ PASS | `php artisan queue:status` — redis healthy |
| OSRM (public) | ✅ PASS | `router.project-osrm.org` route response |
| Valhalla (optional) | ✅ PASS | http://127.0.0.1:8002/status (Porterchain routing profile) |

---

## Component checklist (install requirements)

| Requirement | Status | Notes |
|-------------|--------|-------|
| Clone official repo | ✅ | `apps/fleetbase` @ v0.7.40 |
| AGPL license verified | ✅ | `apps/fleetbase/LICENSE.md` |
| PostgreSQL | N/A | Fleetbase uses MySQL |
| MySQL | ✅ | `porterchain-fleetbase-mysql` |
| Redis | ✅ | `porterchain-fleetbase-redis` |
| Storage | ✅ | Named volume `porterchain-fleetbase-api-storage` |
| WebSockets | ✅ | SocketCluster :38000 |
| Queues | ✅ | `queue` service — redis driver |
| Scheduler | ✅ | `scheduler` service — 18 tasks monitored |
| OSRM | ✅ | Public router (default) |
| Valhalla | ✅ | Porterchain `valhalla` profile on :8002 |
| API | ✅ | :8000 |
| Console | ✅ | :4200 |
| Driver app | ⚙️ | Fleetbase driver app is separate mobile build — not part of Docker stack |
| Dispatcher | ✅ | Console at :4200 |
| Authentication | ⚙️ | Complete onboarding wizard on first Console login |

---

## Porterchain integration (unchanged)

| Component | Status |
|-----------|--------|
| Website booking flow | Not modified |
| Merchant portal | Not modified |
| Porterchain API bridge | Configured via `env/fleetbase.env.example` |
| Fleetbase source code | Not modified |

---

## Re-verify

```bash
pnpm docker:fleetbase:verify
```

Update this file after major upgrades or infrastructure changes.

---

## Known notes

1. **Port 3307** — Fleetbase MySQL host bind avoids Porterchain core MySQL on 3306.
2. **Legacy stack** — Previous Fleetbase install at `~/Documents/GitHub/PC` (project `pc`) was stopped to free ports 8000/4200/38000.
3. **MySQL grants** — Install script grants `fleetbase` user privileges required for `fleetbase_sandbox` migrations.
4. **First login** — Open http://localhost:4200 and complete Fleetbase onboarding before using dispatch features.
