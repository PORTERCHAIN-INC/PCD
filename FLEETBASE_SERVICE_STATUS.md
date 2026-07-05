# Fleetbase Service Status


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Fleetbase version:** v0.7.40  
**Compose project:** `porterchain-fleetbase`  
**Verify command:** `pnpm docker:fleetbase:verify`

> Point-in-time snapshot from automated install verification. Re-run `pnpm docker:fleetbase:verify` after upgrades — do not treat this file as live monitoring.

---

## Summary (2026-06-29 run)

| Result | Detail |
| ------ | ------ |
| **Overall** | ✅ All required checks **PASSED** |
| **Install method** | `pnpm docker:fleetbase:install` |
| **Deploy** | `./deploy.sh` completed (migrations, seeds, permissions) |

---

## Container status (snapshot)

| Service | Container | State | Health | Host ports |
| ------- | --------- | ----- | ------ | ---------- |
| database | `porterchain-fleetbase-mysql` | running | healthy | `127.0.0.1:3307→3306` |
| cache | `porterchain-fleetbase-redis` | running | healthy | internal |
| socket | `porterchain-fleetbase-socketcluster` | running | — | `38000→8000` |
| queue | `porterchain-fleetbase-queue` | running | healthy | internal |
| scheduler | `porterchain-fleetbase-scheduler` | running | unhealthy* | internal |
| application | `porterchain-fleetbase-application` | running | healthy | internal |
| httpd | `porterchain-fleetbase-httpd` | running | — | `8000→80` |
| console | `porterchain-fleetbase-console` | running | — | `4200→4200` |

\*Scheduler Docker health probe may report `unhealthy` while `go-crond` is active — non-blocking for dev.

---

## Endpoint verification (snapshot)

| Check | Result | Target |
| ----- | ------ | ------ |
| API (httpd) | ✅ PASS | http://127.0.0.1:8000 |
| Console | ✅ PASS | http://127.0.0.1:4200 |
| SocketCluster | ✅ PASS | tcp://127.0.0.1:38000 |
| Redis PING | ✅ PASS | `cache` container |
| MySQL ping | ✅ PASS | `database` container |
| Queue worker | ✅ PASS | `php artisan queue:status` |
| Valhalla (optional) | ✅ PASS | http://127.0.0.1:8002/status (Porterchain routing profile) |

---

## Porterchain integration (July 2026)

| Component | Status |
| --------- | ------ |
| Adapter package | ✅ `services/fleetbase-adapter/` |
| Sync engine | ✅ `apps/api/.../fleetbase_engine/` |
| Webhook handler | ✅ `POST /webhooks/fleetbase` |
| Event-driven dispatch | ✅ `order.dispatch_ready` handlers |
| Driver mobile | ✅ `apps/mobile-driver/` (Clerk + Porterchain API — not Fleetbase Navigator) |
| Fleetbase source | ✅ Not modified |

---

## Re-verify

```bash
pnpm docker:fleetbase:verify
```

Update this file after major upgrades or infrastructure changes.

---

## Known notes

1. **Port 3307** — Fleetbase MySQL host bind avoids Porterchain PostgreSQL on 5432 / legacy MySQL on 3306.
2. **First login** — Complete Fleetbase onboarding at http://localhost:4200 before dispatch.
3. **MySQL grants** — Install script grants `fleetbase` user privileges for `fleetbase_sandbox` migrations.

---

## Related

| Document | Purpose |
| -------- | ------- |
| [FLEETBASE_INSTALL.md](./FLEETBASE_INSTALL.md) | Install runbook |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md) | Bridge architecture |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
