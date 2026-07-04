# Porterchain — Security

**Document version:** 1.0  
**Date:** June 29, 2026

---

## Security posture summary

| Area            | Current state                                  | Target state                |
| --------------- | ---------------------------------------------- | --------------------------- |
| Secrets in git  | **Critical** — `details.md` contains live keys | Secret manager only         |
| Auth            | Multi-provider, not unified                    | Clerk + API JWT + RBAC      |
| HTTPS           | Production assumed                             | Enforce HSTS                |
| API hardening   | Not in PCD repo                                | Rate limits, CORS, Helmet   |
| Monitoring      | None                                           | Sentry + uptime checks      |
| Backups         | Not documented                                 | Automated encrypted backups |
| Dependency CVEs | 4 moderate (website)                           | Patch + audit in CI         |

---

## Secrets management

### Critical finding

The file `details.md` at the repository root contains **live credentials** including:

- Stripe secret keys and webhook secrets
- Clerk secret keys
- Database passwords
- SMTP passwords
- Twilio auth tokens
- DigitalOcean API tokens
- Google Maps API keys

### Immediate actions

1. **Remove `details.md` from version control** — add to `.gitignore`
2. **Rotate all exposed credentials** — treat as compromised
3. **Replace with `ENVIRONMENT_VARIABLES.md` + `.env.example` templates** (placeholders only)
4. **Use a secret manager** in production:
   - DigitalOcean App Platform secrets
   - GitHub Actions encrypted secrets (CI only)
   - HashiCorp Vault (enterprise)

### Secret classification

| Class        | Examples                                                 | Storage                   |
| ------------ | -------------------------------------------------------- | ------------------------- |
| **Public**   | `NEXT_PUBLIC_*`, `STRIPE_KEY` (pk_)                      | Env / build args          |
| **Internal** | `PORTERCHAIN_API_URL`, feature flags                     | Env                       |
| **Secret**   | `STRIPE_SECRET`, `CLERK_SECRET_KEY`, DB passwords        | Secret manager only       |
| **Critical** | `STRIPE_WEBHOOK_SECRET`, `APP_KEY`, service account JSON | Secret manager + rotation |

### Rules

- Never commit `.env`, `.env.local`, `credentials/`, `*.p8`, `service-account.json`
- Never log secrets — redact in structured logging
- Browser keys: HTTP referrer restriction
- Server keys: IP restriction
- Mobile keys: bundle ID restriction

---

## Encryption

### In transit

| Connection           | Requirement                |
| -------------------- | -------------------------- |
| Client → CDN/website | TLS 1.2+                   |
| Client → API         | TLS 1.2+                   |
| API → MySQL/Redis    | TLS within private network |
| SMTP                 | SSL on port 465            |
| Webhooks             | HTTPS only                 |

### At rest

| Data                   | Method                               |
| ---------------------- | ------------------------------------ |
| MySQL                  | Managed encryption (DO/AWS RDS)      |
| PostgreSQL             | Managed encryption                   |
| Redis                  | Encrypted volume                     |
| POD images / uploads   | S3 SSE-S3 or SSE-KMS                 |
| Driver tokens (mobile) | `expo-secure-store` (OS keychain)    |
| Laravel `APP_KEY`      | AES-256-CBC for encrypted attributes |

### JWT

- Signed with RS256 (Clerk JWKS) or HS256 (Porterchain-issued)
- Short access token TTL (15–60 minutes)
- Refresh token rotation on use
- Revocation list in Redis for compromised tokens

---

## Authentication security

See [AUTHENTICATION.md](./AUTHENTICATION.md).

| Control          | Implementation                       |
| ---------------- | ------------------------------------ |
| Password hashing | bcrypt/argon2 (API)                  |
| Invite tokens    | Opaque, hashed at rest, 7-day expiry |
| OTP rate limits  | Redis sliding window                 |
| Clerk MFA        | Enable for merchant admins           |
| Session fixation | Clerk handles session rotation       |

---

## API security

### Rate limiting (recommended)

| Endpoint class   | Limit                       |
| ---------------- | --------------------------- |
| Auth (`/auth/*`) | 10 req/min per IP           |
| Driver invite    | 15–30 req/min (configured)  |
| Public quote API | 60 req/min per API key      |
| Webhooks         | No limit (verify signature) |

Implement with Redis + `slowapi` (FastAPI) or Laravel middleware.

### CORS

```python
# Target — Porterchain API
ALLOWED_ORIGINS = [
    "https://porterchain.com",
    "https://www.porterchain.com",
    "https://admin.porterchain.com",
    "https://merchant.porterchain.com",
    "https://driver.porterchain.com",
    "https://customer.porterchain.com",
    "http://localhost:3000",  # dev only
    "http://localhost:3001",  # dev only
]
```

- No wildcard `*` in production
- Credentials: `true` only for same-site cookies

### Helmet / security headers (Next.js)

```typescript
// next.config.ts — target headers
{
  key: "X-Frame-Options", value: "DENY"
  key: "X-Content-Type-Options", value: "nosniff"
  key: "Referrer-Policy", value: "strict-origin-when-cross-origin"
  key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()"
  key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains"
}
```

### CSRF

| Surface            | Protection                       |
| ------------------ | -------------------------------- |
| Next.js API routes | CSRF token for cookie-auth forms |
| Clerk sessions     | Clerk built-in CSRF              |
| Stripe Checkout    | Stripe-hosted (no CSRF risk)     |
| API (Bearer JWT)   | Not CSRF-vulnerable (no cookies) |

