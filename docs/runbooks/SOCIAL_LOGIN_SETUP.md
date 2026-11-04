# Google + Apple sign-in (Keycloak) — setup

Both providers already exist in the `porterchain` realm as **disabled** (hidden on the login page).
They turn on only when real keys are present **and** `SOCIAL_LOGIN_ENABLED=true`:

```bash
# keys live in SOPS (never in the repo); decrypt to a temp env file, then:
SOCIAL_LOGIN_ENABLED=true SOCIAL_ENV=/path/to/decrypted-social.env bash scripts/keycloak-social-setup.sh
```

Env names: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `APPLE_SERVICES_ID`, `APPLE_TEAM_ID`,
`APPLE_KEY_ID`, `APPLE_P8_FILE` (path to the `.p8`). SMTP (ZeptoMail in prod): `KC_SMTP_HOST`, `KC_SMTP_PORT`,
`KC_SMTP_USER`, `KC_SMTP_PASSWORD`, `KC_SMTP_FROM`. The script never recreates Keycloak.

Behaviour: social buttons show for merchant, customer, driver and website sign-in, never on admin (staff are
invite-only + authenticator app). First Google/Apple login links to an existing account **with the same verified
email** (flow `pc-first-broker-login`), otherwise creates the account.

Apple needs the free OSS extension `apple-identity-provider-1.17.0.jar`
(github.com/klausbetz/apple-identity-provider-keycloak, sha512 checked) in `/opt/keycloak/providers/`
(file in `infrastructure/keycloak/providers/`; prod image/compose must mount it, then `kc.sh build` / restart).

## What Ravi must create

### Google (Google Cloud Console → APIs & Services → Credentials)

1. OAuth consent screen: External, app name "Porterchain", support email, logo, privacy + terms URLs,
   scopes `openid email profile`. Publish it.
2. Create **OAuth client ID** → type _Web application_.
3. Authorized redirect URIs:
   - Prod: `https://auth.porterchain.com/realms/porterchain/broker/google/endpoint`
   - Local: `http://localhost:18280/realms/porterchain/broker/google/endpoint`
     (Google does not accept a LAN IP such as 192.168.2.103, so test Google locally on the Ubuntu machine via localhost.)
4. Put Client ID + Client secret into SOPS.

### Apple (developer.apple.com → Certificates, IDs & Profiles; needs the paid Apple Developer account)

1. **App ID** with "Sign in with Apple" enabled (the iOS app's ID can be the primary).
2. **Services ID** (e.g. `com.porterchain.signin`) → enable Sign in with Apple → Configure:
   - Domain: `auth.porterchain.com`
   - Return URL: `https://auth.porterchain.com/realms/porterchain/broker/apple/endpoint`
   - Apple only accepts HTTPS on a real domain, so Apple sign-in **cannot be tested on the local http stack**.
3. **Key** with Sign in with Apple enabled → download the `.p8` (one-time download) → note the **Key ID**.
4. Note the **Team ID** (top right of the developer portal).
5. Put Services ID, Team ID, Key ID and the `.p8` content into SOPS.
6. Optional: email relay — register `no-reply@porterchain.com` (ZeptoMail domain) under
   "Sign in with Apple for Email Communication" so emails reach users who hide their address.
