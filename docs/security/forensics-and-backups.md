# Forensic readiness, backups and restore

## Nightly (systemd `porterchain-postgres-backup.timer`, 07:15 UTC)

`/opt/porterchain/scripts/backup-offsite-postgres.sh` with `/opt/porterchain/backup.env`:

1. `pg_dump -Fc` of `porterchain` and `spicedb`, TOC validated, sha256 recorded.
2. Encrypted with **age** to the recipient(s) in `/opt/porterchain/backup-age-recipients.txt`.
   The private key is **not** on the server (owner keeps it offline: password manager + 2nd copy).
3. Evidence bundle: signed audit checkpoint, full audit-chain export, Caddy access logs, host
   auth log, time-sync status, `SHA256SUMS` → tar.gz → age.
4. Upload to `OFFSITE_TARGET`. Until off-site credentials exist it is
   `file:///var/backups/porterchain` (same droplet, encrypted). To go off-site set ONE variable,
   e.g. `OFFSITE_TARGET=s3://porterchain-db-backups/postgres` (+ bucket key vars) or
   `OFFSITE_TARGET=rclone:offsite:porterchain-db-backups/postgres`.
5. Retention: dumps daily 14 days + monthly 12 months; evidence bundles 400 days.

## Restore (tested 2026-10-10)

```bash
age -d -i ~/.porterchain/backup-age.key porterchain-porterchain-<STAMP>.dump.age > db.dump
sha256sum db.dump    # compare with the .sha256 file
createdb restored && pg_restore --no-owner --no-acl -d restored db.dump
```

Production rollback of a whole DB: `infrastructure/deploy/scripts/restore-porterchain-postgres.sh`.

## Audit chain

- Verify: `docker compose exec -T api python -m porterchain_api.forensics_cli verify`
- Checkpoint: `... forensics_cli checkpoint` (needs `AUDIT_SIGNING_KEY`, Ed25519, in the API env)
- Export: `... forensics_cli export > audit.json`
- Deploys record `deploy` events automatically (deploy workflow).
