# Zoho Mail — Development & Production

**Type:** CANONICAL  
**Last verified:** 2026-07-13  
**Region:** Zoho **Canada** (`*.zohocloud.ca` / `*.zoho.ca`)  
**Domain:** `porterchain.com`

**Authority:** Notification Engine SMTP (`delivery_service.py`) · `porterchain_shared` `MAIL_*` settings  
**See also:** [NOTIFICATION_ARCHITECTURE.md](./NOTIFICATION_ARCHITECTURE.md) · [ENVIRONMENT_VARIABLES.md](../../ENVIRONMENT_VARIABLES.md) · [SECRETS_MAP.md](../SECRETS_MAP.md)

---

## Principle

| Environment    | Outbound email                                                                              |
| -------------- | ------------------------------------------------------------------------------------------- |
| **Local / CI** | **Mailpit** — never put live send-mail tokens in local `.env` committed or shared           |
| **Production** | **ZeptoMail SMTP** (`smtp.zeptomail.ca`, user `emailapikey`) via Doppler / droplet `MAIL_*` |

Human Zoho Mailboxes (`mail.zoho.ca`) remain for inbox/IMAP. **Transactional send** uses ZeptoMail SMTP.

Auth for portals remains **Clerk-only**. Mail is for **transactional + human mailboxes**, not login.

---

## Mailboxes & aliases (`@porterchain.com`)

Configure each address in Zoho Mail Admin (users and/or aliases / group addresses). All examples below use the live domain.

| Address                    | Role                  | Typical use                                                         |
| -------------------------- | --------------------- | ------------------------------------------------------------------- |
| `peter@porterchain.com`    | Founder / exec        | Human inbox; not default app From                                   |
| `ravi@porterchain.com`     | Engineering / founder | Human inbox; optional app From (`MAIL_FROM_ADDRESS3`)               |
| `billing@porterchain.com`  | Finance               | Invoices, receipts, AR follow-up                                    |
| `no-reply@porterchain.com` | System                | Automated notices where replies are not expected                    |
| `ops@porterchain.com`      | Operations            | **Default app From** (`MAIL_FROM_ADDRESS`); dispatch / capacity ops |
| `sales@porterchain.com`    | Commercial            | Quotes, CRM outbound (`MAIL_FROM_ADDRESS2`)                         |
| `support@porterchain.com`  | Support               | Customer tickets, recovery mail                                     |

**Zoho requirement:** for SMTP to send _as_ an alias, enable **Send Mail As** (or equivalent) for that address on the authenticated mailbox. SPF / DKIM / DMARC for `porterchain.com` must stay aligned with Zoho’s published records.

---

## Server settings (Canada DC)

### SMTP outgoing — apps (ZeptoMail transactional)

| Setting           | Value                                                         |
| ----------------- | ------------------------------------------------------------- |
| Host              | `smtp.zeptomail.ca`                                           |
| Port + encryption | **587 + STARTTLS** (preferred) **or** 465 + SSL               |
| Authentication    | Yes                                                           |
| Username          | `emailapikey` (literal)                                       |
| Password          | ZeptoMail **Send Mail Token** (not the Zoho mailbox password) |
| From              | Verified sender, e.g. `noreply@porterchain.com`               |

Upload to Doppler: `bash infrastructure/deploy/scripts/upload-mail-to-doppler.sh`

### Zoho Mail SMTP (human clients — optional)

| Setting           | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Host              | `smtp.zohocloud.ca`                                         |
| Port + encryption | **465 + SSL** **or** 587 + TLS                              |
| Username          | Full address, e.g. `ops@porterchain.com`                    |
| Password          | Zoho account password **or** Zoho **app-specific password** |

### IMAP (incoming — mail clients / tools)

| Setting  | Value                 |
| -------- | --------------------- |
| Host     | `imap.zohocloud.ca`   |
| Port     | `993`                 |
| SSL      | Yes                   |
| Username | `you@porterchain.com` |

### POP (incoming — optional)

| Setting  | Value                 |
| -------- | --------------------- |
| Host     | `pop.zohocloud.ca`    |
| Port     | `995`                 |
| SSL      | Yes                   |
| Username | `you@porterchain.com` |

