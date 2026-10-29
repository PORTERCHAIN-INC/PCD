# PorterChain PCD — Architecture drawing set (index, legend, evidence method)

Generated 2026-10-28 (America/Toronto) from repo `/home/pcd/PCD` at HEAD `56865de9` + working tree. Docs only; no application code changed.

## Files

| #   | AS-BUILT (NOW)                                                     | #   | PLANNED (Phase 1)                                               |
| --- | ------------------------------------------------------------------ | --- | --------------------------------------------------------------- |
| 01  | [System context](01_system_context.md)                             | 12  | [Context + containers](12_planned_context_containers.md)        |
| 02  | [Containers + deployment](02_containers_deployment.md)             | 13  | [DFDs](13_planned_dfd.md)                                       |
| 03  | [DFD L0/L1/L2](03_dfd.md)                                          | 14  | [ER additions](14_planned_er.md)                                |
| 04  | [ER + schema listing](04_er_schema.md) (generated)                 | 15  | [Modules, API, events](15_planned_modules_api_events.md)        |
| 05  | [Backend modules, workers, queues](05_backend_modules.md)          | 16  | [Admin + super-admin IA](16_planned_admin_ia.md)                |
| 06  | [API inventory](06_api_inventory.md) (generated)                   | 17  | [State machines + authz](17_planned_states_authz.md)            |
| 07  | [Interface layer: every screen](07_interface_layer.md) (generated) | 18  | [Agents + autonomy ladder](18_planned_agents.md)                |
| 08  | [State machines](08_state_machines.md)                             | 19  | [Compliance layer + checklist](19_compliance_layer.md)          |
| 09  | [Authz (Clerk + staff IdP + SpiceDB)](09_authz.md)                 | 20  | [Operational legal rulebook](20_operational_legal_rulebook.md)  |
| 10  | [Events + async](10_events_async.md)                               | 21  | [NOW vs PLANNED delta + migration order](21_delta_migration.md) |
| 11  | [AUDIT](11_audit.md)                                               | 28  | [Hybrid deployment (L28)](28_hybrid_deployment.md)              |
|     |                                                                    | 98  | [Unknowns](98_unknowns.md)                                      |

Older `mermaid/*.mmd` (2026-10-27) are kept untouched; this set supersedes them where they conflict.

## Legend

- Solid arrow = verified call/data flow (cited). Dashed arrow = async (Redis Stream / list queue / sweep).
- `[[x]]` = external system. Cylinder = datastore. Tag **(P)** = planned, not in code.
- Status words: **built** (code + data path cited), **partial** (some code, gap named), **missing** (0 refs found).

## Evidence method

1. Code: `rg`/AST scans of `apps/api/src/porterchain_api/**`, `apps/worker`, `services/event-bus`, `shared/python`, `apps/*/src/app/**`. Citations are `path:line` relative to repo root (API paths often shortened to `porterchain_api/...`).
2. Schema: read-only `psql` against the **local stack** Postgres `pcd-local-pg` (port 55632) with `SET default_transaction_read_only=on`; cross-checked against ORM `__tablename__` (129 model tables vs 131 DB tables incl. `alembic_version`). Live 5432/6379/50051 were never touched.
3. API: committed `docs/api/openapi.json` (commit `2a360bac`, 09:18 EDT) joined to handlers; drift listed in 06.
4. Law: each rule links to an official page. Pages fetched this run are marked ✔; others are marked "link not re-opened this run".
5. Anything not proven goes to [98_unknowns.md](98_unknowns.md), not into a diagram.

Rendering: `mmdc` (mermaid-cli) install was refused by the shell safety classifier (error, not a policy decision), so no SVG/PNG; Mermaid renders in GitHub/Cursor preview.

## Added Oct 28, 2026

- `22_planned_state_machines.md` — planned order, job offer, invoice, credit note, driver, quote, box truck (BOL/CVOR gate), cooler run (temp log), autonomy ladder, agent run.
- `23_planned_events.md` — outbox → DBOS relay → Redpanda, 12 `pc.*.v1` topics with producers/consumers, sweeps migration, live GPS on Redis.
- `mermaid/CLEANUP_NOTES.md` — FleetBase-era undefined nodes defined or removed.

## Added Oct 28, 2026 (apps)

- `24_shopify_app.md` — Shopify app now vs planned (API 2026-10, Polaris web components, Functions, Flow, checkout extension, outbox ingest, BFS).
- `25_customer_mobile.md` — customer Expo app now vs planned (push, Live Activities/Live Updates, Wallet, WhatsApp, passkeys, ETA).
- `26_driver_mobile.md` — driver Expo app now vs planned (tamper-evident POD, vision POD check, voice copilot, re-routing, BLE cooler log, DPWRA pay).

## Added Oct 28, 2026 (deployment)

