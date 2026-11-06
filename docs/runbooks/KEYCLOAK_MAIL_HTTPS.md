# Keycloak mail over ZeptoMail HTTPS (DigitalOcean)

## Why

DigitalOcean Droplets block outbound SMTP (ports 25/465/587) by default. Keycloak
only sends mail via SMTP. The PorterChain API already uses ZeptoMail’s HTTPS API
(`MAIL_TRANSPORT=https` → `https://api.zeptomail.ca/v1.1/email` on port 443).

**Permanent fix:** run `pcd-kc-mail-relay` next to Keycloak. Keycloak SMTP points at
the relay on the Docker network; the relay POSTs to ZeptoMail HTTPS. No DigitalOcean
SMTP unblock ticket required. App mail is unchanged.

## Pieces

| Piece                  | Path                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------- |
| Relay                  | `infrastructure/keycloak/mail-relay/` (Python + aiosmtpd)                           |
| Compose                | `infrastructure/keycloak/deploy/docker-compose.keycloak.yml` (service `mail-relay`) |
| Secrets (droplet only) | `/opt/porterchain/secrets/keycloak-mail-relay.env` — never commit                   |
| Realm SMTP apply       | `KC_MAIL_PROVIDER=zeptomail_https bash scripts/keycloak-email-otp-setup.sh`         |

## Droplet hand-deploy (no KC_WIPE)

1. **Fresh Postgres backup** (Keycloak DB lives in `pcd-postgres`):

   ```bash
   ssh porterchain-droplet 'bash /opt/porterchain/scripts/backup-porterchain-postgres.sh'
   ```

2. **Create relay secrets** from the running API env (do not print values):

   ```bash
   ssh porterchain-droplet 'umask 077
     API=porterchain-prod-api-1
     OUT=/opt/porterchain/secrets/keycloak-mail-relay.env
     {
       echo "# generated $(date -u +%Y-%m-%dT%H:%M:%SZ) — do not commit"
       docker exec "$API" printenv MAIL_PASSWORD | sed "s/^/MAIL_PASSWORD=/"
       docker exec "$API" printenv ZEPTOMAIL_API_URL | sed "s/^/ZEPTOMAIL_API_URL=/"
       docker exec "$API" printenv MAIL_FROM_ADDRESS | sed "s/^/MAIL_FROM_ADDRESS=/"
       docker exec "$API" printenv MAIL_FROM_NAME | sed "s/^/MAIL_FROM_NAME=/"
     } > "$OUT"
     chmod 600 "$OUT"
     # verify keys exist without dumping secrets
     awk -F= "{print \$1\"=set_len=\"length(\$2)}" "$OUT"
   '
   ```

3. **Sync compose + relay sources** to `/opt/porterchain/keycloak/` (mail-relay/ +
   docker-compose.keycloak.yml from this branch), then:

   ```bash
   ssh porterchain-droplet 'cd /opt/porterchain/keycloak
     docker compose -f docker-compose.keycloak.yml build mail-relay
     docker compose -f docker-compose.keycloak.yml up -d mail-relay
     docker compose -f docker-compose.keycloak.yml up -d keycloak
     docker logs --tail 20 pcd-kc-mail-relay
   '
   ```

4. **Point realm SMTP at the relay** (idempotent; does not recreate Keycloak):

   ```bash
   ssh porterchain-droplet 'KC_MAIL_PROVIDER=zeptomail_https KC_CONTAINER=pcd-keycloak \
     KC_SMTP_FROM=no-reply@porterchain.com \
     bash /opt/porterchain/keycloak/../scripts/keycloak-email-otp-setup.sh'
   ```

   Or apply SMTP only via kcadm:

   ```bash
   docker exec pcd-keycloak bash -lc '
     /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 \
       --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"
     /opt/keycloak/bin/kcadm.sh update realms/porterchain \
       -s emailTheme=porterchain \
       -s smtpServer.host=pcd-kc-mail-relay -s smtpServer.port=1025 \
       -s smtpServer.from=no-reply@porterchain.com \
       -s smtpServer.fromDisplayName=Porterchain \
       -s smtpServer.auth=false -s smtpServer.starttls=false -s smtpServer.ssl=false \
       -s "smtpServer.user=" -s "smtpServer.password="
   '
   ```

5. **Test send** (replace USER_ID; prefer a test inbox):

   ```bash
   docker exec pcd-keycloak bash -lc '
     /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 \
       --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"
     /opt/keycloak/bin/kcadm.sh create users/"$USER_ID"/execute-actions-email \
       -r porterchain -b "[\"UPDATE_PASSWORD\"]"
   '
   docker logs --tail 50 pcd-kc-mail-relay
   docker logs --tail 50 pcd-keycloak 2>&1 | grep -iE "smtp|email|mail|error" | tail -20
   ```

   Or use the public forgot-password form on https://auth.porterchain.com for
   `iot.ravichauhan@gmail.com` and confirm the relay log shows `forwarded to=… status=201`.

## Local stack

Keep `KC_MAIL_PROVIDER=mailpit`. The HTTPS relay is production-only.

## Rollback

Point realm SMTP back to empty / disable reset emails, then
`docker compose … stop mail-relay`. App `MAIL_TRANSPORT=https` is independent.

## Security

- Relay has **no published host ports** — only Docker network peers can submit SMTP.
- Token file mode `600`, owned by deploy user; never commit `keycloak-mail-relay.env`.
- Do not log `MAIL_PASSWORD` or ZeptoMail response bodies that echo credentials.
