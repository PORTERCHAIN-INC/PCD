# PorterChain secrets (Doppler)

**Canonical inventory:** [`docs/SECRETS_MAP.md`](../../docs/SECRETS_MAP.md).  
**SSOT store:** Doppler project `pcd` / config `prd` (`doppler.yaml`).  
Sync to droplet: `infrastructure/deploy/sync-secrets.sh` (prefers runner-staged `doppler.env`).

## Upload helpers

| Script                                | What it sets                                        |
| ------------------------------------- | --------------------------------------------------- |
| `scripts/upload-clerk-to-doppler.sh`  | Clerk platform + driver keys                        |
| `scripts/upload-ingest-to-doppler.sh` | `PUBLIC_INGEST_API_KEY` (generate if missing)       |
| `scripts/upload-leads-to-doppler.sh`  | Lead webhook / CAPI / territory keys from local env |
| `scripts/upload-mail-to-doppler.sh`   | ZeptoMail HTTPS (`mail-keys.local.env`)             |

## Lead ingest bus (optional until channel goes live)

Set in Doppler when you enable that channel. Empty = webhook/CAPI stays dark (safe).

| Key                                                   | Purpose                                  | Callback / notes                                                         |
| ----------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| `PUBLIC_INGEST_API_KEY`                               | Website → API inquiries                  | Website server env must match                                            |
| `META_APP_SECRET`                                     | Meta Lead Ads / WA / IG HMAC             | `GET/POST /v1/public/leads/webhooks/meta`                                |
| `META_WEBHOOK_VERIFY_TOKEN`                           | Meta hub challenge                       | Same path                                                                |
| `GOOGLE_LEAD_WEBHOOK_SECRET`                          | Google Ads / GBP                         | `POST /v1/public/leads/webhooks/google` · header `X-Lead-Webhook-Secret` |
| `SOCIAL_LEAD_WEBHOOK_SECRET`                          | LinkedIn / X / YouTube                   | `/v1/public/leads/webhooks/{linkedin,x,youtube}` · same header           |
| `META_CAPI_ACCESS_TOKEN`                              | Meta CRM offline convert                 | Fired on lead convert                                                    |
| `META_PIXEL_ID`                                       | Meta CAPI pixel                          | Pair with token                                                          |
| `LINKEDIN_CAPI_TOKEN`                                 | LinkedIn Conversions API                 | Fired on lead convert                                                    |
| `LINKEDIN_CONVERSION_URN`                             | `urn:lla:llaPartnerConversion:…`         | Required with LinkedIn token                                             |
| `LEAD_TERRITORY_MAP_JSON`                             | `{"ON":"<admin_user_id>","DEFAULT":"…"}` | Auto-assign on ingest                                                    |
| `LEAD_ROUND_ROBIN_JSON`                               | `["admin_id_1","admin_id_2"]`            | Fallback assignee pool when territory misses                             |
| `LEAD_SLA_MINUTES_JSON`                               | `{"whatsapp":15,"default":60}`           | First-response SLA by channel                                            |
| `LEAD_INGEST_ASYNC`                                   | `true` / `false` (default false)         | Redis WEBHOOKS queue for hot Meta/Google/social ingest                   |
| `REFERRAL_CREDIT_CENTS`                               | Merchant referral reward (default 25000) | Granted on referred convert                                              |
| `NVIDIA_API_KEY` / `NVIDIA_API_BASE` / `NVIDIA_MODEL` | Lead Assist (NIM)                        | Already documented in `env/api.env.example`                              |

### Local dry-run (no values printed)

```bash
# Generate shared webhook secrets if missing, upload any LEAD_* keys present in apps/api/.env
bash infrastructure/deploy/scripts/upload-leads-to-doppler.sh

# Or point at a gitignored file:
LEADS_ENV=infrastructure/deploy/scripts/leads-keys.local.env \
  bash infrastructure/deploy/scripts/upload-leads-to-doppler.sh
```

Admin Settings → Connections → Lead Ingest can write these keys to Doppler when
`DOPPLER_TOKEN` is present on the API (service token). Secret values are never
shown in the UI — only configured/not configured.
