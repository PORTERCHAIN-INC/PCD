# PorterChain documentation

**Type:** CANONICAL  
**Last verified:** 2026-08-07

When docs disagree with code, trust live `package.json` / `requirements.txt` / compose / `.nvmrc`.

---

## Start here

| Document                                                                       | Role                      |
| ------------------------------------------------------------------------------ | ------------------------- |
| [../README.md](../README.md)                                                   | Clone → run               |
| [PORTERCHAIN_CHARTER.md](PORTERCHAIN_CHARTER.md)                               | Company identity          |
| [PRIORITY_TODOS.md](PRIORITY_TODOS.md)                                         | Execution backlog (P0–P3) |
| [../masterrule.md](../masterrule.md)                                           | Architecture rules        |
| [../TECH_STACK.md](../TECH_STACK.md)                                           | Versions                  |
| [ONBOARDING_ENGINEER.md](ONBOARDING_ENGINEER.md)                               | Engineer onboarding       |
| [SILICON_VALLEY_READINESS_CHECKLIST.md](SILICON_VALLEY_READINESS_CHECKLIST.md) | Release gates             |

---

## Architecture & auth

| Document                                                                        | Role                            |
| ------------------------------------------------------------------------------- | ------------------------------- |
| [architecture/SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md)      | Platform topology               |
| [architecture/README.md](architecture/README.md)                                | Flow diagrams                   |
| [architecture/auth-clerk-spicedb.md](architecture/auth-clerk-spicedb.md)        | Authorization (SpiceDB)         |
| [../AUTHENTICATION_ARCHITECTURE.md](../AUTHENTICATION_ARCHITECTURE.md)          | Identity by portal              |
| [../SSO.md](../SSO.md)                                                          | Admin staff IdP + Fleetbase SSO |
| [../DOMAIN_MODEL.md](../DOMAIN_MODEL.md)                                        | Aggregates                      |
| [../EVENT_BUS.md](../EVENT_BUS.md) · [../EVENT_CATALOG.md](../EVENT_CATALOG.md) | Events                          |
| [../ORDER_LIFECYCLE.md](../ORDER_LIFECYCLE.md)                                  | Order states                    |
| [../FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md)                              | Use / Extend / Replace          |
| [../FLEETBASE_INTEGRATION.md](../FLEETBASE_INTEGRATION.md)                      | Fleetbase bridge                |
| [../INTEGRATIONS.md](../INTEGRATIONS.md)                                        | External systems                |
| [../PRICING_ENGINE.md](../PRICING_ENGINE.md)                                    | Pricing                         |

---

## Operations

| Document                                                                 | Role                                                                 |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| [ops/ORDERS_MODULE.md](ops/ORDERS_MODULE.md)                             | Control Tower & Order 360                                            |
| [ops/ADMIN_PARTNERS_UPGRADE_PLAN.md](ops/ADMIN_PARTNERS_UPGRADE_PLAN.md) | Partners deep audit + upgrade plan (Merchants · Drivers · Customers) |
| [ops/ORDER_360_AUDIT_SCORECARD.md](ops/ORDER_360_AUDIT_SCORECARD.md)     | Release audit form                                                   |
| [ops/VALIDATE_MONTHLY_PROD.md](ops/VALIDATE_MONTHLY_PROD.md)             | Monthly prod validation                                              |
| [../RUNBOOK.md](../RUNBOOK.md)                                           | Ops runbook                                                          |
| [../ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md)               | Env catalog                                                          |
| [SECRETS_MAP.md](SECRETS_MAP.md)                                         | Secrets map                                                          |
| [../infrastructure/deploy/README.md](../infrastructure/deploy/README.md) | Deploy                                                               |

---

## Data · maps · notifications

| Document                                                                                 | Role                |
| ---------------------------------------------------------------------------------------- | ------------------- |
| [../DATABASE_ARCHITECTURE.md](../DATABASE_ARCHITECTURE.md)                               | Postgres + Alembic  |
| [../GOOGLE_MAPS_USAGE.md](../GOOGLE_MAPS_USAGE.md)                                       | Places / tiles only |
| [../OSRM_USAGE.md](../OSRM_USAGE.md) · [../VALHALLA_USAGE.md](../VALHALLA_USAGE.md)      | Routing             |
| [notifications/NOTIFICATION_ARCHITECTURE.md](notifications/NOTIFICATION_ARCHITECTURE.md) | Notifications       |
| [notifications/FCM_CONFIGURATION.md](notifications/FCM_CONFIGURATION.md)                 | FCM                 |
| [notifications/ZOHO_MAIL.md](notifications/ZOHO_MAIL.md)                                 | Email               |

---

## Product surfaces

| Document                                               | Role            |
| ------------------------------------------------------ | --------------- |
| [../DRIVER_PLATFORM.md](../DRIVER_PLATFORM.md)         | Driver platform |
| [../MOBILE_ARCHITECTURE.md](../MOBILE_ARCHITECTURE.md) | Mobile          |
| [../apps/admin/README.md](../apps/admin/README.md)     | Admin           |
| [../apps/api/README.md](../apps/api/README.md)         | API             |
| [../website/README.md](../website/README.md)           | Website         |

---

## Website / GTM

| Document                                                       | Role                   |
| -------------------------------------------------------------- | ---------------------- |
| [WEBSITE_GTM_EXECUTION_PLAN.md](WEBSITE_GTM_EXECUTION_PLAN.md) | GTM                    |
| [WEBSITE_SEO_STRATEGY.md](WEBSITE_SEO_STRATEGY.md)             | SEO                    |
| [ICP.md](ICP.md)                                               | ICP                    |
| [DESIGN_COPY_BAN_LIST.md](DESIGN_COPY_BAN_LIST.md)             | Copy rules             |
| [website/](website/)                                           | SEO/content appendices |

---

## Compliance · investor · legal

| Area         | Path                       |
| ------------ | -------------------------- |
| Compliance   | [compliance/](compliance/) |
| Investor     | [investor/](investor/)     |
| Legal        | [legal/](legal/)           |
| API partners | [api/](api/)               |

---

## Archive

**Do not edit** historical material:

- [archive/README.md](archive/README.md)
- [archive/reports-2026-08/](archive/reports-2026-08/) — readiness / scorecards / E2E dumps
- [archive/redundant-2026-08/](archive/redundant-2026-08/) — overlapping or superseded living docs
- [POINTER_STUB_INDEX.md](POINTER_STUB_INDEX.md) — ≤5 root pointers

**Policy:** one canonical doc per topic. No new root `*_AUDIT.md` / `*_REPORT.md`.
