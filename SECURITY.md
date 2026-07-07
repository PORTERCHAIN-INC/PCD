# Porterchain — Security

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Platform is **not production-ready** — see [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md). This document describes security posture, controls, and pre-production checklist.

---

## Security posture summary

| Area            | Current state                                                        | Target (production)           |
| --------------- | -------------------------------------------------------------------- | ----------------------------- |
| Secrets in git  | `details.md` **removed** (July 2026); use `env/*.example` only       | Doppler + [SECRETS.md](./infrastructure/deploy/SECRETS.md) |
| Auth            | **Clerk-only** user identity + Porterchain RBAC + driver session JWT | MFA for admin/merchant admins |
| Database        | **PostgreSQL 16** (Porterchain); MySQL (Fleetbase only)              | TLS, private network          |
| HTTPS           | Assumed in production deploys                                        | Enforce HSTS                  |
| API hardening   | Partial (Pydantic validation, RBAC)                                  | Rate limits, strict CORS      |
| Monitoring      | Limited                                                              | Sentry + uptime checks        |
| Backups         | Documented below; not verified in CI                                 | Automated encrypted backups   |
| Dependency CVEs | Track via CI audit                                                   | No high/critical in release   |

---

## Secrets management

### Rules

- Never commit `.env`, `.env.local`, `credentials/`, `*.p8`, `service-account.json`
- Root `details.md` was deleted — rotate any credentials that were ever committed
- Reference: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) + `env/*.env.example` (placeholders only)

### Secret classification

| Class        | Examples                                                        | Storage                   |
| ------------ | --------------------------------------------------------------- | ------------------------- |
| **Public**   | `NEXT_PUBLIC_*`, Stripe publishable key                         | Env / build args          |
| **Internal** | `PORTERCHAIN_API_URL`, feature flags                            | Env                       |
| **Secret**   | `STRIPE_SECRET`, `CLERK_SECRET_KEY`, DB passwords               | Secret manager            |
| **Critical** | `STRIPE_WEBHOOK_SECRET`, `JWT_SECRET` (SSO alias: `SSO_JWT_SECRET`), service account JSON | Secret manager + rotation |

### Production storage

