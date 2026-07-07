# ADR-013 — Production secret manager

**Type:** CANONICAL ADR  
**Status:** Accepted  
**Date:** 2026-07-06  
**Checklist:** §5.1.13 (DD-14), §11.1.14  
**Related:** [infrastructure/deploy/SECRETS.md](../../infrastructure/deploy/SECRETS.md) · [SECURITY.md](../../SECURITY.md)

---

## Context

Production deploys wrote secrets into `/opt/porterchain/.env` via a GitHub Actions heredoc on every release. That pattern:

- Duplicates secret storage (GitHub + droplet disk)
- Makes rotation manual and error-prone
- Fails diligence questions on secret manager and audit trail

Local development correctly uses gitignored `.env` files from `env/*.example` templates.

---

## Decision

Use **Doppler** as the **system of record** for production runtime secrets on the DigitalOcean droplet.

| Layer | Stores |
| ----- | ------ |
| **Doppler** (`pcd` / `prd`) | All prod API + compose secrets |
| **GitHub Actions** | `DEPLOY_*`, `DOPPLER_TOKEN`, build-time `NEXT_PUBLIC_*` |
| **Droplet disk** | Generated `.env` (mode `600`) + `secrets/firebase-service-account.json` — never hand-edited |

`infrastructure/deploy/sync-secrets.sh` pulls from Doppler when `DOPPLER_TOKEN` is set; otherwise falls back to legacy per-secret GitHub injection for migration.

---

## Consequences

**Positive**

- Single rotation surface (Doppler UI / CLI)
- Deploy audit trail in Doppler + GitHub Actions
- DD-14 / §5.1.13 closable with documented runbook

**Negative**

- External dependency (Doppler SaaS); mitigated by legacy GitHub fallback
- One-time migration effort to populate Doppler project

---

## Out of scope

- HashiCorp Vault (defer until compliance requires self-hosted)
- Storing secrets in PostgreSQL or admin UI
- Committing `doppler.yaml` secrets (only project/config names are in repo)

---

## Governance

| Document | Role |
| -------- | ---- |
| [PRIORITY_TODOS.md](../PRIORITY_TODOS.md) | DD-14 tracking |
| [RUNBOOK.md](../../RUNBOOK.md) | Rotation procedures |
