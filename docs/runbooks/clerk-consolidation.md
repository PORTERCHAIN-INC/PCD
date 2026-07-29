# Runbook: Clerk consolidation (4 apps → PorterChain Platform)

**Type:** RUNBOOK  
**Status:** Manual — do **not** execute production cutover from agents  
**Date:** 2026-07-28  
**Related:**  
[unified-identity-impact-report.md](../architecture/unified-identity-impact-report.md) ·  
[unified-identity-target.md](../architecture/unified-identity-target.md) ·  
[clerk-cutover-phase10.md](./clerk-cutover-phase10.md) ·  
[SECRETS_MAP.md](../SECRETS_MAP.md) ·  
[CLERK_APPS_SETUP.md](../../infrastructure/deploy/CLERK_APPS_SETUP.md)

---

## 0. Non-negotiables (read first)

1. Never authorize from email.
2. Email = verified match signal only.
3. Never use Clerk user IDs as business primary keys going forward.
4. Never put authz in Clerk `unsafeMetadata`.
5. Frontend guards are not authorization.
6. Every protected API resource checks auth + permission.
7. Deny by default (401 vs 403).
8. Never print, log, commit, or document secret **values**.
9. Doppler remains secret SoT — no unmanaged prod `.env` inventing keys.
10. **Do not** modify production Clerk apps, Doppler prod configs, deployed infra, or prod DBs from automation in this workstream.
11. **Do not** delete old Clerk apps, users, credentials, exports, DB columns, migrations, or prod data until retirement checklist + approvals.
12. Preserve unrelated dirty working tree changes.
13. No broad dependency upgrades (frontend freeze).

---

## 1. Current vs target (one line)

**Local (forced):** 1 Clerk app — **PorterChain Platform** (ex Porterchain Admin); `CLERK_MODE=unified`; all portals share one pk/sk/jwks.  
**Prod Doppler / live Clerk apps:** founder still flips Doppler and deletes Customer / Merchant / Driver apps after import/re-invite (agents never delete apps).  
**Authz SoT:** PC DB multi-role + permissions; Clerk IDs only as IdP subjects (`identity_links` / profile `clerk_user_id`).

---

## 2. Local development (safe)

```bash
# Status — preserve unrelated changes
git status

# Full identity matrix (Phases 1–10 doc guards + 2–9 suites)
pnpm identity:test

# Local Clerk (gitignored) — unified only (PorterChain Platform)
# Platform triad = CLERK_PUBLISHABLE_KEY / CLERK_SECRET_KEY / CLERK_JWKS_URL
# (or derive from CLERK_ADMIN_* — Platform was renamed from Porterchain Admin)
# CLERK_MODE=enterprise is retired — sync exits with an error if requested
pnpm clerk:sync   # fans Platform keys to all portals + API; sets CLERK_UNIFIED_MODE=true
pnpm config:audit # expect mode=unified
```

Do **not** run `upload-clerk-to-doppler.sh` against production as part of exploratory work.

### Phase 5 local notes

- **Forced Platform-only:** `scripts/sync-clerk-env.mjs` is unified-only; registry collapses all `clerk_client_for_kind` calls to the Platform triad.
- All Next apps + Expo shells receive the **same** publishable key.
- Secrets stay server-only (`CLERK_SECRET_KEY` / portal slot names still written for compat).
- AccessGates call `GET /v1/auth/session-context` and `canAccessPortal` (SpiceDB permissions). Removed: `/v1/auth/*/access`.
- API `CLERK_UNIFIED_MODE=true` skips enterprise app-mismatch + exclusivity; invite-only portals still require provisioning.
- Auth domain / azp: prefer `auth.porterchain.com` in Clerk Dashboard; allowlist PorterChain origins via `CLERK_AUTHORIZED_PARTIES` (names in `env/api.env.example`).
- Mobile Expo shells stay blank feature-wise; `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` is written for future wiring only.
- **Human:** after consumers are on Platform, delete Customer / Merchant / Driver Clerk applications yourself (import/re-invite first). Agents never delete Clerk apps.

### Phase 7 local notes

- Migration CLI: `pnpm identity:migrate` (audit → plan → dry-run → apply → verify).
- Exports **outside** the repo; admin allowlist required for invite-only roles.
- Metadata roles never elevate. Same email across apps requires an explicit map.
- Doc: [identity-migration-cli.md](../architecture/identity-migration-cli.md).

### Phase 8 local notes

