# Fleetbase Operations Runbook — Porterchain

Day-2 procedures for the self-hosted Fleetbase stack in `apps/fleetbase/`.

---

## Daily checks

```bash
pnpm docker:fleetbase:verify
```

Confirm:

- API http://localhost:8000 responds
- Console http://localhost:4200 loads
- Queue worker healthy (`redis` driver)
- No containers in restart loop: `docker ps --filter name=porterchain-fleetbase`

---

## Start / stop

### Start

```bash
pnpm docker:fleetbase:up
```

### Stop (preserve data)

```bash
pnpm docker:fleetbase:down
```

### Stop and wipe data (destructive)

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml down -v
```

---

## View logs

```bash
# All services
pnpm docker:fleetbase:logs

# Single service
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml logs -f application
```

| Service       | When to tail                     |
| ------------- | -------------------------------- |
| `application` | API errors, Laravel exceptions   |
| `queue`       | Failed jobs, dispatch delays     |
| `httpd`       | 502/504, nginx                   |
| `database`    | Connection issues                |
| `socket`      | WebSocket disconnects in console |

---

## Redeploy / migrations

After env changes or version upgrade:

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -T application bash -c "./deploy.sh"

docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml up -d
```

`deploy.sh` runs: `mysql:createdb`, `migrate`, `sandbox:migrate`, `fleetbase:seed`, permissions, cache clear, `registry:init`.

---

## MySQL access

| From         | Connection                                                                                   |
| ------------ | -------------------------------------------------------------------------------------------- |
| Host         | `127.0.0.1:3307`, user `fleetbase`, password in `apps/fleetbase/docker-compose.override.yml` |
| Inside stack | host `database`, port `3306`                                                                 |

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -it database mysql -ufleetbase -p fleetbase
```

---

## Redis access

```bash
cd apps/fleetbase
docker compose -f docker-compose.yml -f docker-compose.override.yml \
  -f ../../infrastructure/docker/fleetbase.porterchain.override.yml \
  exec -it cache redis-cli
```

---

## Queue management

```bash
# Status
docker compose ... exec -T queue php artisan queue:status

# Restart workers after deploy
docker compose ... exec -T application php artisan queue:restart

# Restart queue container
docker compose ... restart queue
```

---

## Scheduler

Cron runs in `scheduler` container via `go-crond`. After deploy, sync tasks:

```bash
docker compose ... exec -T application php artisan schedule-monitor:sync
docker compose ... exec -T application php artisan schedule-monitor:list
```

---

## WebSocket / Console issues

1. Confirm `socket` container running on port `38000`
2. Check `apps/fleetbase/console/fleetbase.config.json`:
   - `API_HOST`: `http://localhost:8000`
   - `SOCKETCLUSTER_HOST`: `localhost`
   - `SOCKETCLUSTER_PORT`: `38000`
3. Verify `SOCKETCLUSTER_OPTIONS` origins in `docker-compose.override.yml` include `localhost`

Restart console + socket:

```bash
docker compose ... restart socket console
```

---

## Routing (OSRM / Valhalla)

| Engine         | When to use                                         |
| -------------- | --------------------------------------------------- |
| OSRM public    | Default; no local setup                             |
| Valhalla local | Start Porterchain routing: `pnpm docker:up:routing` |

Application env (via override): `VALHALLA_BASE_URL=http://host.docker.internal:8002`

Test Valhalla: `curl http://127.0.0.1:8002/status`

---

## Porterchain bridge

Porterchain API syncs orders to Fleetbase — **merchants never call Fleetbase directly**.

| Porterchain env                  | Purpose                   |
| -------------------------------- | ------------------------- |
| `FLEETBASE_API_URL`              | `http://localhost:8000`   |
| `FLEETBASE_DISPATCH_BRIDGE`      | `true`                    |
| `FLEETBASE_DEFAULT_COMPANY_UUID` | From Fleetbase onboarding |

Verify bridge (Porterchain API running):

```bash
curl http://localhost:8001/health
# Create test merchant booking — order should reach DISPATCH_READY + Fleetbase sync
```

---

## Port conflicts

| Port              | Owner                              | Resolution                                                                     |
| ----------------- | ---------------------------------- | ------------------------------------------------------------------------------ |
| 3306              | Porterchain MySQL OR legacy stacks | Fleetbase uses **3307** on host                                                |
| 8000, 4200, 38000 | Must be Fleetbase                  | Stop other stacks: `docker ps` → identify → `docker compose -p <project> down` |

Legacy install detected at `/Users/ravi/Documents/GitHub/PC/PC` (project `pc`) — stop before starting PCD Fleetbase.

---

## Backup

### MySQL

```bash
docker exec porterchain-fleetbase-mysql mysqldump -uroot -p<ROOT_PASS> \
  --databases fleetbase fleetbase_sandbox > fleetbase-backup-$(date +%F).sql
```

### Storage volume

```bash
docker run --rm -v porterchain-fleetbase-api-storage:/data -v $(pwd):/backup alpine \
  tar czf /backup/fleetbase-storage-$(date +%F).tar.gz -C /data .
```

---

## Incident response

| Symptom              | Action                                                                     |
| -------------------- | -------------------------------------------------------------------------- |
| API 502              | Check `application` + `httpd` logs; restart both                           |
| Migrations failed    | Grant MySQL privileges (install script step 6b); fresh volume if corrupted |
| Queue backlog        | Scale queue workers (duplicate `queue` service in override for prod)       |
| Console blank        | Rebuild console: `docker compose ... up -d --build console`                |
| Dispatch not syncing | Verify Porterchain `FLEETBASE_*` env + company UUID                        |

---

## Escalation

- Fleetbase upstream issues: https://github.com/fleetbase/fleetbase/issues
- Porterchain bridge: `apps/api/src/porterchain_api/booking_engine/fleetbase_sync_service.py`
- Do **not** patch Fleetbase core — extend via Porterchain API layer only

---

## Related

- [FLEETBASE_INSTALL.md](./FLEETBASE_INSTALL.md)
- [DOCKER_SETUP.md](./DOCKER_SETUP.md)
- [SERVICE_STATUS.md](./SERVICE_STATUS.md)
