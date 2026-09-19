# Security

**Type:** CANONICAL  
**Parent:** [`infrastructure/system.md`](./infrastructure/system.md)  
**Verified against code:** 2026-09-12  
**Lens:** Jeff Dean — least privilege; fail closed; boring secrets.

---

## Posture (coded)

| Area          | Rule                                                    | SoT                                    |
| ------------- | ------------------------------------------------------- | -------------------------------------- |
| Portal authn  | Clerk JWKS/secret per portal                            | `Settings` `CLERK_*` · `auth/clerk.py` |
| Admin authn   | Staff IdP (Clerk retired for staff login)               | `staff_idp_service.py`                 |
| Authz         | SpiceDB live Check; deny if down; no Check-result cache | `authz/client.py` · `require_module`   |
| Dev bypass    | Only `APP_ENV=local` + `clerk_dev_bypass` / portal flag | `auth/dev.py` · `packages/auth`        |
| Secrets       | Doppler prod; `env/clerk.env` + `pnpm clerk:sync` local | deploy SECRETS docs                    |
| Network       | Browsers → API only                                     | no Fleetbase/SocketCluster SDK in web  |
| Payments      | Stripe signature + idempotent webhooks                  | `stripe_webhook_service` / COD service |
| Retired flags | `CLERK_UNIFIED_MODE` must remain false                  | config validator                       |

---

## Explicit non-goals

- Homegrown session crypto replacing Clerk/Staff IdP
- Module catalogs as authorization SoT
- Check allow-caching
- Prod auth bypass

---

## Related

[`RUNBOOK.md`](./RUNBOOK.md) · [`docs/SECRETS_MAP.md`](./docs/SECRETS_MAP.md) · [`infrastructure/deploy/README.md`](./infrastructure/deploy/README.md) · [`INTEGRATIONS.md`](./INTEGRATIONS.md)
