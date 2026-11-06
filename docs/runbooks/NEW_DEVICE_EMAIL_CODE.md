# New-device email code (Keycloak)

**What users see:** merchants, drivers, customers and website users get a 6-digit email code **only when they sign in
from a browser we have not seen before** (or after the 180-day device trust expires / cookies are cleared).
Same browser later: no code. Staff/admin (role `mfa_required`) **never** get the email code; they keep TOTP.

## Pieces

| Piece                              | Where                                                                                                                                                                                                                                                                                                    |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Extension                          | `infrastructure/keycloak/providers/email-otp-authenticator-v1.8.1-kc-26.8.1.jar` — github.com/for-keycloak/email-otp-authenticator, **Unlicense** (public domain, free for commercial use), release 2026-10-14, built for Keycloak 26.8.1, sha256 `8013758f…7cedea` (pinned in `scripts/local-stack.sh`) |
| Flow                               | `pc-browser → pc-forms → pc-new-device-code` (CONDITIONAL): `Condition - user role mfa_required` **negated**, then `Email OTP Form`. Source: `infrastructure/keycloak/build_realm.py`                                                                                                                    |
| Settings                           | device trust ON (cookie `EMAIL_OTP_DEVICE_TRUST_*`, per user+realm, HttpOnly, Secure, 180 days, set automatically after a correct code); IP trust OFF (shared office/Wi-Fi IPs must not skip it); 6 digits, 10 min; resend cooldown 60 s; max 5 codes per user per 15 min                                |
| Code screen                        | `themes/porterchain/login/login-email-otp.ftl` + `template.ftl` ("Check your email", masked address, Resend, Use another account) EN/FR                                                                                                                                                                  |
| Email                              | `themes/porterchain/email/{html,text}/otp-email.ftl` + `messages_{en,fr}` (subject "Your Porterchain sign-in code" / "Votre code de connexion Porterchain"); realm `emailTheme=porterchain`                                                                                                              |
| Setup (idempotent, existing realm) | `scripts/keycloak-email-otp-setup.sh`                                                                                                                                                                                                                                                                    |
| Tests                              | `apps/api/tests/test_keycloak_email_otp.py` (config); e2e `~/.pcd-local-stack/eotp-e2e.mjs` (Mailpit)                                                                                                                                                                                                    |

## "Risky login"

Keycloak itself decides risk here as: unknown browser (no valid trust cookie) → code. Repeated wrong passwords
are handled by the realm brute-force lockout (10 failures). There is no geo/IP-reputation scoring in this OSS
extension; adding one would need another extension or a paid risk engine.

## Local stack

```bash
bash scripts/local-stack.sh kc-ext   # copies jar (+theme) into the RUNNING Keycloak, restarts it only if the jar was new, applies the flow
node ~/.pcd-local-stack/eotp-e2e.mjs # new browser → code in Mailpit (http://192.168.2.103:58026); same browser later → none; admin → TOTP
```

The local stack is plain http, but the trust cookie is `Secure` (correct for prod). Browsers only keep it on https
or localhost, so **on http://192.168.2.103 a real browser will ask for a code every sign-in**. The e2e test uses
Chromium's `--unsafely-treat-insecure-origin-as-secure` for the Keycloak origin. Prod (https) is unaffected.
Fresh `up` mounts the jar and runs the setup script automatically.

## Prod (ZeptoMail HTTPS relay on DigitalOcean)

Keycloak only speaks SMTP; DigitalOcean Droplets block outbound 25/465/587. **Do not** point
Keycloak at `smtp.zeptomail.ca` on the droplet.

**Permanent path:** `pcd-kc-mail-relay` (SMTP on the Docker network → ZeptoMail HTTPS :443).
Full steps: `docs/runbooks/KEYCLOAK_MAIL_HTTPS.md`.

```bash
# After the relay container is up (see KEYCLOAK_MAIL_HTTPS.md):
KC_MAIL_PROVIDER=zeptomail_https KC_SMTP_FROM=no-reply@porterchain.com \
  KC_CONTAINER=pcd-keycloak bash scripts/keycloak-email-otp-setup.sh
```

→ Keycloak `smtpServer.host=pcd-kc-mail-relay` port `1025`, no STARTTLS; token stays in
`/opt/porterchain/secrets/keycloak-mail-relay.env` (never in the realm SMTP password).

On non-DO hosts where 587 is open you may still use `KC_MAIL_PROVIDER=zeptomail` (direct
SMTP). The prod Keycloak image must also include the email-otp jar and the `porterchain` theme.

## Turn off

Set `pc-new-device-code` to DISABLED in the admin console (Authentication → pc-browser), or render the realm with
`EMAIL_OTP_ENABLED=false`.
