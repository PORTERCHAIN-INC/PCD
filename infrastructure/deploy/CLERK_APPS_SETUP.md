# Clerk — 4 production applications (§0.5)

**Type:** CANONICAL  
**Last verified:** 2026-07-06

One Clerk **application** per user class. The API verifies JWTs from all four via `clerk_registry.py`; each portal/mobile build embeds only its own publishable key.

---

## Current state (2026-07-07)

| Store | What you have |
| ----- | ------------- |
| Local | `env/clerk.env` — single source; `pnpm clerk:sync` |
| Doppler `pcd` / `prd` | Runtime secrets via `DOPPLER_TOKEN` + `sync-secrets.sh` |
| GitHub | Deploy creds + 4× `CLERK_*_PUBLISHABLE_KEY` for Docker builds |
| Server | Generated `/opt/porterchain/.env` — never hand-edit |

**Verify:** `pnpm secrets:verify` · API: `curl …/health/ready | jq '.clerk_mode, .clerk_apps'`

**Before go-live:** use `pk_live_` / `sk_live_` keys (not `pk_test_` / `sk_test_`).

---

## Step 1 — Open Clerk

1. Go to [dashboard.clerk.com](https://dashboard.clerk.com)
2. Open instance **`relaxing-warthog-11`** (or your prod instance)
3. Top-left **application switcher** → **Create application** (repeat 4 times)

| Application name | Suggested slug | Used by |
| ---------------- | -------------- | ------- |
| Porterchain Customer | `porterchain-customer` | Website, customer portal, customer mobile |
| Porterchain Merchant | `porterchain-merchant` | Merchant portal |
| Porterchain Admin | `porterchain-admin` | Admin portal |
| Porterchain Driver | `porterchain-driver` | Driver portal, driver mobile |

---

## Step 2 — Production keys per application

For **each** of the 4 applications:

1. Clerk Dashboard → select application
2. Toggle environment to **Production** (top bar)
3. **Configure → API Keys**
   - Copy **Publishable key** (`pk_live_…`)
   - Copy **Secret key** (`sk_live_…`)
4. **Advanced** (same page) → copy **JWKS Endpoint**  
   - Usually `https://<instance>.clerk.accounts.dev/.well-known/jwks.json`  
   - All four apps on the **same instance** may share the same JWKS URL — that is fine; set the same URL in all four `CLERK_*_JWKS_URL` fields.

---

## Step 3 — Redirect URLs & domains

### Customer app (`porterchain-customer`)

**Paths:** website `/login`, customer portal `/sign-in`

| Setting | Values |
| ------- | ------ |
| **Home URL** | `https://porterchain.com` |
| **Allowed redirect URLs** | `https://porterchain.com/*`, `https://www.porterchain.com/*`, `https://customer.porterchain.com/*` |
| **Sign-in URL** | `https://porterchain.com/login` (website); customer portal uses `/sign-in` on its host |
| **Sign-up URL** | `https://porterchain.com/login` or customer `/sign-in` |
| **After sign-in** | `https://customer.porterchain.com/dashboard` (portal) / website book flow |

**Customer mobile** (`apps/mobile-customer`):

- Add redirect: `porterchain-customer://`
- EAS secret: `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` = customer `pk_live_…`

### Merchant app (`porterchain-merchant`)

| Setting | Values |
| ------- | ------ |
| **Home URL** | `https://merchant.porterchain.com` |
| **Allowed redirect URLs** | `https://merchant.porterchain.com/*` |
| **Sign-in / sign-up** | `https://merchant.porterchain.com/sign-in`, `/sign-up` |

### Admin app (`porterchain-admin`)

Clerk **Paths** only shows **Component paths** (where `<SignIn />`, `<SignUp />`, etc. live). There is **no** “After sign-in URL” in the dashboard (removed in Core 2). Post-login redirect is set in app env — see `adminPublicEnv()`.

**Configure → Paths → Component paths** (production — full `https://` URLs on your app domain):

| Component | Value |
| --------- | ----- |
| `<SignIn />` | `https://admin.porterchain.com/sign-in` |
| `<SignUp />` | `https://admin.porterchain.com/sign-in` (invite-only — same as sign-in) |
| Signing out | `https://admin.porterchain.com/sign-in` |
| `<OAuthConsent />` | leave default unless you use custom OAuth consent |

Pointing SignIn at **your app** (not `accounts.admin…`) keeps auth on `admin.porterchain.com` and avoids Account Portal bounce. Alternatively keep Account Portal and rely on code redirects below.

**After sign-in redirect (code only):**

```bash
NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL=/dashboard
NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=/dashboard
```

Baked in `packages/config/monorepo-env.mjs` → `adminPublicEnv()`. Redeploy admin image for prod.

Ensure DNS CNAMEs for `clerk.admin.porterchain.com` and `accounts.admin.porterchain.com` are verified in Clerk → **Domains**.

Restrict sign-ups: **Configure → Restrictions** → disable public sign-up; invite staff only.

### Driver app (`porterchain-driver`)

| Setting | Values |
| ------- | ------ |
| **Home URL** | `https://driver.porterchain.com` |
| **Allowed redirect URLs** | `https://driver.porterchain.com/*` |
| **Sign-in** | `https://driver.porterchain.com/login` |

**Driver mobile** (`apps/mobile-driver`):

- Add redirect: `porterchain-driver://`
- EAS secret: `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` = driver `pk_live_…`

---

## Step 4 — Fill keys locally

```bash
cp infrastructure/deploy/scripts/clerk-keys.template.env infrastructure/deploy/scripts/clerk-keys.local.env
# Edit clerk-keys.local.env — paste all 12 values (never commit)

pnpm clerk:sync
```

`pnpm clerk:sync` writes the correct Clerk app into each web portal, mobile app, and `apps/api/.env` (see `env/README.md`).

Validate before upload:

```bash
bash infrastructure/deploy/scripts/validate-clerk-keys.sh
```

---

## Step 5 — Upload to Doppler + GitHub

```bash
# Doppler (runtime secrets on droplet)
bash infrastructure/deploy/scripts/upload-clerk-to-doppler.sh

# GitHub (portal Docker build args — publishable keys only)
bash infrastructure/deploy/scripts/upload-clerk-to-github.sh
```

Or paste manually in [Doppler `pcd` / `prd`](https://dashboard.doppler.com) using the variable names in `clerk-keys.template.env`.

**After upload:** remove or leave legacy `CLERK_SECRET_KEY` / `CLERK_PUBLISHABLE_KEY` / `CLERK_JWKS_URL` — enterprise keys take precedence when all twelve per-portal vars are set.

---

## Step 6 — Deploy & verify

Trigger **Deploy** workflow (rebuilds all portal images with correct `pk_live_` per app).

```bash
# After deploy
curl -s https://api.porterchain.com/health/ready | jq '.clerk_mode, .checks.clerk, .clerk_apps'

# On droplet
bash scripts/verify-clerk.sh
```

Expected: `clerk_mode: "enterprise"`, all four `clerk_apps.*: "ok"`.

---

## Step 7 — Smoke login (manual)

| Portal | URL | Test user |
| ------ | --- | --------- |
| Customer | https://customer.porterchain.com/sign-in | Retail customer |
| Merchant | https://merchant.porterchain.com/sign-in | Merchant user in DB |
| Admin | https://admin.porterchain.com/sign-in | `admin_users` row |
| Driver web | https://driver.porterchain.com/login | Driver with Clerk linked |
| Website | https://porterchain.com/login | Same customer app |

API must return 200 on access gates: `/v1/auth/{admin,merchant,customer}/access` with Bearer token.

---

## Migration note

Users created in the **old single Clerk app** do not automatically exist in the new apps. Plan:

1. Create 4 apps + keys (above)
2. Invite / re-provision users per portal (`provision_merchant_user.py`, admin invite, driver invite flow)
3. Deprecate legacy `CLERK_*` keys after cutover

---

## Related

| Doc | Role |
| --- | ---- |
| [AUTHENTICATION_ARCHITECTURE.md](../../AUTHENTICATION_ARCHITECTURE.md) | Auth model |
| [SECRETS.md](./SECRETS.md) | Doppler + rotation |
| [env/production.env.example](../../env/production.env.example) | Prod URL reference |
