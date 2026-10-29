# 39 · Incident response (with PIPEDA breach steps)

| Sev | Example                                                             | Response                               | Who                                    |
| --- | ------------------------------------------------------------------- | -------------------------------------- | -------------------------------------- |
| 1   | site/payments down, data breach, cooler excursion with medical load | ack in 15 min, fix or fail over in 1 h | Ravi (backup: named staff member, TBD) |
| 2   | one portal degraded, Kafka lag, failed backup                       | ack in 1 h, fix same day               | Ravi                                   |
| 3   | cosmetic bug                                                        | next release                           | —                                      |

**Flow:** detect (alert, doc 36) → declare a Sev in a `#incident` log (admin incident page) → contain → fix → status page update (Uptime Kuma on Oracle) → merchant email if their orders are affected → post-mortem within 5 business days (template: timeline, cause, fix, prevention).

## PIPEDA breach of security safeguards

1. Contain, and preserve logs (forensic chain).
2. Assess **real risk of significant harm (RROSH)**: how sensitive the data is, plus the probability of misuse.
3. If RROSH: report to the Office of the Privacy Commissioner of Canada "as soon as feasible" (OPC breach form), notify the affected people directly, and notify organizations that can reduce harm (e.g. banks, Stripe).
4. Record **every** breach, even below RROSH, in the breach log and keep it **24 months** (Breach of Security Safeguards Regulations).
5. If merchants' customer data is involved, notify the merchant under the DPA (`docs/legal/merchant-dpa.md`) within the agreed hours.

Week 6 (plan + tabletop drill), week 13 (second drill during the DR test). Lawyer review of the notice templates is in the week 6 legal batch.