Web / admin consoles (Canada): `https://mail.zoho.ca` · API console `https://api-console.zohocloud.ca`

---

## Development (local)

### Default: Mailpit (recommended)

Stack rule: local transactional email goes through **Mailpit**, not Zoho.

| Service | Endpoint                   |
| ------- | -------------------------- |
| SMTP    | `localhost:1025` (no auth) |
| UI      | http://localhost:8025      |

```bash
pnpm docker:up   # starts Mailpit (see infrastructure/docker/docker-compose.yml)
```

**Local API env** (`env/api.env` or `apps/api` env — do **not** commit secrets):

```env
# Local: capture all mail in Mailpit
MAIL_MAILER=smtp
MAIL_HOST=localhost
MAIL_PORT=1025
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_ENCRYPTION=
MAIL_FROM_ADDRESS=ops@porterchain.com
MAIL_FROM_ADDRESS2=sales@porterchain.com
MAIL_FROM_ADDRESS3=ravi@porterchain.com
MAIL_FROM_NAME=Porterchain (local)
PORTERCHAIN_OPS_EMAILS=ops@porterchain.com
```

With `MAIL_HOST` empty, the Notification Engine logs email instead of sending (`email (log-only)`). Prefer Mailpit so you can open real messages in the UI.

### Optional: live Zoho from localhost (rare)

Only for verifying SPF/DKIM or a production-like send. Use an **app password**, never a shared login password in git.

```env
MAIL_MAILER=smtp
MAIL_HOST=smtp.zohocloud.ca
MAIL_PORT=465
MAIL_USERNAME=ops@porterchain.com
MAIL_PASSWORD=<zoho-app-password>
MAIL_ENCRYPTION=ssl
MAIL_FROM_ADDRESS=ops@porterchain.com
MAIL_FROM_ADDRESS2=sales@porterchain.com
MAIL_FROM_ADDRESS3=ravi@porterchain.com
MAIL_FROM_NAME=Porterchain
```

**API note:** `delivery_service.py` uses `smtplib.SMTP_SSL` → use **port 465 + SSL**. Do not set `MAIL_PORT=587` for the API until STARTTLS is implemented.

---

## Production

### Env (Doppler → droplet / API + worker)

```env
MAIL_MAILER=smtp
MAIL_HOST=smtp.zohocloud.ca
MAIL_PORT=465
MAIL_USERNAME=ops@porterchain.com
MAIL_PASSWORD=<zoho-app-password>
MAIL_ENCRYPTION=ssl
MAIL_FROM_ADDRESS=ops@porterchain.com
MAIL_FROM_ADDRESS2=sales@porterchain.com
MAIL_FROM_ADDRESS3=ravi@porterchain.com
MAIL_FROM_NAME=Porterchain
PORTERCHAIN_OPS_EMAILS=ops@porterchain.com
```

| Variable                 | Production value             | Notes                                                  |
| ------------------------ | ---------------------------- | ------------------------------------------------------ |
| `MAIL_HOST`              | `smtp.zohocloud.ca`          | Canada DC                                              |
| `MAIL_PORT`              | `465`                        | Matches `SMTP_SSL` in code                             |
| `MAIL_ENCRYPTION`        | `ssl`                        | Documentational; SSL implied by port 465 path          |
| `MAIL_USERNAME`          | Mailbox used to authenticate | Often `ops@…`; must be allowed to send as From aliases |
| `MAIL_PASSWORD`          | App-specific password        | Rotate in Zoho; store only in Doppler                  |
| `MAIL_FROM_ADDRESS`      | `ops@porterchain.com`        | Default From (`smtp_from`)                             |
| `MAIL_FROM_ADDRESS2`     | `sales@porterchain.com`      | `from_alias=sales`                                     |
| `MAIL_FROM_ADDRESS3`     | `ravi@porterchain.com`       | `from_alias` personal / ravi                           |
| `MAIL_FROM_NAME`         | `Porterchain`                | Display name                                           |
| `PORTERCHAIN_OPS_EMAILS` | `ops@porterchain.com`        | Ops distribution / alerts                              |

Secrets live in **Doppler / deploy secrets** — see [SECRETS_MAP.md](../SECRETS_MAP.md). Never commit real `MAIL_PASSWORD`.