- `28_hybrid_deployment.md` — L28 droplet + Ubuntu + Oracle Always Free: placement, WireGuard mesh, data ownership, load balancing/failover, Ubuntu-off and Oracle-off tables, sizing/cost, PIPEDA, failover drill.

## Operations and coverage docs (29–39, 46–55)

- `29_coverage_matrix.md`: every repo item with its as-built ref, plan ref and status
- `30_operational_readiness.md`: the operational areas O1–O22, with the doc for each
- `31_sweep_processor_mapping.md`: 22 sweeps + 5 processors → DBOS / Kafka
- `32_script_triage_ci_lanes.md`: 229 scripts triaged; CI lanes for droplet, Ubuntu, Oracle, EAS, Shopify
- `33_item_decisions.md`: tables, routers, pages
- `34_data_migration_cutover.md`: Clerk → Keycloak, passkey re-enrolment, dual-run, rollback
- `35_backups_dr.md`: RPO/RTO, 3-2-1, USB monthly
- `36_monitoring_alerts.md`
- `37_secrets.md`: SOPS replaces Doppler
- `38_security.md`
- `39_incident_response.md`: PIPEDA breach steps
- `48_merchant_onboarding_offboarding.md`
- `49_legal_documents.md`: for lawyer review
- `50_mobile_release_store.md`
- `51_shopify_review.md`
- `52_runbooks.md`
- `53_accessibility_french.md`
- `54_support_sops_training.md`
- `55_remaining_item_decisions.md`

(40–45 are the UI/UX and backend docs from other commits.)

- 56 · L30 Ravi decisions of 29 Oct 2026 (Checkr, SOPS, Shopify unlisted, pen test, French, on-call, box truck short-term rental, GPU 6 GB re-check, 10+ drivers, Oracle)

## Phase 0 (added 29 Oct 2026, L31)

Ravi defined Phase 0 before Phase 1: no agentic mode; every replacement, routing + operations redesign, database organisation, store releases, dead-code removal, S1 fixes and hybrid deployment. 12 weeks, gated by G1–G21 plus G-INS for paid deliveries (doc 60 §2).

| #   | NOW vs PHASE 0                                                                                                                                                            |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 60  | [Phase 0 plan](60_phase0_plan.md): goals, gates, schedule, workstreams, cleanup inventory, migration order, DB plan, routing/ops pages, store checklist, risks, decisions |
| 61  | [Context + containers](61_p0_context_containers.md)                                                                                                                       |
| 62  | [Deployment + network](62_p0_deployment.md)                                                                                                                               |
| 63  | [ER core entities](63_p0_er.md)                                                                                                                                           |
| 64  | [DFD L1/L2](64_p0_dfd.md)                                                                                                                                                 |
| 65  | [Sequences](65_p0_sequences.md)                                                                                                                                           |
| 66  | [State machines](66_p0_state_machines.md)                                                                                                                                 |
| 67  | [Apps: mobile, Shopify, portals](67_p0_apps.md)                                                                                                                           |

All 28 Mermaid blocks in 61–67 were rendered to SVG with mermaid-cli 11.17.1 (on the agent box, not this machine) and saved in `rendered_p0/` (`<doc>_<block>.svg`). The `29` matrix now has a **Phase** column (P0/P1/P2).

## L35 Business-ready Phase 0 (29 Oct 2026)

| #   | Doc                                                                                                        |
| --- | ---------------------------------------------------------------------------------------------------------- |
| 68  | [Trust & Help Centre](68_trust_help_centre.md)                                                             |
| 70  | [Business model: Organisation + operating profile](70_business_model_architecture.md)                      |
| 71  | [Progressive onboarding](71_progressive_onboarding.md)                                                     |
| 72  | [Pricing, simplified](72_pricing_simplified.md)                                                            |
| 73  | [Support and issue playbook](73_support_and_issue_playbook.md)                                             |
| 74  | [Integrations per business type (+ Shopify and mobile review fixes)](74_integrations_per_business_type.md) |
| 75  | [Ops console reorganisation](75_ops_console_reorganisation.md)                                             |
| 76  | [Acceptance tests before build (G19–G21)](76_acceptance_tests_before_build.md)                             |

- 77 · [Phase 0 traceability of Ravi's asks + consistency passes](77_phase0_traceability.md)
- 78 · [Leads / CRM module](78_leads_crm_module.md)
- `79_business_metrics_engine.md`: our main business formulas (EBITDA, ROI/ROIC/WACC/EVA, CCC, Little/Kingman/SS/EOQ, unit economics), $77k baseline, Insights, A-FIN tests

Mermaid blocks in 70, 71, 73, 75 rendered to SVG (mermaid-cli, agent box) in `rendered_l35/`, 0 syntax errors.
