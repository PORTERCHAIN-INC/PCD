# Porterchain documentation

**Type:** CANONICAL
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Master index for the PCD monorepo. Root-level reports remain searchable; **canonical** deep docs are linked below.

---

## Documentation simplification program

Per **[masterrule §21](../masterrule.md#21-simplification--essential-complexity)** (essential vs accidental complexity):

| Item   | Detail                                                                                              |
| ------ | --------------------------------------------------------------------------------------------------- |
| Scope  | 191 platform markdown files                                                                         |
| Groups | 39 × 5 — tracker in [Appendix C](../masterrule.md#appendix-c--documentation-simplification-program) |
| Audit  | [CTO_AUDIT_REPORT.md](../CTO_AUDIT_REPORT.md)                                                       |
| Rule   | One canonical doc per topic; trim pointers; no new root audit files                                 |

---

## Entry & governance

| Document                                              | Description                                     |
| ----------------------------------------------------- | ----------------------------------------------- |
| [README.md](../README.md)                             | Quick start, ports, dev commands                |
| [masterrule.md](../masterrule.md)                     | **Single source of truth** — architecture rules |
| [REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md) | Monorepo layout and boundaries                  |
| [CONTRIBUTING_GUIDE.md](../CONTRIBUTING_GUIDE.md)     | Contribution rules                              |
| [TECH_STACK.md](../TECH_STACK.md)                     | Technology versions                             |
| [FOLDER_STRUCTURE.md](../FOLDER_STRUCTURE.md)         | Pointer → repository structure                  |

---

## Production status

| Document                                                                       | Description                                            |
| ------------------------------------------------------------------------------ | ------------------------------------------------------ |
| [CTO_AUDIT_REPORT.md](../CTO_AUDIT_REPORT.md)                                  | **Doc vs code audit** (12 bunches, 2026-07-05)         |
| [SILICON_VALLEY_READINESS_CHECKLIST.md](SILICON_VALLEY_READINESS_CHECKLIST.md) | **10/10 scorecard gates** — Fowler evolution checklist |
| [PRIORITY_TODOS.md](PRIORITY_TODOS.md)                                         | **Prioritized execution todos** (P0–P3)                |
| [PRODUCTION_READINESS_REPORT.md](../PRODUCTION_READINESS_REPORT.md)            | **Go/no-go** certification                             |
| [GAP_ANALYSIS.md](../GAP_ANALYSIS.md)                                          | Open platform gaps                                     |
| [ROADMAP.md](../ROADMAP.md)                                                    | Remediation timeline                                   |
| [MODULE_SCORECARD.md](../MODULE_SCORECARD.md)                                  | Per-module readiness                                   |

---

## Architecture

| Document                                                                        | Description                                         |
| ------------------------------------------------------------------------------- | --------------------------------------------------- |
| [docs/architecture/SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) | **Canonical** platform topology                     |
| [SYSTEM_ARCHITECTURE.md](../SYSTEM_ARCHITECTURE.md)                             | Pointer → architecture doc above                    |
| [DOMAIN_MODEL.md](../DOMAIN_MODEL.md)                                           | Domain aggregates, lifecycles, events               |
| [ENTITY_RELATIONSHIP_MODEL.md](../ENTITY_RELATIONSHIP_MODEL.md)                 | ER diagrams                                         |
| [BUSINESS_GLOSSARY.md](../BUSINESS_GLOSSARY.md)                                 | Business terminology                                |
| [architecture/README.md](architecture/README.md)                                | Flow diagrams index (booking, dispatch, payment, …) |
| [FLEETBASE_ADAPTER_ARCHITECTURE.md](../FLEETBASE_ADAPTER_ARCHITECTURE.md)       | Fleetbase adapter design                            |
| [INTEGRATIONS.md](../INTEGRATIONS.md)                                           | External systems matrix                             |

---

## Authentication & access

| Document                                                                   | Description                |
| -------------------------------------------------------------------------- | -------------------------- |
| [AUTHENTICATION_ARCHITECTURE.md](../AUTHENTICATION_ARCHITECTURE.md)        | **Canonical** auth design  |
| [architecture/AUTHENTICATION_FLOW.md](architecture/AUTHENTICATION_FLOW.md) | Clerk + Fleetbase SSO flow |
| [RBAC_MATRIX.md](../RBAC_MATRIX.md)                                        | Permission matrix          |
| [RBAC.md](../RBAC.md)                                                      | Pointer → RBAC cluster     |
| [SSO.md](../SSO.md)                                                        | Single sign-on             |
| [SECURITY.md](../SECURITY.md)                                              | Security policy            |

---

## Events & order lifecycle

| Document                                                           | Description                          |
| ------------------------------------------------------------------ | ------------------------------------ |
| [EVENT_BUS.md](../EVENT_BUS.md)                                    | **Canonical** event bus architecture |
| [EVENT_CATALOG.md](../EVENT_CATALOG.md)                            | **Canonical** domain event catalog   |
| [architecture/EVENT_BUS_FLOW.md](architecture/EVENT_BUS_FLOW.md)   | Event bus flow diagram               |
| [ORDER_LIFECYCLE.md](../ORDER_LIFECYCLE.md)                        | Order states (root)                  |
| [architecture/ORDER_LIFECYCLE.md](architecture/ORDER_LIFECYCLE.md) | Order lifecycle diagram              |
| [EVENT_FLOW.md](../EVENT_FLOW.md)                                  | Pointer → EVENT_BUS + EVENT_CATALOG  |

---

## Database

| Document                                                                       | Description                             |
| ------------------------------------------------------------------------------ | --------------------------------------- |
| [DATABASE_ARCHITECTURE.md](../DATABASE_ARCHITECTURE.md)                        | **Canonical** — PostgreSQL 16 + Alembic |
| [DATABASE_OWNERSHIP_MATRIX.md](../DATABASE_OWNERSHIP_MATRIX.md)                | Table ownership                         |
| [ALEMBIC_VALIDATION.md](../ALEMBIC_VALIDATION.md)                              | Migration chain (13 revisions)          |
| [architecture/DATABASE_RELATIONSHIP.md](architecture/DATABASE_RELATIONSHIP.md) | ER flow diagram                         |
| [archive/README.md#database](archive/README.md#database)                       | Historical database audits              |

---

## Maps & routing

| Document                                                             | Description                   |
| -------------------------------------------------------------------- | ----------------------------- |
| [GOOGLE_MAPS_USAGE.md](../GOOGLE_MAPS_USAGE.md)                      | Google Maps policy (viz only) |
| [OSRM_USAGE.md](../OSRM_USAGE.md)                                    | OSRM distance/ETA             |
| [VALHALLA_USAGE.md](../VALHALLA_USAGE.md)                            | Valhalla optimization         |
| [ROUTE_CENTER_ARCHITECTURE.md](../ROUTE_CENTER_ARCHITECTURE.md)      | Admin Route Center            |
| [architecture/GOOGLE_MAPS_FLOW.md](architecture/GOOGLE_MAPS_FLOW.md) | Maps flow diagram             |

---

## Fleetbase

| Document                                                                 | Description                         |
| ------------------------------------------------------------------------ | ----------------------------------- |
| [FLEETBASE_INTEGRATION.md](../FLEETBASE_INTEGRATION.md)                  | Integration overview                |
| [FLEETBASE_INSTALL.md](../FLEETBASE_INSTALL.md)                          | Docker install                      |
| [FLEETBASE_SERVICE_STATUS.md](../FLEETBASE_SERVICE_STATUS.md)            | Verification snapshot               |
| [SERVICE_STATUS.md](../SERVICE_STATUS.md)                                | Pointer → service status            |
| [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md)                          | Module breakdown                    |
| [EXTENSION_GUIDE.md](../EXTENSION_GUIDE.md)                              | Extend the adapter                  |
| [UPGRADE_GUIDE.md](../UPGRADE_GUIDE.md)                                  | Version upgrades                    |
| [archive/README.md#fleetbase-detail](archive/README.md#fleetbase-detail) | Historical Fleetbase detail reports |

---

## Operations

| Document                                                | Description                |
| ------------------------------------------------------- | -------------------------- |
| [RUNBOOK.md](../RUNBOOK.md)                             | Operations runbook         |
| [DOCKER_SETUP.md](../DOCKER_SETUP.md)                   | Docker compose             |
| [env/README.md](../env/README.md)                       | Environment templates      |
| [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md) | Full env catalog           |
| [PORT_CONFIGURATION.md](../PORT_CONFIGURATION.md)       | Local and production ports |

---

## E2E validation reports (regenerable)

Generated by `pnpm validate:e2e:reports`:

| Report                                                        | Phase                     |
| ------------------------------------------------------------- | ------------------------- |
| [FORWARD_LOGISTICS_REPORT.md](../FORWARD_LOGISTICS_REPORT.md) | Forward chain             |
| [REVERSE_LOGISTICS_REPORT.md](../REVERSE_LOGISTICS_REPORT.md) | Returns                   |
| [DATA_CONSISTENCY_REPORT.md](../DATA_CONSISTENCY_REPORT.md)   | Cross-surface consistency |
| [FAILURE_SCENARIOS_REPORT.md](../FAILURE_SCENARIOS_REPORT.md) | Failure matrix            |
| [NOTIFICATION_REPORT.md](../NOTIFICATION_REPORT.md)           | Notification templates    |

---

## Notifications & realtime

| Document                                                                                 | Description                |
| ---------------------------------------------------------------------------------------- | -------------------------- |
| [notifications/NOTIFICATION_ARCHITECTURE.md](notifications/NOTIFICATION_ARCHITECTURE.md) | Notification engine design |
| [notifications/FCM_CONFIGURATION.md](notifications/FCM_CONFIGURATION.md)                 | Firebase push setup        |
| [architecture/NOTIFICATION_FLOW.md](architecture/NOTIFICATION_FLOW.md)                   | Delivery flow diagram      |
| [REALTIME_COMMUNICATION_REPORT.md](../REALTIME_COMMUNICATION_REPORT.md)                  | WS + polling audit         |
| [architecture/REALTIME_FLOW.md](architecture/REALTIME_FLOW.md)                           | Live map WebSocket flow    |

---

## Module surfaces (canonical)

| Module       | Architecture                                                          | Readiness                                                               |
| ------------ | --------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Merchant     | [MERCHANT_ARCHITECTURE_REPORT.md](../MERCHANT_ARCHITECTURE_REPORT.md) | [MERCHANT_PRODUCTION_READINESS.md](../MERCHANT_PRODUCTION_READINESS.md) |
| Driver       | [DRIVER_PLATFORM.md](../DRIVER_PLATFORM.md)                           | [DRIVER_PRODUCTION_READINESS.md](../DRIVER_PRODUCTION_READINESS.md)     |
| Mobile       | [MOBILE_ARCHITECTURE_REPORT.md](../MOBILE_ARCHITECTURE_REPORT.md)     | [MOBILE_PRODUCTION_READINESS.md](../MOBILE_PRODUCTION_READINESS.md)     |
| Route Center | [ROUTE_CENTER_ARCHITECTURE.md](../ROUTE_CENTER_ARCHITECTURE.md)       | —                                                                       |

Superseded audit/security/performance reports for these modules are **pointer stubs** at repo root; frozen copies live under [archive/](archive/README.md).

---

## Documentation archive

Historical audit snapshots and merged duplicates: **[archive/README.md](archive/README.md)** (55 files, July 2026 consolidation).

Phase 2 merged database reports, API snapshots, platform audits, and Fleetbase detail reports into the canonical docs above.
---

## Governance

| Document                                      | Role              |
| --------------------------------------------- | ----------------- |
| [masterrule.md](../masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../CTO_AUDIT_REPORT.md) | Doc vs code audit |
