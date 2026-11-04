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

## Prod (ZeptoMail)

Keycloak only sends via SMTP. Run once per environment, token from SOPS/Doppler (never on the command line history):

```bash
KC_MAIL_PROVIDER=zeptomail KC_SMTP_PASSWORD="$ZEPTOMAIL_SMTP_TOKEN" KC_SMTP_FROM=no-reply@porterchain.com \
  KC_CONTAINER=<prod keycloak container> bash scripts/keycloak-email-otp-setup.sh
```

→ `smtp.zeptomail.ca:587` STARTTLS, user `emailapikey`.
**Reachability (2026-10-30, from the Ubuntu dev machine 192.168.2.103, TCP connect only):** `smtp.zeptomail.ca` 587 and 465 both OPEN. This says nothing about the DO droplet.
**Check first:** `docs/CONNECTIONS.md` says the DigitalOcean droplet blocks SMTP (the API uses ZeptoMail HTTPS for
that reason). If ports 587/465 are blocked for Keycloak too, codes will not send: ask DO to lift the SMTP block,
or run Keycloak where SMTP is allowed, or add an SMTP→HTTPS relay. Test with one login before switching it on.
The prod Keycloak image must also include the jar (`ADD` it to `/opt/keycloak/providers/`, then `kc.sh build`) and the
`porterchain` theme (login + email).

## Turn off

Set `pc-new-device-code` to DISABLED in the admin console (Authentication → pc-browser), or render the realm with
`EMAIL_OTP_ENABLED=false`.
