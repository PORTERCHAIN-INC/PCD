# Clerk / Doppler secret-access matrix (Phase 6)

**Type:** WORKING  
**Status:** Updated 2026-08 — SoT is `platform_driver` (not unified)  
**Date:** 2026-07-28  
**Related:** [SECRETS_MAP.md](../SECRETS_MAP.md) · [SSO.md](../../SSO.md)

---

## 1. Principles

1. Doppler is the production secret SoT. Local uses `env/clerk.env` → `pnpm clerk:sync`.
2. Docs and tooling report **names + validity** only — never secret values.
3. One Clerk Platform app ≠ one shared Doppler bag for every consumer class.
4. Separate Doppler configs for **dev / staging / prod**. Prod workloads use read-only config-scoped service tokens.
5. Agents / automation in this workstream must **not** run `upload-clerk-to-doppler.sh` against production.

---

## 2. Consumer access matrix (`platform_driver`)

| Consumer               | May hold (names)                                                                                                                                  | Must not hold                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| API / worker           | Platform triad + `CLERK_DRIVER_*`, `CLERK_WEBHOOK_SIGNING_SECRET`, azp/issuers/audience, `CLERK_MODE=platform_driver`, `CLERK_UNIFIED_MODE=false` | Client-only redirect UX secrets that belong in Next public env only  |
| Next portals / website | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (Platform or Driver per app), public redirect URL vars                                                        | `CLERK_SECRET_KEY`, webhook signing secret, any `sk_*`               |
| Expo (when wired)      | `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`                                                                                                               | Any server secret / JWKS private material                            |
| GitHub Actions (build) | Publishable keys only (`pk_*` / portal publishable slots)                                                                                         | `sk_*`, JWKS signing secrets, webhook secrets                        |
| Doppler                | Per-env configs; service tokens scoped read-only for prod deploy                                                                                  | Cross-env mixing; frontend+backend secret bags in one unmanaged file |

---

## 3. Supported sync mode

| Mode                         | Local source                      | Runtime (API)                                                                          | Build (Next)                                                             |
| ---------------------------- | --------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `CLERK_MODE=platform_driver` | Platform triad + `CLERK_DRIVER_*` | Expand Platform → customer/merchant/admin; Driver separate; `CLERK_UNIFIED_MODE=false` | Platform pk on website/customer/merchant/admin; Driver pk on driver apps |

`CLERK_MODE=unified` and `enterprise` are **retired** — sync/upload/validate exit.

---

## 4. Startup validation (API)

Implemented in `porterchain_api.auth.clerk_config_audit` + `Settings.require_clerk_in_production`.

| Check                                                     | Non-local behavior |
| --------------------------------------------------------- | ------------------ |
| Incomplete Clerk config                                   | Fail boot          |
| `CLERK_DEV_BYPASS=true`                                   | Fail boot          |
| `pk_test_` / `sk_test_` present                           | Fail boot          |
| Publishable live + secret test (or reverse)               | Fail boot          |
| `CLERK_AUTHORIZED_ISSUERS` set but no JWKS issuer overlap | Fail boot          |
| Unified Platform live keys (triad + slot aliases)         | Boot OK            |

Local / development: warnings via `pnpm config:audit`; boot remains permissive for test keys.

---

## 5. config-audit CLI

```bash
pnpm config:audit              # human report (names + status)
pnpm config:audit -- --json    # JSON
pnpm config:audit -- --strict  # exit 1 if production_errors non-empty
```

Never prints secret values. Does **not** call Doppler.

Shell validator (format + optional JWKS fetch):

```bash
bash infrastructure/deploy/scripts/validate-clerk-keys.sh env/clerk.env
```

---

## 6. Manual Doppler cutover / rollback matrix

| Step | Action                                                   | Rollback                      |
| ---- | -------------------------------------------------------- | ----------------------------- |
| A    | Snapshot Doppler `prd` config version / export **names** | Restore prior Doppler version |
| B    | Add unified Clerk names alongside legacy (dual-read)     | Leave legacy keys active      |
| C    | Deploy API that accepts unified **and** legacy issuers   | Redeploy previous API image   |
| D    | Point portals at unified publishable key (build)         | Rebuild with prior pk secrets |
| E    | Freeze signups on legacy Clerk apps                      | Re-enable legacy apps         |
| F    | Observation window → revoke legacy sk / tokens           | Re-issue only if emergency    |

Never delete legacy Doppler keys until verification + approved retirement window.

---

## 7. Explicit confirmation

> No production Clerk applications, Doppler production configs, deployed infrastructure, or production databases were changed or deleted by Phase 6. Cutover remains a documented manual operation.
