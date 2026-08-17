# Backup & restore — Porterchain Postgres (§5.1.7, §5.1.15, DD-28)

**Type:** CANONICAL  
**Checklist:** [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md)  
**Last verified:** 2026-07-08

Porterchain **business data** lives in Postgres (`orders`, `merchants`, `quotes`, …). Fleetbase MySQL + volumes are separate — see [RUNBOOK.md](../RUNBOOK.md) § Backup.

## Scripts

| Script                                                          | Purpose                                        |
| --------------------------------------------------------------- | ---------------------------------------------- |
| `infrastructure/deploy/scripts/backup-porterchain-postgres.sh`  | `pg_dump` → gzip                               |
| `infrastructure/deploy/scripts/restore-porterchain-postgres.sh` | Restore drill (requires `CONFIRM_RESTORE=yes`) |

### Local dev (docker-compose core)

```bash
COMPOSE_FILE=infrastructure/docker/docker-compose.yml \
  POSTGRES_SERVICE=postgres \
  ./infrastructure/deploy/scripts/backup-porterchain-postgres.sh
```

### Production droplet

```bash
cd /opt/porterchain
./infrastructure/deploy/scripts/backup-porterchain-postgres.sh /var/backups/porterchain-$(date +%F).sql.gz
```

Store off-droplet: S3-compatible object storage or DO Spaces with encryption at rest.

## Quarterly restore drill (DD-28)

**Cadence:** first week of each quarter (Jan / Apr / Jul / Oct).  
**Owner:** on-call engineer.  
**Duration target:** <60 minutes including verification.

| Step | Action                                                                            | Pass                    |
| ---- | --------------------------------------------------------------------------------- | ----------------------- |
| 1    | Run backup script on staging or isolated restore VM                               | `.sql.gz` file >0 bytes |
| 2    | `CONFIRM_RESTORE=yes ./restore-porterchain-postgres.sh <file>` on **non-prod** DB | psql completes          |
| 3    | `pnpm db:migrate` (head)                                                          | no pending errors       |
| 4    | `curl -fsS http://localhost:8001/health/ready`                                    | `status: ok`            |
| 5    | `pnpm validate:p0:fast`                                                           | green                   |
| 6    | Log drill date + operator in ops channel                                          | ticket closed           |

**Never** point restore at production without explicit change window and `CONFIRM_RESTORE=yes`.

## Retention

| Environment | Retention             | Notes                                              |
| ----------- | --------------------- | -------------------------------------------------- |
| Production  | 30 daily + 12 monthly | Automate via cron on droplet or managed PG backups |
| Local       | optional              | Delete `backups/` after drill                      |

## Verification in CI

```bash
pnpm validate:golden-rules   # includes verify_backup_restore_doc.py
```
