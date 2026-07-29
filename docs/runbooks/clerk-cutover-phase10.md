# Phase 10 — Clerk consolidation cutover (manual only)

**Type:** RUNBOOK (production gate)  
**Status:** Documented — **do not execute from Cursor agents**  
**Date:** 2026-07-28  
**Owner:** Founder / security owner (human)  
**Companion:** [clerk-consolidation.md](./clerk-consolidation.md) · [clerk-doppler-secret-matrix.md](../architecture/clerk-doppler-secret-matrix.md) · [identity-migration-cli.md](../architecture/identity-migration-cli.md)

---

## 0. Purpose of Phase 10

Phases 1–9 delivered architecture, schema, clients, tooling, and tests.

**Local code default (2026-07-28+):** PorterChain Platform only (`CLERK_MODE=unified`, Platform = ex Porterchain Admin). Invites/directory/JWKS use one Backend API.

Phase 10 production cutover remains **manual**: Doppler flip, user import/re-invite from legacy apps, then **founder deletes** Customer / Merchant / Driver Clerk applications. Agents never delete apps or mutate Doppler `prd`.

> **Agent prohibition:** Do not run `upload-clerk-to-doppler.sh` against prod, do not delete Clerk apps, do not mutate Doppler `prd`, do not apply migration `--confirm APPLY` against production DBs, do not rotate live keys from this workstream.

---

## 1. Pre-cutover readiness (local workstream complete)

| Gate              | Evidence                                             | Status expected before human cutover |
| ----------------- | ---------------------------------------------------- | ------------------------------------ |
| P1 Audit          | Impact + target + characterization                   | Done                                 |
| P2 Schema         | `porterchain_users` / assignments / migration tables | Done (additive)                      |
| P3 IdP            | `CurrentPrincipal` + `/v1/auth/session-context`      | Done (dual-read)                     |
| P4 Sync           | `/webhooks/clerk` + ensure-user                      | Done                                 |
| P5 Clients        | Unified pk mode + AccessGates                        | Done (local)                         |
| P6 Doppler matrix | Names + `pnpm config:audit`                          | Done (local; no prod mutate)         |
| P7 Migration CLI  | `pnpm identity:migrate` dry-run first                | Done                                 |
| P8 FK backfill    | `porterchain_user_id` additive; legacy cols kept     | Done                                 |
| P9 Test matrix    | `pnpm identity:test` green                           | Done locally                         |

Local verification before any human prod window:

```bash
pnpm identity:test
pnpm config:audit
pnpm identity:migrate -- backfill-audit   # against the intended env only when authorized
```

---

## 2. Roles & approvals

| Role                     | Responsibility                                            |
| ------------------------ | --------------------------------------------------------- |
| Founder / security owner | Go / no-go; retirement approval; Doppler prod changes     |
| Ops / deploy             | Image digests, Doppler version snapshot, rollback drill   |
| Identity eng             | Dry-run migration conflict report; admin allowlist review |
| Support                  | User comms (re-login / password reset)                    |

**Required recorded approvals before Step 1 of §4:**

- [ ] Security owner name + date
- [ ] Maintenance window agreed
- [ ] Rollback owner named
- [ ] Export storage path approved (outside git, encrypted)

---

## 3. Go / no-go checklist (day of)

**Go only if all are true:**

- [ ] `pnpm identity:test` green on the release commit
- [ ] Postgres backup completed + restore smoke known
- [ ] Clerk exports for all 4 legacy apps downloaded outside repo; checksums recorded (names only in tickets)
- [ ] Reviewed admin allowlist JSON ready (invite-only roles)
- [ ] Migration dry-run conflict count accepted or zero
- [ ] Doppler `prd` config version snapshotted
- [ ] Current API + portal image digests documented for rollback
- [ ] Unified Platform Clerk app exists in **production** Clerk (human-created)
- [ ] Webhook signing secret prepared for unified app (name only in Doppler plan)
- [ ] Mobile min-supported-version plan ready if old pk will be retired

**No-go if any:** unresolved admin allowlist gaps, dry-run conflicts unreviewed, backup missing, or agent-driven prod mutation was attempted.

