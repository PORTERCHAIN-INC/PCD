# Production rollback runbook

Production is one DigitalOcean droplet (`/opt/porterchain`, `docker-compose.prod.yml`).
Every image in GHCR is tagged with the full commit SHA it was built from:
`ghcr.io/porterchain-inc/pcd-{api,website,admin,merchant,driver,customer}:<sha>`.
The worker runs the `pcd-api` image.

## What happens automatically

| Deploy type                 | Rollback point recorded                                                                         | Rolled back automatically when                                                                   |
| --------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Full (`rollout: full`)      | `backups/pre-migrate-latest.manifest`: running images + Postgres dump                           | migrate fails, API unhealthy, internal smoke fails, public smoke fails, worker heartbeat fails   |
| Scoped (`rollout: partial`) | `backups/pre-partial-latest.manifest`: running images (+ Postgres dump when the scope migrates) | scoped deploy step fails after the snapshot, any scoped/core smoke fails, worker heartbeat fails |

After every deploy the droplet keeps, per service, the running image, the image
named in each `pre-*-latest.manifest`, and one older tag. Everything else is pruned.

If an automatic rollback ran, the Deploy run is red and its last step says
`Rollback complete from <manifest>`. Production is then on the previous release.

## Manual rollback (images only, no DB change)

Use when a release is bad but its migration (if any) is backwards compatible.

1. SSH to the droplet: `ssh porterchain-droplet`, then `cd /opt/porterchain`.
2. See what is running and what is available:
   ```bash
   docker ps --format '{{.Names}}\t{{.Image}}'
   docker images --format '{{.Repository}}:{{.Tag}} {{.CreatedSince}}' | grep pcd-
   cat backups/pre-partial-latest.manifest backups/pre-migrate-latest.manifest
   ```
3. Write an images-only manifest (no `DUMP=` line) with all six refs, e.g.
   `backups/manual-rollback.manifest`:
   ```
   API_IMAGE=ghcr.io/porterchain-inc/pcd-api:<good-sha>
   WEB_IMAGE=ghcr.io/porterchain-inc/pcd-website:<good-sha>
   ADMIN_IMAGE=ghcr.io/porterchain-inc/pcd-admin:<good-sha>
   MERCHANT_IMAGE=ghcr.io/porterchain-inc/pcd-merchant:<good-sha>
   DRIVER_IMAGE=ghcr.io/porterchain-inc/pcd-driver:<good-sha>
   CUSTOMER_IMAGE=ghcr.io/porterchain-inc/pcd-customer:<good-sha>
   ```
   Each service may have a different SHA (scoped deploys only rebuild some images).
   A tag that was pruned locally is pulled from GHCR (needs `docker login ghcr.io`).
4. Run: `CONFIRM_RESTORE=yes bash scripts/rollback-prod.sh backups/manual-rollback.manifest`
5. Verify (below).

## Manual rollback including the database

Only when a migration broke data or schema. This **loses writes made since the
dump** (orders, scans, emails logged). Get Ravi's OK first.

```bash
CONFIRM_RESTORE=yes bash scripts/rollback-prod.sh backups/pre-migrate-latest.manifest
```

The three newest dumps are kept in `backups/pre-migrate-*.sql.gz`.

## Verify after any rollback

```bash
curl -fsS https://api.porterchain.com/health          # {"status":"ok"}
curl -fsS -o /dev/null -w '%{http_code}\n' https://api.porterchain.com/health/ready   # 200
for u in https://porterchain.com/en https://porterchain.com/en/track \
         https://admin.porterchain.com/sign-in https://driver.porterchain.com/login \
         https://merchant.porterchain.com/login https://customer.porterchain.com/login; do
  curl -s -o /dev/null -w "%{http_code} $u\n" "$u"; done
docker inspect -f '{{.State.Health.Status}}' pcd-worker   # healthy
```

## Then fix forward

Revert the bad commit with a normal PR (`git revert <sha>`). CI must pass, and the
merge redeploys automatically. Never push to main directly or dispatch a deploy
of an untested SHA: the Deploy workflow refuses manual runs unless the SHA is on
main and CI passed for that exact SHA.
