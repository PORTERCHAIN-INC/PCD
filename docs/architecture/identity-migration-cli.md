# Identity migration CLI (Phase 7)

**Type:** WORKING  
**Status:** Phase 7 local tooling — dry-run default; no production Clerk/Doppler cutover  
**Date:** 2026-07-28  
**Related:** [unified-identity-target.md](./unified-identity-target.md) · [clerk-consolidation.md](../runbooks/clerk-consolidation.md)

---

## 1. Purpose

Consolidate users from legacy Clerk apps (Admin / Merchant / Driver / Customer) into PorterChain Platform identity (`porterchain_users` + `identity_links` + `user_role_assignments`).

Bookkeeping tables (Phase 2): `identity_migration_runs`, `identity_migration_records`.

---

## 2. Non-negotiables

1. Dry-run is the default. Apply requires `--confirm APPLY`.
2. Clerk exports live **outside** the git repo (never commit exports).
3. Never log passwords, MFA secrets, tokens, or full secret keys.
4. Matching: explicit map > existing identity link > verified email candidate.
5. Same verified email across legacy apps **≠** auto-merge (requires map).
6. Invite-only / admin roles only via reviewed **admin allowlist**.
7. Clerk `public_metadata` / `unsafe_metadata` role hints are **ignored** for elevation (recorded as `metadata_role_hint_ignored`).
8. Do not call production Clerk/Doppler from agents. Do not delete legacy apps.

---

## 3. Commands

```bash
# Summarize exports (and optional legacy DB clerk_user_id counts)
pnpm identity:migrate -- audit --exports-dir ~/porterchain-migration-exports --db

# Build plan (persists run; always dry_run=true on the run row)
pnpm identity:migrate -- plan \
  --exports-dir ~/porterchain-migration-exports \
  --label "local-dev-1" \
  --map ~/porterchain-migration-exports/map.json \
  --admin-allowlist ~/porterchain-migration-exports/admin-allowlist.json

pnpm identity:migrate -- dry-run --run-id <uuid>
pnpm identity:migrate -- conflicts --run-id <uuid>
pnpm identity:migrate -- apply --run-id <uuid> --confirm APPLY
pnpm identity:migrate -- verify --run-id <uuid>
```

Or from `apps/api`:

```bash
PYTHONPATH=src:../../shared/python .venv/bin/python scripts/identity_migrate.py audit --help
```

Email candidates are not applied unless `--accept-email-candidates` is set.

---

## 4. File shapes (names only)

### Export file (`~/…/customer.json`)

```json
{
  "source_app": "customer",
  "issuer": "https://<instance>.clerk.accounts.dev",
  "users": [
    {
      "id": "user_xxx",
      "email_addresses": [
        { "email_address": "a@example.com", "verification": { "status": "verified" } }
      ]
    }
  ]
}
```

Filename may include the portal name (`admin.json`, …) when the JSON omits `source_app`.

### Admin allowlist

```json
{
  "legacy_admin_clerk_user_ids": ["user_admin_1"],
  "role_by_clerk_user_id": {
    "user_admin_1": ["admin"]
  }
}
```

### Explicit map

```json
{
  "links": [
    {
      "source_app": "admin",
      "source_clerk_user_id": "user_old",
      "target_clerk_user_id": "user_platform",
      "internal_user_id": null,
      "roles": ["admin"]
    }
  ]
}
```

---

## 5. Record statuses

| Status                   | Meaning                                                       |
| ------------------------ | ------------------------------------------------------------- |
| `matched_map`            | Reviewed explicit map                                         |
| `matched_identity`       | Existing `identity_links` / `porterchain_users.clerk_user_id` |
| `email_candidate`        | Unique verified email match (gated on apply)                  |
| `unmatched`              | New customer/driver create candidate                          |
| `conflict`               | Needs human resolution                                        |
| `dry_run_ok` / `applied` | After dry-run / apply                                         |

---

## 6. Explicit confirmation

> No production Clerk applications, Doppler configs, or production databases were changed or deleted by Phase 7 tooling development. Apply against production remains a founder/security-owned manual gate.
