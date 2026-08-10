# Phase 8 — business FK backfill (internal UUID)

**Type:** WORKING  
**Status:** Phase 8 local — additive columns + dry-run-first backfill; no column drops  
**Date:** 2026-07-28  
**Related:** [unified-identity-target.md](./unified-identity-target.md) · [identity-migration-cli.md](./identity-migration-cli.md)

---

## 1. Findings

There are **no** `clerk_user_id` columns on orders / quotes / payments. Operational rows already FK to profile PKs (`customers.id`, etc.).

Phase 8 therefore adds `porterchain_user_id` → `porterchain_users.id` on **profile / invite** tables and backfills from Clerk subject → internal UUID, while **retaining** `clerk_user_id`.

| Table              | Legacy column kept | New column            |
| ------------------ | ------------------ | --------------------- |
| `admin_users`      | `clerk_user_id`    | `porterchain_user_id` |
| `merchant_users`   | `clerk_user_id`    | `porterchain_user_id` |
| `customers`        | `clerk_user_id`    | `porterchain_user_id` |
| `drivers`          | `clerk_user_id`    | `porterchain_user_id` |
| `user_invitations` | `clerk_user_id`    | `porterchain_user_id` |

Also heals `identity_links.platform_user_id` when it still points at a legacy profile UUID instead of `porterchain_users.id`.

Migration: `y8z9a0b1c2d3_unified_identity_phase8_fk_backfill.py` (nullable FK, `ON DELETE SET NULL`).

---

## 2. Resolution order

1. `porterchain_users.clerk_user_id == subject`
2. `identity_links` → `platform_user_id` if that id exists in `porterchain_users`
3. Optional `--create-missing` (apply only): create unprovisioned `porterchain_users` stub
4. Else: unmatched (reported; no silent elevate)

Pending / `dev_clerk_user` ids are skipped.

---

## 3. Commands

```bash
pnpm db:migrate   # applies y8z9a0b1c2d3 when DB is up

pnpm identity:migrate -- backfill-audit
pnpm identity:migrate -- backfill                  # dry-run (default)
pnpm identity:migrate -- backfill --create-missing # dry-run preview of creates
pnpm identity:migrate -- backfill --apply --confirm APPLY
pnpm identity:migrate -- backfill --apply --confirm APPLY --create-missing
```

Ensure-user dual-write also sets `porterchain_user_id` on legacy profiles when present.

---

## 4. Explicit confirmation

> No production Clerk / Doppler resources were changed. Legacy `clerk_user_id` columns were not dropped. Production apply of backfill remains a founder/security-owned gate.
