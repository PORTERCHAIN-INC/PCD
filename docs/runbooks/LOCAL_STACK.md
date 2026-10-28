# Persistent local stack on Ubuntu (copy of live data)

Isolated from live: own Postgres/Redis/SpiceDB/Mailpit, outbound sweeps paused, SMS/push have no
credentials, webhooks/FCM/Shopify tokens scrubbed on the copy. Files live in `/home/pcd/pcd-local`
(chmod 700, not in git): `compose.yml`, `.env` and `app.env` (chmod 600), `with-env.sh`, `logs/`.

| Service                    | URL                                                                       |
| -------------------------- | ------------------------------------------------------------------------- |
| Website                    | http://192.168.2.103:13100                                                |
| Merchant portal            | http://192.168.2.103:13101 (dev bypass = merchant@porterchain.com, owner) |
| Admin                      | http://192.168.2.103:13102 → "Continue as Local Super Admin"              |
| Driver portal              | http://192.168.2.103:13103 (dev bypass)                                   |
| Customer portal            | http://192.168.2.103:13104 (dev bypass)                                   |
| API                        | http://192.168.2.103:18100 (`/docs`, `Authorization: Bearer dev`)         |
| Mailpit UI                 | http://192.168.2.103:58125 (no relay)                                     |
| Postgres / Redis / SpiceDB | 127.0.0.1:55632 / 56679 / 55251 (localhost only)                          |

Infra runs in docker compose project `pcd-local` (`restart: unless-stopped`); apps run as systemd
user units under `pcd-local.target` (`Restart=always`, linger on, so they start at boot).

```bash
# status
systemctl --user status 'pcd-local-*' --no-pager; docker compose -p pcd-local ps
# stop everything
systemctl --user stop pcd-local.target 'pcd-local-*'; cd ~/pcd-local && docker compose stop
# start everything
cd ~/pcd-local && docker compose up -d && systemctl --user start pcd-local.target
# one app
systemctl --user restart pcd-local-api   # api worker website merchant admin driver customer
tail -f ~/pcd-local/logs/api.log
# migrations / scripts against the copy
cd ~/PCD/apps/api && ~/pcd-local/with-env.sh .venv/bin/alembic upgrade head
# remove completely (data volumes too)
systemctl --user disable --now pcd-local.target 'pcd-local-*'; cd ~/pcd-local && docker compose down -v
```

Refresh from live (read-only dump): `docker exec porterchain-postgres pg_dump -U porterchain -d porterchain -Fc --no-owner > ~/pcd-local/live.dump`,
then drop/recreate `porterchain` in `pcd-local-pg`, `pg_restore`, re-run the scrub SQL (webhook URLs,
FCM tokens, Shopify tokens), `alembic upgrade head`, and `python -m porterchain_api.authz.bootstrap`.

Paused sweeps are listed in `WORKER_PAUSED_SWEEPS` in `app.env`; remove a name and restart
`pcd-local-worker` to enable it. Merchant/driver/customer use the Clerk dev bypass (no Clerk test
keys exist on this machine); add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`/`CLERK_SECRET_KEY` test keys
to `app.env` to test real sign-in.
