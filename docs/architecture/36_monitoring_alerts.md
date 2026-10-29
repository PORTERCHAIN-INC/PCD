# 36 · Monitoring and alerts (all free, self-hosted)

| Piece                                                                   | Where                                                                       | Purpose                                                                                  |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Prometheus                                                              | Ubuntu (main) + small Prometheus agent on droplet and Oracle (remote-write) | metrics: API latency/errors, DB, Redpanda lag, DBOS queue depth, GPU queue, margin bands |
| Grafana OSS                                                             | Ubuntu, read replica dashboard on Oracle                                    | dashboards: Today, money, events, agents, hosts                                          |
| Loki + Promtail/Alloy                                                   | Ubuntu (store), agents on all hosts                                         | logs, 30-day retention                                                                   |
| Alertmanager                                                            | **Oracle** (so it alerts when Ubuntu is off)                                | routing                                                                                  |
| GlitchTip                                                               | droplet (small)                                                             | app/mobile errors (replaces Sentry, week 3)                                              |
| Uptime Kuma                                                             | Oracle                                                                      | external HTTP checks of all public URLs and status page                                  |
| node_exporter, postgres_exporter, cAdvisor, Redpanda metrics, DBOS OTel | all hosts                                                                   | sources                                                                                  |

## Alert routing to Ravi (free)

- **Red margin (≤ 35%):** in-app alert on the admin Today screen plus push to all admins (web-push + ntfy), as Ravi decided.
- **Sev1** (site down, payments failing, DB replica lag > 5 min, cooler excursion, red margin over $500/day): ntfy push (self-hosted on Oracle, free iOS/Android app) plus email via ZeptoMail (allowed). The ntfy message repeats every 10 min until it's acknowledged.
- **Sev2** (Kafka lag > 5 min, sweep parity mismatch, GPU queue > 2 min, disk > 80%, backup failed): ntfy push.
- **Sev3:** a daily email digest at 08:00 Toronto.
- Telegram bot (free) is an optional second push channel. No SMS (Twilio removed, L26).

Rollout: week 3 (stack, host and API alerts), week 6 (business alerts), week 13 (Kafka lag + DR alerts). Done check: a seeded outage reaches Ravi's phone within 2 minutes.

**L30-9:** single on-call (Ravi). Quiet hours 22:00–07:00, Sev1 only pages; agent first-response; safe mode after 30 min un-acked Sev1. See doc 56.
