# 55 · Remaining item decisions (closing file 29)

Items the second-pass scan still couldn't match by name to docs 31–55, given an explicit decision here. Host per doc 28.

| Item                                                                | Category            | Decision                                                                                                |
| ------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------- |
| `api`                                                               | app/service/package | KEEP: FastAPI app; split host per doc 28 (public routers on droplet, admin routers on Ubuntu); week 2   |
| `customer-motion`                                                   | app/service/package | KEEP: shared animation package; week 2 (design system)                                                  |
| `mobile-theme`                                                      | app/service/package | KEEP: merge into design-system tokens; week 2                                                           |
| `ui`                                                                | app/service/package | KEEP: becomes the single design system for 5 portals; week 2                                            |
| `content_engine`                                                    | api module          | KEEP (blog/CMS); week 1                                                                                 |
| `gateway_engine`                                                    | api module          | KEEP; merge with `gateway` module (duplicate names) in Phase 2                                          |
| `marketing_site`                                                    | api module          | KEEP (website API); droplet; week 1                                                                     |
| `oauth_engine`                                                      | api module          | REPLACE by Keycloak OIDC for staff/business; keep only Shopify/partner OAuth parts; week 5              |
| `soft_delete`                                                       | api module          | KEEP (feeds deleted_items_purge); week 7                                                                |
| `spatial`                                                           | api module          | KEEP; self-hosted OSRM/Valhalla + PMTiles; week 4                                                       |
| `geo`                                                               | router              | KEEP; self-hosted geocoder (Pelias/Photon) replaces Google Places; week 4                               |
| `integrations.yaml`                                                 | config/CI           | KEEP; remove paid vendors (L26); week 1                                                                 |
| `knip.json`                                                         | config/CI           | KEEP (dead-code gate); week 1                                                                           |
| `opencode.json`                                                     | config/CI           | KEEP (dev tool config); week 1                                                                          |
| `pnpm-workspace.yaml`                                               | config/CI           | KEEP; week 1                                                                                            |
| `apps/api/alembic.ini`                                              | config/CI           | KEEP; single migrator on Ubuntu deploy lane (doc 32); week 2                                            |
| `apps/api/pyproject.toml`                                           | config/CI           | KEEP; add uv/ruff (latest-tech); week 1                                                                 |
| `apps/api/bandit.yaml`                                              | config/CI           | KEEP (PR gate, doc 38); week 1                                                                          |
| `env/admin.env.example`                                             | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/api.env.example`                                               | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/clerk.env.example`                                             | config/CI           | DELETE after Keycloak cutover (doc 34); week 5                                                          |
| `env/compose.env.example`                                           | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/customer-portal.env.example`                                   | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/driver-portal.env.example`                                     | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/merchant-portal.env.example`                                   | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/mobile-driver.env.example`                                     | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/production.env.example`                                        | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/website.env.example`                                           | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `env/worker.env.example`                                            | config/CI           | KEEP; split into droplet/ubuntu/oracle env files, values from SOPS (doc 37); week 1–2                   |
| `infrastructure/deploy/SECRETS.md`                                  | config/CI           | REPLACE content with SOPS (doc 37); week 1                                                              |
| `infrastructure/deploy/deploy-rules.json`                           | config/CI           | KEEP; add droplet/ubuntu/oracle targets (doc 32); week 2                                                |
| `infrastructure/deploy/docker-compose.backup.example.yml`           | config/CI           | REPLACE by pgBackRest (doc 35); week 2                                                                  |
| `infrastructure/deploy/systemd/porterchain-health-watch.service`    | config/CI           | KEEP; health-watch → Prometheus/Alertmanager (doc 36) week 3; backup timer → pgBackRest (doc 35) week 2 |
| `infrastructure/deploy/systemd/porterchain-health-watch.timer`      | config/CI           | KEEP; health-watch → Prometheus/Alertmanager (doc 36) week 3; backup timer → pgBackRest (doc 35) week 2 |
| `infrastructure/deploy/systemd/porterchain-postgres-backup.service` | config/CI           | KEEP; health-watch → Prometheus/Alertmanager (doc 36) week 3; backup timer → pgBackRest (doc 35) week 2 |
| `infrastructure/deploy/systemd/porterchain-postgres-backup.timer`   | config/CI           | KEEP; health-watch → Prometheus/Alertmanager (doc 36) week 3; backup timer → pgBackRest (doc 35) week 2 |
| `infrastructure/docker/docker-compose.yml`                          | config/CI           | KEEP for local rehearsal; per-host compose in doc 28; week 2                                            |
| `.github/workflows/set-public-ingest-key.yml`                       | config/CI           | KEEP; secret source moves to SOPS (doc 37); week 1                                                      |
| `website/Dockerfile`                                                | config/CI           | KEEP; droplet lane; week 2                                                                              |
| `apps/api/Dockerfile`                                               | config/CI           | KEEP; multi-arch build for Oracle ARM (doc 32); week 2                                                  |
| `website/Dockerfile`                                                | config/CI           | KEEP; droplet lane; week 2                                                                              |
| `base_adapter`                                                      | integration         | KEEP; week 7                                                                                            |
| `doppler_secrets`                                                   | integration         | REPLACE by SOPS loader (doc 37); week 2                                                                 |
| `netsuite_adapter`                                                  | integration         | DEFER: Phase 2 (no Phase 1 merchant uses NetSuite)                                                      |
| `zapier_catalog`                                                    | integration         | DEFER: Phase 2 (Zapier is paid for multi-step zaps; webhooks remain)                                    |
| `apps/api/tests/admin_p0 (2 files)`                                 | test suite          | KEEP; PR gate (pytest) or nightly lane (Playwright e2e), doc 32; week 1                                 |
| `apps/api/tests/merchant_p0 (6 files)`                              | test suite          | KEEP; PR gate (pytest) or nightly lane (Playwright e2e), doc 32; week 1                                 |
| `website/e2e (4 files)`                                             | test suite          | KEEP; PR gate (pytest) or nightly lane (Playwright e2e), doc 32; week 1                                 |
| `apps/admin/e2e (7 files)`                                          | test suite          | KEEP; PR gate (pytest) or nightly lane (Playwright e2e), doc 32; week 1                                 |
| `apps/driver-portal/e2e (3 files)`                                  | test suite          | KEEP; PR gate (pytest) or nightly lane (Playwright e2e), doc 32; week 1                                 |
| `apps/merchant-portal/e2e (5 files)`                                | test suite          | KEEP; PR gate (pytest) or nightly lane (Playwright e2e), doc 32; week 1                                 |
| `admin:/blog/new`                                                   | portal page         | KEEP; Ubuntu; week 2                                                                                    |
| `admin:/`                                                           | portal page         | KEEP → Today screen (doc 16); Ubuntu; week 2                                                            |
| `customer:/`                                                        | portal page         | KEEP; droplet; week 2                                                                                   |
| `driver-portal:/`                                                   | portal page         | KEEP; droplet; week 2                                                                                   |
| `merchant-portal:/api`                                              | portal page         | KEEP; API keys + limits (doc 38); droplet; week 6                                                       |
| `merchant-portal:/`                                                 | portal page         | KEEP; droplet; week 2                                                                                   |
| `website:/[locale]/[...rest]`                                       | portal page         | KEEP (catch-all 404/redirects); droplet; week 2                                                         |
| `website:/[locale]/[city]/[industrySlug]`                           | portal page         | KEEP (programmatic SEO); droplet; week 2                                                                |
| `website:/[locale]/faq`                                             | portal page         | KEEP; update prices from rate card v2; week 2                                                           |
| `website:/[locale]`                                                 | portal page         | KEEP (home); droplet; week 2                                                                            |
| `web-push`                                                          | app/service/package | KEEP: web push for portals (red-margin alert to admins, doc 36); week 3                                 |

**L30-6 (29 Oct 2026):** Zapier and NetSuite decided Phase 2.
