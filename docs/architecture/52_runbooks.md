# 52 · Runbooks to add (extends RUNBOOK.md)

Each entry has symptoms → checks → fix → rollback. It has to exist before that component goes live (week shown).

| Runbook                      | Covers                                                                                                                    | Week |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---- |
| Ubuntu planned/unplanned off | what keeps running on droplet/Oracle, admin read-only fallback, catch-up when back (DBOS resumes, Kafka consumers replay) | 6    |
| Droplet down                 | promote Oracle Postgres replica, switch DNS, start the standby API                                                        | 13   |
| Redpanda                     | broker down, disk full, consumer lag, topic re-create from outbox                                                         | 4    |
| DBOS                         | stuck workflow, replay, queue backlog, version mismatch                                                                   | 5    |
| Keycloak                     | login outage, key rotation, realm export/restore, locked-out super-admin (break-glass account in SOPS)                    | 5    |
| llama.cpp / GPU              | model server down, VRAM full, fall back to rules-only (T0) mode                                                           | 1    |
| OSRM / Valhalla              | rebuild Ontario extract, memory limits, fallback to haversine labelled estimate                                           | 4    |
| Backups                      | failed backup, restore steps (doc 35)                                                                                     | 2    |
| Payments                     | Interac match failures, Stripe webhook backlog                                                                            | 5    |
| Cooler excursion             | temperature alarm → hold load → notify → claim                                                                            | 5    |
| Load balancing               | Caddy/Cloudflare health-check failover between droplet and Oracle for public portals (doc 28)                             | 6    |

**L30-9:** every runbook gets an "agent can do / Ravi must do" split and a phone-sized version (doc 56).
