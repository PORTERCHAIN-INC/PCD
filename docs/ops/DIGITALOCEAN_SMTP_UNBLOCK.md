# DigitalOcean SMTP unblock request

**Why:** DO droplets block outbound SMTP (ports 25/465/587) by default. PorterChain prod
timed out connecting to `smtp.zeptomail.ca:587` from `68.183.103.49`.

**Mitigation in code:** Notification Engine uses ZeptoMail **HTTPS API**
(`https://api.zeptomail.ca/v1.1/email`) automatically when `MAIL_HOST` contains `zeptomail`
and `APP_ENV` is not local (`MAIL_TRANSPORT=auto`). SMTP remains available after unblock
via `MAIL_TRANSPORT=smtp`.

## Open a ticket

1. Sign in: https://cloud.digitalocean.com/support
2. New ticket → **Account / networking** (or SMTP / email delivery)
3. Paste the template below

Or with CLI (after `doctl auth init`):

```bash
doctl support tickets create \
  --subject "Please unblock outbound SMTP (587/465) for droplet 68.183.103.49" \
  --body "$(cat docs/ops/DIGITALOCEAN_SMTP_UNBLOCK.md | sed -n '/^## Ticket body/,/^## /p' | sed '1d;$d')"
```

(If `doctl support` is unavailable in your CLI version, use the web form.)

## Ticket body

**Subject:** Unblock outbound SMTP ports 587 and 465 for PorterChain production droplet

Hello DigitalOcean Support,

Please enable outbound SMTP (TCP 587 and 465) for our production droplet:

- Droplet IP: `68.183.103.49`
- Region: (see droplet in control panel)
- Use case: Transactional email via ZeptoMail (`smtp.zeptomail.ca`) for order/invoice
  notifications from `noreply@porterchain.com` on `porterchain.com`
- We are not operating an open relay; authenticated client SMTP only to ZeptoMail

We currently send via ZeptoMail’s HTTPS API as a workaround. Unblocking SMTP would let us
use their documented SMTP path as well.

Thank you,
PorterChain / PCD
