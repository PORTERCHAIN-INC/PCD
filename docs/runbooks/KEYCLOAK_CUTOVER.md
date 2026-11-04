# Keycloak cutover (Clerk retirement) — manual ops runbook

**Status:** live runbook (L36). Do **not** execute from Cursor agents. Production steps are
run by Ravi only. Agents work on local branches and throwaway Docker containers.

Clerk is removed from code, infra, workflows and env templates. Production still needs the
steps below, in order. No production secrets were changed or deleted by the code change.

## Steps

1. **Secrets (SOPS, `secrets/*.enc.yaml`):** add `KEYCLOAK_ADMIN_CLIENT_SECRET` (pc-api-admin)
   and `AUTH_SESSION_SECRET` (32+ random chars). `infrastructure/deploy/sync-secrets.sh`
   refuses to deploy without them and strips any leftover `CLERK_*` keys.
2. **Realm:** render and re-import `infrastructure/keycloak/realm-porterchain.json`
   (`render-realm.sh`); configure realm SMTP (ZeptoMail); create staff users (admin and
   super admin enrol TOTP at first login).
   New-device email code for non-staff: see `docs/runbooks/NEW_DEVICE_EMAIL_CODE.md` (jar + theme + `scripts/keycloak-email-otp-setup.sh`).
3. **Users:** run `infrastructure/keycloak/migrate_clerk_users.py` against the Clerk export.
   It writes `subject-remap.csv` (legacy_subject, keycloak_sub, email).
4. **Database:** `alembic upgrade head` with `PCD_SUBJECT_REMAP_CSV=<path to subject-remap.csv>`.
   Revision `kc8authsubject0008` renames `clerk_user_id` → `auth_subject` and backfills
   subjects from the CSV.
5. **Deploy**, then smoke: website `/en/login`, each portal `/auth/login`, both mobile apps
   with the reviewer accounts.
6. **Clean up:** delete `CLERK_*` from Doppler / GitHub secrets; close the Clerk apps.

## Rollback

`alembic downgrade kc7dropclerkwh0007` restores the column names (subjects stay Keycloak
subs). Redeploy the previous image tag. There is no production Clerk path left in code,
so rollback means the previous release, not a config flag.
