# Connect a NEW GitHub account/repo → DigitalOcean + this MacBook

Generated: 2026-07-28  
Scope: **checklist + public keys + secret NAMES** — private keys / Doppler tokens are NOT pasted here (copy them from your vault / `pbcopy` when filling GitHub).

Current live droplet: `68.183.103.49` (api.porterchain.com)  
SSH user: `root`  
Local Mac keys already on droplet: `ravi@macbook` + `pcd-github-deploy`

---

## What you are connecting (3 separate links)

| Link                             | Purpose                                       | What to add                                               |
| -------------------------------- | --------------------------------------------- | --------------------------------------------------------- |
| **A. Mac → new GitHub account**  | `git clone` / `git push` as the other account | GitHub **Account** → Settings → SSH keys → Mac public key |
| **B. New GitHub repo → droplet** | Actions Deploy over SSH                       | Repo **Secrets**: `DEPLOY_*` + `DOPPLER_TOKEN`            |
| **C. Mac → droplet**             | Manual SSH / backup                           | Already works; optional 2nd key                           |

Do **not** put Clerk `sk_*`, Stripe, or Postgres passwords in GitHub — those stay in **Doppler**.

---

## A) MacBook ↔ different GitHub account

### Recommended: one SSH key per GitHub account

```bash
# Generate a key ONLY for the new GitHub account
ssh-keygen -t ed25519 -C "ravi@macbook-github2" -f ~/.ssh/id_ed25519_github2 -N ""

# Show public key → paste into NEW GitHub account → Settings → SSH and GPG keys → New SSH key
cat ~/.ssh/id_ed25519_github2.pub
```

### SSH config (`~/.ssh/config`) so both accounts work on one Mac

```
# Existing / default GitHub (current account)
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes

# NEW GitHub account
Host github-new
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github2
  IdentitiesOnly yes
```

Clone / remotes for the new account:

```bash
git clone git@github-new:NEW_ORG_OR_USER/NEW_REPO.git
# or change remote:
git remote set-url origin git@github-new:NEW_ORG_OR_USER/NEW_REPO.git
```

### Mac public key already on this machine (current default)

Use this for the **current** GitHub account (already labeled `ravi@macbook`):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN32kA5Ygh0L3OBY13wcoCuNOplevnF4aKodjF1lMP9q ravi@macbook
```

Fingerprint: `SHA256:CQCe7ZoXDLDke6TT87+xV0aLrjbDVf38xWxdk53Co9Q`

For the **new** account, prefer a **new** key (`id_ed25519_github2`) so accounts stay isolated.

---

## B) New GitHub **repository** secrets (required for Deploy → DigitalOcean)

In the **new** repo: **Settings → Secrets and variables → Actions**

### Required secrets (copy these NAMES exactly)

| Secret name      | What value to put                           | Where to get it                                                                                             |
| ---------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `DEPLOY_HOST`    | `68.183.103.49`                             | Droplet public IP                                                                                           |
| `DEPLOY_USER`    | `root`                                      | Current prod user                                                                                           |
| `DEPLOY_SSH_KEY` | **Full private key PEM** (entire file)      | Prefer NEW keypair (below) or reuse `~/.ssh/pcd_deploy`                                                     |
| `DOPPLER_TOKEN`  | Doppler **service token** for `pcd` / `prd` | Doppler → Project pcd → Access → Service Tokens (or reuse existing token only if you intend shared secrets) |

Optional:

| Secret name   | Notes                                   |
| ------------- | --------------------------------------- |
| `DEPLOY_PORT` | Default `22` — only set if non-standard |

### Required build-time secrets (public Clerk + Maps — same as current PCD)

| Secret name                            | Value type       |
| -------------------------------------- | ---------------- |
| `CLERK_CUSTOMER_PUBLISHABLE_KEY`       | `pk_live_…`      |
| `CLERK_MERCHANT_PUBLISHABLE_KEY`       | `pk_live_…`      |
| `CLERK_ADMIN_PUBLISHABLE_KEY`          | `pk_live_…`      |
| `CLERK_DRIVER_PUBLISHABLE_KEY`         | `pk_live_…`      |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`      | Maps browser key |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID`        | Optional GA      |
| `NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE` | Optional Zoho    |

### Required repository **variables** (not secrets)

| Variable                           | Value                    |
| ---------------------------------- | ------------------------ |
| `DOPPLER_PROJECT`                  | `pcd`                    |
| `DOPPLER_CONFIG`                   | `prd`                    |
| `PORTERCHAIN_PUSH_ENABLED`         | `true` (if using push)   |
| `PORTERCHAIN_PUSH_SEND`            | `true` (if sending push) |
| `NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED` | `true` / `false`         |

### Paste commands (run after `gh auth login` as the **new** account)

```bash
# Point gh at the new repo first, then:
gh secret set DEPLOY_HOST -b "68.183.103.49"
gh secret set DEPLOY_USER -b "root"
gh secret set DEPLOY_SSH_KEY < ~/.ssh/pcd_deploy_new   # or ~/.ssh/pcd_deploy
# DOPPLER_TOKEN: paste interactively (do not echo into shell history)
gh secret set DOPPLER_TOKEN