### Input validation

- Pydantic models on all FastAPI endpoints
- Zod schemas on Next.js server actions
- File upload: MIME type + size limits (POD photos max 10MB)
- SQL injection: ORM only — no raw string interpolation

---

## Webhook security

### Stripe

```python
stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
```

- Verify signature on every request
- Idempotency: store `event.id` in DB before processing
- Return 200 quickly; process async via queue

### Outbound merchant webhooks

- HMAC-SHA256 signature: `X-Porterchain-Signature`
- Timestamp header to prevent replay (5-minute window)
- Retry: 3 attempts with exponential backoff

---

## Network security

### Docker

- Database and Redis on `internal: true` network
- No public port binding for MySQL (3306) or Redis (6379)
- Valhalla accessible only from API containers

### Production firewall

- Only 443 (and 80 redirect) public
- SSH via bastion or VPN
- API behind reverse proxy with WAF (Cloudflare or DO)

---

## File upload security

| Control        | Detail                                    |
| -------------- | ----------------------------------------- |
| Max size       | 10 MB photos, 1 MB signatures             |
| Allowed types  | `image/jpeg`, `image/png`, `image/webp`   |
| Storage        | Private bucket; signed URLs for retrieval |
| Virus scan     | ClamAV or cloud scan (recommended)        |
| EXIF stripping | Remove GPS from customer-uploaded photos  |

---

## Dependency security

See [DEPENDENCY_REPORT.md](./DEPENDENCY_REPORT.md).

| Action                     | Frequency              |
| -------------------------- | ---------------------- |
| `npm audit` / `pnpm audit` | Every CI run           |
| Dependabot / Renovate      | Weekly PRs             |
| `pip audit` (API)          | Every CI run           |
| Container image scan       | On every build (Trivy) |

Current website findings: 4 moderate CVEs (js-yaml, postcss transitive).

---

## Logging and monitoring

### What to log

| Event            | Log level           |
| ---------------- | ------------------- |
| Auth failures    | WARN                |
| Rate limit hits  | WARN                |
| Webhook failures | ERROR               |
| Payment events   | INFO (no card data) |
| Admin actions    | INFO (audit trail)  |

### What NOT to log

- Passwords, OTP codes, JWT tokens
- Full credit card numbers
- Stripe secret keys
- Personal health or sensitive PII beyond operational need

### Sentry (recommended)

```env
SENTRY_DSN=https://...@sentry.io/...
NEXT_PUBLIC_SENTRY_DSN=...
```

- Scrub PII in `beforeSend` hook
- Separate projects: website, api, mobile

---

## Backups

| Asset      | Method                    | Encryption        | Retention |
| ---------- | ------------------------- | ----------------- | --------- |
| MySQL      | Daily dump + binlog       | AES-256 at rest   | 30 days   |
| PostgreSQL | pg_dump + WAL             | AES-256 at rest   | 30 days   |
| Redis      | AOF snapshot              | Volume encryption | 7 days    |
| S3 uploads | Cross-region replication  | SSE               | 1 year    |
| Secrets    | Secret manager versioning | Provider-managed  | 90 days   |

### Recovery objectives

| Metric          | Target  |
| --------------- | ------- |
| RPO (data loss) | 1 hour  |
| RTO (downtime)  | 4 hours |

Test restore quarterly.

---

## Compliance

| Regulation           | Relevance    | Status                              |
| -------------------- | ------------ | ----------------------------------- |
| **PIPEDA** (Canada)  | Customer PII | Privacy policy not published        |
| **PCI DSS**          | Card data    | Stripe handles — SAQ A eligible     |
| **WSIB / insurance** | Operations   | Documented on website               |
| **GDPR**             | EU traffic   | PC-CRM module only; not public site |

### Recommended legal pages (not in PCD repo)

- `/privacy` — PIPEDA-compliant privacy policy
- `/terms` — Terms of service
- `/cookies` — Cookie consent + policy

---

## Incident response

1. **Detect** — Sentry alert, uptime monitor, Stripe fraud alert
2. **Contain** — Rotate compromised keys, disable affected API keys
3. **Assess** — Determine scope (PII, payment data)
4. **Notify** — Ops team, legal if PIPEDA breach threshold met
5. **Remediate** — Patch, redeploy, post-mortem

### Key rotation runbook

| Secret      | Rotation trigger | Process                                       |
| ----------- | ---------------- | --------------------------------------------- |
| Stripe      | Suspected leak   | Dashboard → roll keys → update env → redeploy |
| Clerk       | Suspected leak   | Clerk dashboard → rotate → update JWKS        |
| DB password | Quarterly        | Update secret manager → rolling restart       |
| `APP_KEY`   | Compromise       | Laravel key rotate + re-encrypt               |

---

## Security checklist (pre-production)

- [ ] `details.md` removed and all secrets rotated
- [ ] HTTPS enforced with HSTS
- [ ] CORS restricted to known origins
- [ ] Rate limiting on auth endpoints
- [ ] Stripe webhook signature verified
- [ ] Google API keys restricted
- [ ] Database not publicly accessible
- [ ] Sentry configured with PII scrubbing
- [ ] Backups tested
- [ ] Dependency audit clean (no high/critical)
- [ ] `.gitignore` covers all secret file patterns

---

_Security is a continuous process. Review this document quarterly and after any incident._