- Additive `porterchain_user_id` on admin/merchant/customer/driver/invitation profiles (Alembic `y8z9a0b1c2d3`).
- Legacy `clerk_user_id` retained — no drops.
- `pnpm identity:migrate -- backfill-audit` / `backfill` (dry-run default; `--apply --confirm APPLY`).
- Doc: [identity-fk-backfill.md](../architecture/identity-fk-backfill.md).

### Phase 9 local notes

- Full matrix: `pnpm identity:test` (Phases 1–9 characterization + suites).
- Covers 401/403, org IDOR isolation, webhook signature/idempotency, session-context safety, portal permission parity.
- Doc: [identity-test-matrix.md](../architecture/identity-test-matrix.md).

### Phase 10 — production cutover (manual only)

- **SSOT:** [clerk-cutover-phase10.md](./clerk-cutover-phase10.md)
- Pre-cutover readiness, go/no-go, ordered human steps, retirement, observation window, sign-off template.
- Agents must **not** execute production Clerk / Doppler / DB cutover steps.

---

## 3. Secret-access matrix (names only)

**SSOT (Phase 6):** [clerk-doppler-secret-matrix.md](../architecture/clerk-doppler-secret-matrix.md)

### Portal slot aliases (filled from Platform triad)

| Portal   | Build (GitHub pk)                | Runtime (Doppler sk + JWKS)                            |
| -------- | -------------------------------- | ------------------------------------------------------ |
| Customer | `CLERK_CUSTOMER_PUBLISHABLE_KEY` | `CLERK_CUSTOMER_SECRET_KEY`, `CLERK_CUSTOMER_JWKS_URL` |
| Merchant | `CLERK_MERCHANT_PUBLISHABLE_KEY` | `CLERK_MERCHANT_*`                                     |
| Admin    | `CLERK_ADMIN_PUBLISHABLE_KEY`    | `CLERK_ADMIN_*`                                        |
| Driver   | `CLERK_DRIVER_PUBLISHABLE_KEY`   | `CLERK_DRIVER_*`                                       |

### Canonical (unified Platform)