- **[Doppler](https://www.doppler.com)** — production runtime SSOT (`pcd` / `prd`); synced by `infrastructure/deploy/sync-secrets.sh` (DD-14)
- GitHub Actions encrypted secrets — deploy credentials + legacy fallback until `DOPPLER_TOKEN` is set
- Browser keys: HTTP referrer restriction; server keys: IP restriction; mobile: bundle ID restriction

---

## Encryption

### In transit

| Connection               | Requirement                |
| ------------------------ | -------------------------- |
| Client → portals / API   | TLS 1.2+                   |
| API → PostgreSQL / Redis | TLS within private network |
| SMTP                     | SSL/TLS                    |
| Webhooks                 | HTTPS only                 |

### At rest

| Data                     | Method                            |
| ------------------------ | --------------------------------- |
| PostgreSQL (Porterchain) | Managed encryption (DO/AWS RDS)   |
| MySQL (Fleetbase)        | Managed encryption                |
| Redis                    | Encrypted volume                  |
| POD / uploads            | S3 SSE-S3 or SSE-KMS              |
| Driver tokens (mobile)   | `expo-secure-store` (OS keychain) |

### JWT

- User tokens: Clerk RS256 via JWKS (`auth/clerk.py`)
- Porterchain-issued: HS256 for driver session + Fleetbase SSO (`JWT_SECRET`)
- Short TTL on SSO tokens (default 300s); driver access tokens 15–60 min

---

## Authentication security

See [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md).

| Control           | Implementation                                        |
| ----------------- | ----------------------------------------------------- |
| Identity provider | Clerk only — no Supabase/Twilio OTP                   |
| Authorization     | Server-side RBAC — [RBAC_MATRIX.md](./RBAC_MATRIX.md) |
| Invite tokens     | Opaque, hashed at rest, expiry enforced               |
| Clerk MFA         | Recommended for admin and merchant admins             |
| Dev bypass        | `CLERK_DEV_BYPASS` — local only (`APP_ENV=local`)     |
| Delivery POD OTP  | Operational proof-of-delivery — not user auth         |

---

## API security

### Rate limiting (recommended)

| Endpoint class   | Limit                           |
| ---------------- | ------------------------------- |
| Auth (`/auth/*`) | 10 req/min per IP               |
| Driver invite    | 15–30 req/min                   |
| Public quote API | 60 req/min per API key          |
| Webhooks         | Signature verify; no rate limit |

Implement with Redis + middleware (FastAPI).

### CORS (target)

```python
ALLOWED_ORIGINS = [
    "https://porterchain.com",
    "https://www.porterchain.com",
    "https://admin.porterchain.com",
    "https://merchant.porterchain.com",
    "https://driver.porterchain.com",
    "https://customer.porterchain.com",
    "http://localhost:3000",  # dev
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
]
```

No wildcard `*` in production.

### Security headers (Next.js)

`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Strict-Transport-Security` — configure in each app's `next.config.ts`.

### Input validation

- Pydantic on all FastAPI endpoints
- Zod on Next.js server actions
- ORM only — no raw SQL interpolation
- File upload: MIME + size limits (POD max 10MB)

---

## Webhook security

### Stripe

Verify signature on every request; idempotency via stored `event.id`; process async where possible.

### Outbound merchant webhooks

- HMAC-SHA256: `X-Porterchain-Signature`
- Timestamp header (replay window)
- Retry with exponential backoff

---

## Network security

### Docker

- PostgreSQL, Redis, MySQL on internal networks
- No public binding for database ports in production compose
- Routing engines (OSRM/Valhalla) accessible only from API containers

### Production firewall

- Public: 443 only (80 → redirect)
- API behind reverse proxy / WAF

---

## File upload security

| Control  | Detail                                  |
| -------- | --------------------------------------- |
| Max size | 10 MB photos, 1 MB signatures           |
| Types    | `image/jpeg`, `image/png`, `image/webp` |
| Storage  | Private bucket; signed URLs             |
| EXIF     | Strip GPS from customer uploads         |

---

## Dependency security

See [DEPENDENCY_REPORT.md](./DEPENDENCY_REPORT.md).

| Action                 | Frequency    |
| ---------------------- | ------------ |
| `pnpm audit`           | Every CI run |
| `pip audit` (API)      | Every CI run |
| Dependabot / Renovate  | Weekly       |
| Container scan (Trivy) | On build     |

---

## Logging and monitoring

### Log

Auth failures (WARN), rate limits (WARN), webhook failures (ERROR), admin actions (INFO audit).

### Do not log

Passwords, JWT tokens, OTP codes, card numbers, secret keys.

### Sentry (recommended)

Separate projects per app; scrub PII in `beforeSend`.

---

## Backups

| Asset             | Method                   | Retention |
| ----------------- | ------------------------ | --------- |
| PostgreSQL        | pg_dump + WAL            | 30 days   |
| MySQL (Fleetbase) | Daily dump + binlog      | 30 days   |
| Redis             | AOF snapshot             | 7 days    |
| S3 uploads        | Cross-region replication | 1 year    |

**RPO:** 1 hour · **RTO:** 4 hours · Test restore quarterly.

---

## Compliance

| Regulation      | Relevance    | Notes                          |
| --------------- | ------------ | ------------------------------ |
| PIPEDA (Canada) | Customer PII | Privacy policy on website      |
| PCI DSS         | Card data    | Stripe-hosted — SAQ A eligible |
| GDPR            | EU traffic   | Limited scope                  |

---

## Incident response

1. Detect (Sentry, uptime, Stripe fraud)
2. Contain (rotate keys, disable API keys)
3. Assess scope (PII, payments)
4. Notify (ops, legal if PIPEDA threshold)
5. Remediate and post-mortem

---

## Pre-production checklist

- [ ] All secrets rotated if ever in git history
- [ ] HTTPS + HSTS enforced
- [ ] CORS restricted to known origins
- [ ] Rate limiting on auth endpoints
- [ ] Stripe webhook signature verified
- [ ] Google/API keys restricted
- [ ] PostgreSQL not publicly accessible
- [ ] Sentry with PII scrubbing
- [ ] Backups tested
- [ ] No high/critical dependency CVEs
- [ ] `.gitignore` covers secret file patterns

---

## Related documents

| Document                                                           | Purpose                   |
| ------------------------------------------------------------------ | ------------------------- |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) | Auth policy               |
| [RBAC_MATRIX.md](./RBAC_MATRIX.md)                                 | Authorization             |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)             | Env reference             |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) | Go/no-go                  |
| [docs/archive/SECURITY_AUDIT.md](./docs/archive/SECURITY_AUDIT.md) | Historical audit snapshot |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