---

## 4. Cutover sequence (human ops — ordered)

Do **not** execute from agents. Each step is a gate.

| #   | Step                                                                              | Rollback                          |
| --- | --------------------------------------------------------------------------------- | --------------------------------- |
| 1   | Backup Postgres; store Clerk export checksums outside repo                        | Restore DB from backup            |
| 2   | Confirm exports for Admin / Merchant / Driver / Customer (+ Platform target)      | N/A                               |
| 3   | Freeze sign-ups / enter maintenance if required                                   | Lift freeze                       |
| 4   | Final `identity:migrate` **dry-run**; review conflicts + allowlist                | Do not apply                      |
| 5   | Import users into unified **production** Clerk (Clerk UI / approved tooling only) | Keep legacy apps live             |
| 6   | Reconcile PC identities/roles (`plan` → authorized `apply`); never admin-by-email | Revert migration run; keep legacy |
| 7   | Optional authorized `backfill --apply` for `porterchain_user_id`                  | FK nullable; leave unset          |
| 8   | Deploy API with dual-issuer / dual-key read if needed                             | Redeploy prior API digest         |
| 9   | Deploy portals/website with unified publishable key                               | Rebuild with prior pk             |
| 10  | Mobile release + min version before retiring old pk                               | Keep old pk builds working        |
| 11  | Doppler: **add** unified names alongside legacy → flip consumers → observe        | Restore prior Doppler version     |
| 12  | Persona smoke tests (§6 in main runbook)                                          | Rollback images + Doppler         |
| 13  | Monitor 401/403, webhooks, old-issuer traffic for observation window              | Rollback                          |
| 14  | User communication (re-login / reset where needed)                                | Support scripts                   |
| 15  | Disable legacy webhooks only after unified healthy                                | Re-enable legacy webhooks         |
| 16  | Revoke legacy Doppler tokens / Clerk sk after window                              | Re-issue emergency only           |
| 17  | Secure-delete temp exports per retention                                          | N/A                               |
| 18  | Delete legacy Clerk **applications** only after retirement checklist (§5)         | Impossible — do not rush          |

---

## 5. Retirement checklist (all required)

Copy from main runbook; all must be checked before permanent deletion:

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

**Still do not drop** `clerk_user_id` columns until a later, separately approved schema retirement (post Phase 8 keep-alive).

---

## 6. Observation window (suggested)

| Signal                           | Watch                          |
| -------------------------------- | ------------------------------ |
| Auth 401 / 403 by portal         | Spike → rollback consideration |
| Webhook failures / duplicates    | Unified endpoint health        |
| JWKS / wrong issuer rejects      | Dual-issuer misconfig          |
| Old `CLERK_*_JWKS_URL` traffic   | Should fall to zero after flip |
| Unresolved / conflict identities | Migration follow-up            |
| Driver cookie session refresh    | Driver portal path             |

Default observation before revoking legacy secrets: **≥ 7 days** (owner may extend).

---

## 7. Forbidden automation (Phase 10 forever)

Agents and CI in this workstream must **not**:

1. Call Doppler write APIs against `prd` for Clerk cutover
2. Run `upload-clerk-to-doppler.sh` / `prune-legacy-clerk-doppler.sh` without explicit human command outside this phase doc
3. Delete Clerk applications or users in production
4. `identity:migrate apply` / `backfill --apply` against production without recorded human approval in the change ticket
5. Commit Clerk exports, allowlists with PII, or secret values
6. Drop `clerk_user_id` columns

---

## 8. Sign-off template

```text
Cutover window: ____________________ (UTC)
Release commit / image digests: ____________________
Doppler prd snapshot version: ____________________
Dry-run conflict count: ____________________
Admin allowlist reviewer: ____________________
Go / no-go: GO | NO-GO
Security owner: ____________________ date: __________
Rollback owner: ____________________
Phase 10 executed from agents? NO (required)
```

---

## 9. Explicit confirmation

> No production Clerk applications, Doppler production configs, deployed infrastructure, or production databases were changed or deleted by Phase 10 documentation work. Cutover remains a founder/security-owned manual operation.
