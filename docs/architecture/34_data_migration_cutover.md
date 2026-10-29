# 34 · Data migration and cutover (PCD live → Phase 1)

Rules: L13, which means a full local rehearsal first and the live DB is never touched by a rehearsal. Migrations use expand → migrate → contract only. Every step has a rollback point.

## Steps

| Step | What                                                                                                                                                     | Week                       | Rollback                                                                       |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------ |
| M1   | Snapshot live Postgres (pg_dump + WAL position) into a rehearsal copy on Ubuntu (port 55632)                                                             | 4                          | n/a                                                                            |
| M2   | Run the Alembic expand migrations (new tables from 14, `event_outbox`, `processed_events`, BOL, temp logs). Old columns stay                             | 4                          | downgrade script per revision, tested in rehearsal                             |
| M3   | Backfill: POD retention flags to 6 years (A01), single invoice status (A02), credit-note issuer (A03), enums (A15–A18), merchant tier from 90-day volume | 4–5                        | backfill writes new columns only, so drop them to roll back                    |
| M4   | Domain events: Redis `bus.py` XADD replaced by outbox writes; the old Redis stream drains to empty, then is turned off                                   | 4                          | feature flag `EVENTS_VIA_OUTBOX=false`                                         |
| M5   | Clerk → Keycloak (below)                                                                                                                                 | 2 (stand up), 5 (cut over) | Clerk stays live and read-only for 14 days                                     |
| M6   | Rate card v2: old tariffs archived, Kaylulu contract re-entered as a dated override                                                                      | 2                          | old pricing path behind a flag until week 6                                    |
| M7   | Dual-run: new workflows and consumers run in shadow next to the old sweeps; parity tests compare outputs daily                                           | 4–7                        | pause the new path, resume the sweep                                           |
| M8   | Contract: drop old columns and tables (`domain_events` after a 6-year read-only window; never POD/invoices)                                              | Phase 2                    | restore from backup                                                            |
| M9   | Final rehearsal on a fresh live copy, then cutover in a low-volume window (Sun 02:00–05:00 Toronto)                                                      | 14                         | DNS / Caddy back to the old stack; DB restore point taken right before cutover |

## Clerk → Keycloak user migration

1. **Week 2:** run Keycloak 26 on the droplet, because end users must be able to log in when Ubuntu is off. Its DB is the droplet Postgres, replicated to Oracle. Realms: `business` (merchants, customers, drivers) and `staff` (admin, super-admin, which can also be served from Ubuntu).
2. **Export users:** use the Clerk Backend API to export users (id, email, phone, org, roles, metadata). Clerk doesn't export password hashes for every hasher, so plan for no passwords.
3. **Import:** use Keycloak's admin REST partial import. Keep the Clerk user id as attribute `legacy_clerk_id`, and the API maps the `sub` claim from either issuer during dual-run (the JWT verifier accepts both JWKS).
4. **First login:** email magic link / required action "UPDATE_PASSWORD" or WebAuthn passwordless registration. **Passkeys must be re-enrolled.** Clerk passkeys are bound to the Clerk RP ID, so all users register a new passkey under `auth.porterchain.com`. Show a banner for 30 days in the portals and apps.
5. **Mobile:** both apps switch from `@clerk/expo` to `react-native-app-auth` / `expo-auth-session` (OIDC + PKCE). Fix the iOS associated domain to `webcredentials:auth.porterchain.com` (also fixes doc 25 C-issue).
6. **Staff:** super-admin TOTP + passkey are required. Impersonation (super-admin only) is done with a Keycloak token-exchange audit event.
7. **Dual-run (week 5, 7–14 days):** both issuers are accepted. New sign-ups go to Keycloak only. Then Clerk is removed: scripts and tables are deleted (file 32), and the `clerk_webhook_events` table moves to an archive.
8. **Rollback:** switch the issuer flag back to Clerk, which is possible while the Clerk instance still exists (keep it on the free tier until day 14).

**Done check:** 100% of active users have a Keycloak id, and 0 auth calls go to Clerk for 7 days.