| Consumer          | Names                                                                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| API / worker      | `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `CLERK_WEBHOOK_SIGNING_SECRET`, `CLERK_AUTHORIZED_PARTIES`, optional `CLERK_AUDIENCE` / `CLERK_AUTHORIZED_ISSUERS`, `CLERK_UNIFIED_MODE` |
| Next apps         | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (+ public redirect URL vars)                                                                                                               |
| Expo (when wired) | `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`                                                                                                                                            |

Keep separate Doppler configs for **dev / staging / prod**. Prod workloads: read-only config-scoped service tokens.

### Local validation (safe)

```bash
pnpm config:audit
pnpm config:audit -- --json
bash infrastructure/deploy/scripts/validate-clerk-keys.sh env/clerk.env
```

### Cutover / retirement matrix (manual checklist)

| Step | Action                                                | Rollback                      |
| ---- | ----------------------------------------------------- | ----------------------------- |
| A    | Snapshot Doppler `prd` config version / export names  | Restore prior Doppler version |
| B    | Ensure Platform triad + slot aliases dual-read        | Leave prior keys active       |
| C    | Deploy API that accepts Platform issuer               | Redeploy previous API image   |
| D    | Point portals at unified publishable key (build)      | Rebuild with prior pk secrets |
| E    | Stop minting sessions on legacy apps (freeze signups) | Re-enable legacy apps         |
| F    | After observation window, revoke legacy sk / tokens   | Re-issue only if emergency    |

Never delete legacy Doppler keys until verification + approved window.

---

## 4. Production cutover sequence (manual human ops)

**Phase 10 detail:** [clerk-cutover-phase10.md](./clerk-cutover-phase10.md) (readiness, go/no-go, sign-off).

Do **not** execute from Cursor agents. Founder / security owner owns each gate.

1. **Backup** Postgres + export checksum for Clerk user exports (encrypted temp storage outside repo).
2. Download Clerk exports for legacy Admin / Merchant / Driver / Customer (+ target if needed). Paths **outside** git.
3. Freeze sign-ups / maintenance window as needed.
4. Final **dry-run** migration + conflict review (admin allowlist required).
5. Import users into unified **production** Clerk (human + approved tooling).
6. Reconcile internal identities + roles (no admin-by-email).
7. Deploy backend (dual-issuer if needed).
8. Deploy portals (unified publishable key).
9. Mobile release + **minimum-supported-version** enforcement before retiring old pk.
10. Doppler key switch (add unified → flip consumers → observe).
11. Smoke test every persona: admin, merchant_owner, merchant_staff, driver, customer, multi-role.
12. Monitor: login failures, 401/403 spikes, unresolved identities, webhook failures, **old issuer** traffic.
13. Rollback = prior Doppler config + prior images (document image digests before flip).
14. User communication: re-login / password reset where credentials did not transfer.
15. Remove old webhook endpoints only after new webhooks healthy.
16. Revoke old Doppler service tokens and legacy Clerk API keys after window.
17. Secure-delete temporary exports containing password hashes per retention policy.
18. **Permanent** deletion of legacy Clerk applications only after retirement checklist.

---

## 5. Retirement checklist (all required)

- [ ] Source and target user counts reconciled
- [ ] All conflicts resolved or explicitly accepted
- [ ] No orphaned internal users
- [ ] No legacy Clerk IDs used as **active** business foreign keys
- [ ] No old-issuer traffic for approved observation period
- [ ] Active mobile users upgraded or blocked by min version
- [ ] Rollback window expired
- [ ] Backups + export retention approved
- [ ] Old webhooks disabled
- [ ] Old service tokens revoked
- [ ] Founder / security owner approval recorded

---

## 6. Persona smoke tests (post-cutover)

| Persona                     | Expect                                        |
| --------------------------- | --------------------------------------------- |
| Unauthenticated API         | 401                                           |
| Customer without admin role | Cannot hit admin modules (403)                |
| Driver                      | Driver jobs only; no merchant admin           |
| Merchant staff              | Org-scoped data only (IDOR fail)              |
| Support                     | Cannot assign `super_admin`                   |
| Suspended user              | Denied                                        |
| Multi-role user             | Workspace switch; server enforces permissions |
| Admin invite-only           | Sign-up alone does not grant staff            |

---

## 7. Monitoring signals

- Auth 401 / 403 rates by portal
- `identity_conflict` / unresolved subject counts (should trend to zero under unified model)
- Webhook failure / duplicate delivery metrics
- JWKS fetch errors / wrong issuer rejects
- Driver cookie session refresh failures
- Old `CLERK_*_JWKS_URL` traffic (should stop after flip)

---

## 8. Explicit confirmation (every PR / handoff)

> No production Clerk applications, Doppler production configs, deployed infrastructure, or production databases were changed or deleted by this workstream. Cutover and retirement remain documented manual operations.

---

## 9. Phase artifacts

| Artifact                    | Path                                                                              |
| --------------------------- | --------------------------------------------------------------------------------- |
| Impact report               | `docs/architecture/unified-identity-impact-report.md`                             |
| Target model                | `docs/architecture/unified-identity-target.md`                                    |
| This runbook                | `docs/runbooks/clerk-consolidation.md`                                            |
| Characterization tests      | `apps/api/tests/test_unified_identity_characterization.py`                        |
| Phase 2–5 tests             | `apps/api/tests/test_unified_identity_phase{2,3,4,5}.py`                          |
| Phase 6 tests               | `apps/api/tests/test_unified_identity_phase6.py`                                  |
| Phase 7 tests               | `apps/api/tests/test_unified_identity_phase7.py`                                  |
| Phase 8 tests               | `apps/api/tests/test_unified_identity_phase8.py`                                  |
| Phase 9 tests               | `apps/api/tests/test_unified_identity_phase9.py`                                  |
| Phase 10 tests              | `apps/api/tests/test_unified_identity_phase10.py` (doc / dry-run guards)          |
| Identity matrix runner      | `pnpm identity:test` → `apps/api/scripts/run_identity_matrix.py`                  |
| Phase 10 cutover            | `docs/runbooks/clerk-cutover-phase10.md`                                          |
| Clerk sync                  | `scripts/sync-clerk-env.mjs` (unified only; enterprise exits)                     |
| Config audit                | `pnpm config:audit` → `apps/api/scripts/config_audit.py`                          |
| Identity migrate            | `pnpm identity:migrate` → `apps/api/scripts/identity_migrate.py`                  |
| Doppler matrix              | `docs/architecture/clerk-doppler-secret-matrix.md`                                |
| Migration CLI doc           | `docs/architecture/identity-migration-cli.md`                                     |
| FK backfill doc             | `docs/architecture/identity-fk-backfill.md`                                       |
| Test matrix doc             | `docs/architecture/identity-test-matrix.md`                                       |
| Shared session/auth helpers | `packages/auth/src/session-context.ts` (apps import `@porterchain/auth` directly) |