gh variable set DOPPLER_PROJECT -b "pcd"
gh variable set DOPPLER_CONFIG -b "prd"
```

---

## C) Deploy SSH key: GitHub Actions → DigitalOcean

### Current deploy public key (already on droplet `authorized_keys`)

Comment: `pcd-github-deploy`  
Private file on Mac: `~/.ssh/pcd_deploy` (this is what current repo’s `DEPLOY_SSH_KEY` is)

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBRL9Bnl1qxIvT1e5nX8PescmYZKQUNRvw2YMMMNXu9O pcd-github-deploy
```

Fingerprint: `SHA256:5IsItWQ8mxH/UXtHAvYUVCKEW4ydtCssK5aMfX/TIqY`

### Option 1 — Reuse same deploy key (fastest)

1. New repo secret `DEPLOY_SSH_KEY` = contents of `~/.ssh/pcd_deploy`  
   (`pbcopy < ~/.ssh/pcd_deploy` then paste in GitHub UI)
2. No droplet change needed (pubkey already authorized)

### Option 2 — New key for the new GitHub account (cleaner isolation)

```bash
ssh-keygen -t ed25519 -C "pcd-github-deploy-account2" -f ~/.ssh/pcd_deploy_new -N ""

# Add PUBLIC key to droplet
ssh -i ~/.ssh/pcd_deploy root@68.183.103.49 \
  'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys' \
  < ~/.ssh/pcd_deploy_new.pub

# Put PRIVATE key in NEW repo only
gh secret set DEPLOY_SSH_KEY < ~/.ssh/pcd_deploy_new
```

### Mac → droplet (manual)

Already authorized:

```
ssh -i ~/.ssh/id_ed25519 root@68.183.103.49
# or
ssh -i ~/.ssh/pcd_deploy root@68.183.103.49
```

Optional `~/.ssh/config` Host:

```
Host porterchain-do
  HostName 68.183.103.49
  User root
  IdentityFile ~/.ssh/pcd_deploy
  IdentitiesOnly yes
```

Then: `ssh porterchain-do`

---

## D) What NOT to put in the new GitHub repo

| Keep out of GitHub                       | Where it belongs                 |
| ---------------------------------------- | -------------------------------- |
| `CLERK_*_SECRET_KEY`, JWKS URLs          | Doppler `pcd`/`prd`              |
| `STRIPE_SECRET`, `STRIPE_WEBHOOK_SECRET` | Doppler (frozen — do not rotate) |
| `POSTGRES_PASSWORD`, `JWT_SECRET`        | Doppler                          |
| Firebase JSON                            | Doppler                          |
| `MAIL_PASSWORD`                          | Doppler                          |

