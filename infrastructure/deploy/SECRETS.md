# PorterChain secrets (SOPS + age)

**Canonical inventory:** [`docs/SECRETS_MAP.md`](../../docs/SECRETS_MAP.md).
**SSOT store:** `secrets/droplet.enc.yaml`, encrypted with SOPS for the age recipients in `.sops.yaml` (doc 37).
Deploy: `.github/actions/stage-sops-env` decrypts on the Actions runner with the `SOPS_AGE_KEY` GitHub secret, copies `runtime.env` to the droplet, and `sync-secrets.sh` turns it into `.env`.

## Setting keys

| Command                                                                                                | What it does                             |
| ------------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| `sops secrets/droplet.enc.yaml`                                                                        | Edit the file in `$EDITOR` (re-encrypts) |
| `bash scripts/secrets/sops-set-from-env.sh droplet <local.env>`                                        | Copy every non-empty `KEY=value` into it |
| `bash scripts/secrets/sops-set-from-env.sh droplet infrastructure/deploy/scripts/mail-keys.local.env`  | ZeptoMail HTTPS keys                     |
| `bash scripts/secrets/sops-set-from-env.sh droplet infrastructure/deploy/scripts/leads-keys.local.env` | Lead webhook / CAPI / territory keys     |

Generate a new shared secret with `openssl rand -hex 32`. Values are never printed by these scripts.

## Interac e-Transfer inbox (optional)

Read-only IMAP pull of Interac notifications into Admin → Finance → Interac (proposals only; an admin approves every payment). Off unless `INTERAC_IMAP_ENABLED=true` and host, user and password are set. Passed to `api` and `worker` in `docker-compose.prod.yml`.

| Key                          | Value / notes                                          |
| ---------------------------- | ------------------------------------------------------ |
| `INTERAC_IMAP_ENABLED`       | `true` to turn the reader on                           |
| `INTERAC_IMAP_HOST`          | `imap.gmail.com`                                       |
| `INTERAC_IMAP_PORT`          | `993`                                                  |
| `INTERAC_IMAP_USER`          | `porterchaininc@gmail.com`                             |
| `INTERAC_IMAP_PASSWORD`      | Gmail app password (2-Step Verification on); secret    |
| `INTERAC_AUTHSERV_ID`        | `mx.google.com` (Gmail's Authentication-Results stamp) |
| `INTERAC_IMAP_FOLDER`        | Optional, default `INBOX`                              |
| `INTERAC_IMAP_LOOKBACK_DAYS` | Optional, default `60`                                 |

## Lead ingest bus (optional until channel goes live)

Set in `secrets/droplet.enc.yaml` when you enable that channel. Empty = webhook/CAPI stays dark (safe).

| Key                          | Purpose                                  | Callback / notes                                                         |
| ---------------------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| `PUBLIC_INGEST_API_KEY`      | Website → API inquiries                  | Website server env must match                                            |
| `META_APP_SECRET`            | Meta Lead Ads / WA / IG HMAC             | `GET/POST /v1/public/leads/webhooks/meta`                                |
| `META_WEBHOOK_VERIFY_TOKEN`  | Meta hub challenge                       | Same path                                                                |
| `GOOGLE_LEAD_WEBHOOK_SECRET` | Google Ads / GBP                         | `POST /v1/public/leads/webhooks/google` · header `X-Lead-Webhook-Secret` |
| `SOCIAL_LEAD_WEBHOOK_SECRET` | LinkedIn / X / YouTube                   | `/v1/public/leads/webhooks/{linkedin,x,youtube}` · same header           |
| `META_CAPI_ACCESS_TOKEN`     | Meta CRM offline convert                 | Fired on lead convert                                                    |
| `META_PIXEL_ID`              | Meta CAPI pixel                          | Pair with token                                                          |
| `LINKEDIN_CAPI_TOKEN`        | LinkedIn Conversions API                 | Fired on lead convert                                                    |
| `LINKEDIN_CONVERSION_URN`    | `urn:lla:llaPartnerConversion:…`         | Required with LinkedIn token                                             |
| `LEAD_TERRITORY_MAP_JSON`    | `{"ON":"<admin_user_id>","DEFAULT":"…"}` | Auto-assign on ingest                                                    |
| `LEAD_ROUND_ROBIN_JSON`      | `["admin_id_1","admin_id_2"]`            | Fallback assignee pool when territory misses                             |
| `LEAD_SLA_MINUTES_JSON`      | `{"whatsapp":15,"default":60}`           | First-response SLA by channel                                            |
| `LEAD_INGEST_ASYNC`          | `true` / `false` (default false)         | Redis WEBHOOKS queue for hot Meta/Google/social ingest                   |
| `REFERRAL_CREDIT_CENTS`      | Merchant referral reward (default 25000) | Granted on referred convert                                              |

### Setting lead keys (no values printed)

```bash
cp infrastructure/deploy/scripts/leads-keys.local.env.example infrastructure/deploy/scripts/leads-keys.local.env
# fill values, then
bash scripts/secrets/sops-set-from-env.sh droplet infrastructure/deploy/scripts/leads-keys.local.env
```

Admin Settings → Connections → Lead Ingest shows configured / not configured and checks new
values, then lists the keys to set with `sops`. The API cannot write the SOPS file. Secret
values are never shown in the UI.