### Upload local Zoho password → production (Doppler → droplet)

After `MAIL_*` is set in `apps/api/.env` (gitignored):

```bash
# One-time: brew install dopplerhq/cli/doppler && doppler login
bash infrastructure/deploy/scripts/upload-mail-to-doppler.sh
```

That writes `MAIL_*` into Doppler project **`pcd`** / config **`prd`**. The next GitHub **Deploy** (or on the droplet `bash sync-secrets.sh`) refreshes `/opt/porterchain/.env` for the live API/worker.

Do **not** paste the app password into GitHub Actions secrets individually — Doppler is the runtime SSOT.

### Recommended From by notification type

| Message type            | Prefer From                | How                                                                 |
| ----------------------- | -------------------------- | ------------------------------------------------------------------- |
| Ops / capacity / system | `ops@porterchain.com`      | Default (`MAIL_FROM_ADDRESS`)                                       |
| Quote / commercial      | `sales@porterchain.com`    | Context `from_alias=sales`                                          |
| No-reply automations    | `no-reply@porterchain.com` | Set as `MAIL_FROM_ADDRESS` **or** extend settings + `smtp_from_for` |
| Billing                 | `billing@porterchain.com`  | Same (extend when billing mail ships)                               |
| Support replies         | `support@porterchain.com`  | Human / helpdesk; usually not Notification Engine                   |
| Personal founder mail   | `peter@…` / `ravi@…`       | Clients (IMAP); app only uses `ravi` via `MAIL_FROM_ADDRESS3` today |

Alias selection in code: `settings.smtp_from_for(alias)` in `shared/python/porterchain_shared/config/settings.py`, called from `notification_engine/delivery_service.py`.

---

## Client setup (desktop / phone)

Use the same hosts for Thunderbird, Apple Mail, Outlook, Zoho mobile, etc.

1. Account type: IMAP (preferred) or POP
2. Email: e.g. `support@porterchain.com`
3. Incoming: `imap.zohocloud.ca:993` SSL (or POP `pop.zohocloud.ca:995`)
4. Outgoing: `smtp.zohocloud.ca:465` SSL (or `587` TLS)
5. Username = full email · Authentication = password / app password

---

## DNS checklist (production domain)

Before sending real customer mail from `@porterchain.com`:

- [ ] Zoho domain verified for `porterchain.com`
- [ ] SPF includes Zoho Canada senders
- [ ] DKIM enabled in Zoho Admin → DNS TXT published
- [ ] DMARC policy published (start with `p=none`, then tighten)
- [ ] Each alias above exists and can **Send Mail As** from the SMTP user
- [ ] Test: API health / diagnostics **Email (SMTP)** + send a quote confirmation to a personal inbox

---

## Verification

### Local (Mailpit)

```bash
pnpm docker:up
# Trigger any email path (e.g. business inquiry, driver invite)
open http://localhost:8025
```

Admin diagnostics: **Mailpit (Dev Email)** / **Email (SMTP)** soft-pass when Mailpit is up.

### Production

```bash
# On API host — key names only (no values)
grep -E '^MAIL_' /opt/porterchain/.env | cut -d= -f1

# App-level: Admin → Diagnostics → Email (SMTP) healthy
# Then send a test transactional mail to a controlled inbox
```

---

## Security

- Prefer **app-specific passwords** for SMTP servers; revoke on rotate / offboarding
- Restrict who can read Doppler `MAIL_PASSWORD`
- Do not use Zoho mailbox passwords in CI logs or screenshot runbooks
- `no-reply@` should not be monitored as a support inbox; use `support@` for replies
- IMAP/POP credentials are for humans/tools — **API only needs SMTP**

---

## Related code & config

| Path                                                   | Role                                   |
| ------------------------------------------------------ | -------------------------------------- |
| `shared/python/porterchain_shared/config/settings.py`  | `MAIL_*` → `smtp_*`, `smtp_from_for()` |
| `apps/api/.../notification_engine/delivery_service.py` | Outbound SMTP_SSL                      |
| `env/api.env.example` · `apps/api/env.example`         | Template vars                          |
| `infrastructure/docker/docker-compose.yml`             | Mailpit service                        |
| Calendar (separate)                                    | `ZOHO_CALENDAR_*` — not mail transport |