GitHub only needs **deploy SSH + Doppler token + publishable/build keys**.

---

## E) GHCR / image registry note

Current workflows push to `ghcr.io` under the **repo’s** GitHub org/user via `GITHUB_TOKEN`.

If the new account/org is different:

1. Ensure Packages write permission for Actions
2. Update image names in deploy compose/workflows if they hardcode `ghcr.io/porterchain/...`
3. On the droplet, `docker login ghcr.io` must use a token that can pull those new images

---

## F) Checklist (do in order)

- [ ] Create/login **new** GitHub account
- [ ] Create new repository (copy/push code)
- [ ] Generate Mac SSH key for that account → add to **Account SSH keys**
- [ ] Add `Host github-new` to `~/.ssh/config`
- [ ] Set repo secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DOPPLER_TOKEN`
- [ ] Set Clerk `pk_live_*` ×4 + Maps (+ optional GA/Zoho)
- [ ] Set variables: `DOPPLER_PROJECT=pcd`, `DOPPLER_CONFIG=prd`
- [ ] If new deploy key: append `.pub` to droplet `authorized_keys`
- [ ] Fix GitHub **Billing / Actions spending limit** (currently blocks Deploy)
- [ ] `gh workflow run Deploy` from the new repo
- [ ] Smoke: `pnpm validate:d3:prod`

---

## G) Quick “copy board” — public keys only

### Mac default (`ravi@macbook`)

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN32kA5Ygh0L3OBY13wcoCuNOplevnF4aKodjF1lMP9q ravi@macbook
```

### Deploy (`pcd-github-deploy`) — already on DO

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBRL9Bnl1qxIvT1e5nX8PescmYZKQUNRvw2YMMMNXu9O pcd-github-deploy
```

### Private keys — copy from disk, never commit

| File                        | Use                                               |
| --------------------------- | ------------------------------------------------- |
| `~/.ssh/id_ed25519`         | Mac → GitHub (current)                            |
| `~/.ssh/id_ed25519_github2` | Mac → GitHub (new) — create first                 |
| `~/.ssh/pcd_deploy`         | GitHub Actions → droplet (current)                |
| `~/.ssh/pcd_deploy_new`     | GitHub Actions → droplet (new account) — optional |

```bash
# Example: copy deploy private key to clipboard for GitHub secret paste
pbcopy < ~/.ssh/pcd_deploy
```

---

## H) Minimum secrets for “SSH deploy only” (if you only care about DO link)

If the new repo’s only job is deploy to this droplet:

1. `DEPLOY_HOST` = `68.183.103.49`
2. `DEPLOY_USER` = `root`
3. `DEPLOY_SSH_KEY` = private key matching a pubkey in droplet `authorized_keys`
4. `DOPPLER_TOKEN` = service token (required by current `deploy.yml`)

Everything else is for **building** portal/website images with Clerk/Maps baked in.

---

## Status: portrxpress/PCD (2026-07-28)

- SSH Mac key `ravi@macbook` → authenticates as **portrxpress**
- `main` pushed (`b4096e2`) via remote `portrxpress`
- Secrets set: DEPLOY__, 4× CLERK___PUBLISHABLE_KEY, Maps, GA, Zoho widget
- Variables set: DOPPLER_PROJECT/CONFIG, PUSH_*, ZOHO enabled
- **Still missing:** `DOPPLER_TOKEN` (not available on this Mac/droplet — copy from Doppler dashboard or from porterchain repo secret UI once, then):

```bash
gh secret set DOPPLER_TOKEN -R portrxpress/PCD
# paste dp.st.prd.… when prompted
```

- Local WIP (Capacity Guide etc.) was **not** committed/pushed — only existing `main` history
- Local `origin` still = `porterchain/PCD`; push to new account with: `git push portrxpress main`
