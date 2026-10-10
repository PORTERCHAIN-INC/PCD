# Postgres off-site backup & restore runbook

Owner: ops · Applies to: production droplet (`/opt/porterchain`) · Added: readiness audit #4 (Oct 2026)

## What runs

| Piece                      | Path                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------- |
| Backup script              | `infrastructure/deploy/scripts/backup-offsite-postgres.sh` → `/opt/porterchain/scripts/`          |
| Restore script             | `infrastructure/deploy/scripts/restore-offsite-postgres.sh`                                       |
| Config (no secrets in git) | `infrastructure/deploy/backup.env.example` → `/opt/porterchain/backup.env` (chmod 600)            |
| Schedule                   | `systemd/porterchain-postgres-backup.{service,timer}` — daily 07:15 UTC (03:15 Toronto)           |
| Alternative                | `docker-compose.backup.example.yml` (one-shot container) + cron lines in its header               |
| Existing on-box dump       | `scripts/backup-porterchain-postgres.sh` (plain gzip, local only) — keep for pre-deploy snapshots |

Pipeline per database (`porterchain`, `spicedb`):
`pg_dump -Fc` (inside the postgres container, so client = server major version) → `pg_restore --list`
sanity check → SHA-256 of the plaintext → **encrypt** (age public key, or gpg) → upload `.dump.age`

- `.dump.sha256` → prune off-site copies (keep all for 14 days + 1st-of-month for 12 months) → prune
  local work dir (3 days) → optional heartbeat ping. The script refuses to run without encryption.

RPO: 24 h (daily). For tighter RPO enable WAL archiving (pgBackRest/wal-g) later.
RTO target: < 1 h for the current DB size (drill: ~75 KB dump restores in ~1 s locally).

## One-time setup on the droplet (manual)

1. Create a bucket at a **different provider/region** than the droplet (Cloudflare R2, Backblaze B2, or
   DO Spaces in another region). Turn on versioning/object lock if offered.
2. Create an access key scoped to that bucket only. Put it in `/opt/porterchain/backup.env`
   (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `OFFSITE_TARGET`).
3. Encryption keys — on a trusted laptop, not the droplet:
   `age-keygen -o porterchain-backup.key` → store the private key in the password manager **and** a
   second offline location. Copy only the public line (`age1…`) to `/opt/porterchain/backup-age-recipients.txt`.
4. Install tools: `apt-get install -y age awscli` (or `rclone`).
5. Copy scripts + units:
   ```bash
   install -m 755 infrastructure/deploy/scripts/{backup,restore}-offsite-postgres.sh infrastructure/deploy/scripts/deploy-paths.sh /opt/porterchain/scripts/
   install -m 644 infrastructure/deploy/systemd/porterchain-postgres-backup.{service,timer} /etc/systemd/system/
   systemctl daemon-reload && systemctl enable --now porterchain-postgres-backup.timer
   ```
6. First run by hand and watch it: `systemctl start porterchain-postgres-backup.service && journalctl -u porterchain-postgres-backup -n 50`.
7. Set `BACKUP_HEARTBEAT_URL` (healthchecks.io or similar) so a missed night alerts.

## Restore (verify) — safe, never touches live data

```bash
set -a; . /opt/porterchain/backup.env; set +a
export AGE_IDENTITY_FILE=/root/porterchain-backup.key   # copied in temporarily, shred afterwards
aws s3 ls ${S3_ENDPOINT_URL:+--endpoint-url $S3_ENDPOINT_URL} "$OFFSITE_TARGET/" | tail
/opt/porterchain/scripts/restore-offsite-postgres.sh porterchain-porterchain-20261009T071500Z.dump.age
# -> restores into porterchain_restore_check, prints table count + alembic version
shred -u /root/porterchain-backup.key
```

Spot-check: `select count(*) from orders; select max(created_at) from orders;` in `porterchain_restore_check`,
then `DROP DATABASE porterchain_restore_check;`.

## Restore (disaster) — promote a verified copy

1. Announce maintenance; stop writers: `docker compose -f docker-compose.prod.yml stop api worker`.
2. Snapshot what is there now: `scripts/backup-porterchain-postgres.sh` (even if damaged).
3. Restore to a side DB as above (`… <file> porterchain_restore`).
4. Swap names (same pattern as `restore-porterchain-postgres.sh`):
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='porterchain' AND pid<>pg_backend_pid();
   ALTER DATABASE porterchain RENAME TO porterchain_old;
   ALTER DATABASE porterchain_restore RENAME TO porterchain;
   ```
5. `alembic upgrade head` if the backup predates the deployed code; start api/worker; smoke test
   (`/health`, admin orders list, a quote preview).
6. Keep `porterchain_old` for 7 days, then drop. Repeat for `spicedb` if needed.
7. Whole-droplet loss: provision via `bootstrap-droplet.sh`, bring up postgres only, then steps 3–5.

## Drill log

| Date       | Who                          | Result                                                                                                                                                                                                                                                                                                                                                                                            |
| ---------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-10-09 | readiness fixes (local only) | gpg-symmetric + file target: `porterchain_review` → `porterchain_review_restore_drill`, 93 tables, alembic `fx0retirefleet5e6f`, orders 13 = 13. age + `BACKUP_SOURCE=url` in a Linux container (as in the compose snippet) against a throwaway PG18: OK; retention pruned a mid-month object >14 d and kept the 1st-of-month one. Plaintext refused without a key. **Not run against production.** |

Run a restore drill quarterly and after any Postgres major upgrade (prod is still PG16).
