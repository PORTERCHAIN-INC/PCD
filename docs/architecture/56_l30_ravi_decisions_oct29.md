# 56 · L30: Ravi decisions of 29 Oct 2026 (defaults approved + pilot facts)

Status: DECIDED (Ravi, 29 Oct 2026, America/Toronto). Docs only; no code changed. Statements marked **verify** are not yet checked against an official source or the lease/insurance papers.

## L30 decision table

| ID     | Topic                    | Decision                                                                                                                                                                                                          | Docs touched   |
| ------ | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| L30-1  | Background checks        | Manual police check (CPIC / vulnerable-sector not required) + driver's abstract obtained by the driver; Checkr is used **only if the insurer requires it**, and then it is a paid _mandatory_ exception under L26 | 20, 48, 54, 98 |
| L30-2  | Secrets                  | Doppler retired; SOPS + age in weeks 1–2 (doc 37 plan unchanged)                                                                                                                                                  | 37             |
| L30-3  | Shopify                  | **Unlisted custom app** for the pilot (no App Store review, no Shopify Billing needed; merchants pay by Interac per L10); public listing later (doc 51 checklist kept for that). Closes S11                       | 24, 51         |
| L30-4  | Pen test                 | No paid pen test. OWASP ZAP (baseline + authenticated full scan in CI on test stack 55432), Trivy (images, deps, IaC, secrets), ASVS L1 self-check before pilot                                                   | 38             |
| L30-5  | French                   | Phase 1: everything customer-facing — website, customer/merchant/driver portals, customer + driver apps, Shopify app, emails/push/PDFs, legal documents. Admin console: Phase 2                                   | 53, 41, 49     |
| L30-6  | Zapier, NetSuite         | Phase 2 (adapters stay dormant, no new work)                                                                                                                                                                      | 55             |
| L30-7  | Meta Cloud API free tier | Not now. WhatsApp = Business app + wa.me + agent drafts, human sends (L27)                                                                                                                                        | 27             |
| L30-8  | Pilot merchant           | Exists; **name TBD from Ravi**                                                                                                                                                                                    | strict plan §9 |
| L30-9  | On-call                  | Ravi alone (see "Single on-call design")                                                                                                                                                                          | 36, 39, 52     |
| L30-10 | Box truck                | **Leased** (see "Leased truck") ; ELD legal check still open                                                                                                                                                      | 20, 28, 98     |
| L30-11 | Lawyer                   | Ravi has one; lawyer review of doc 49 legal set by **week 6**                                                                                                                                                     | 49             |
| L30-12 | GPU                      | Stay on GTX 1660 SUPER 6 GB (no RTX 3090)                                                                                                                                                                         | 27             |
| L30-13 | Pilot drivers            | 10+ at launch                                                                                                                                                                                                     | 26, 28, 31     |
| L30-14 | Insurance                | Cargo + commercial insurance in place (policy limits / named insured / lessor wording to be read: **verify**)                                                                                                     | 20             |
| L30-15 | Oracle                   | Signed up, home region Toronto (ca-toronto-1)                                                                                                                                                                     | 28, 98         |

## Single on-call design (Ravi alone)

- **Severity → channel.** Sev1 (site/payments down, breach, cooler excursion): ntfy high-priority + phone call-style alarm, bypasses quiet hours. Sev2 (one host down but failover healthy, queue backlog, red margin): ntfy normal; quiet hours hold until 07:00. Sev3 (warnings, drift, cert < 14 days): daily brief at 08:00 only.
- **Quiet hours 22:00–07:00 Toronto.** Only Sev1 pages. Everything else is batched in the morning brief.
- **Agents handle first.** The ops agent runs the runbook steps that are safe and reversible (restart a worker container on Ubuntu, re-run a failed DBOS step, switch routing to Oracle/haversine, pause a sweep). It never promotes Oracle (`promote.sh` stays manual), never refunds above $100, never touches money records. Every auto action is logged and listed in the brief.
- **Dedupe + escalation.** One alert per incident (Uptime Kuma + Alertmanager grouping, 10-min group window). If a Sev1 isn't acked in 15 min, repeat every 5 min; after 30 min, the system enters safe mode (bookings show "please retry", D-LB1) rather than wait for a human.
- **Runbooks** (doc 52) each get an "agent can do / Ravi must do" split and a one-screen phone version.
- **Risk:** no human backup. If Ravi is unreachable for a day, safe mode protects data but stops new bookings. Recommend naming a backup before the proven window (week 15).

## Leased truck (lessee responsibilities)

- **CVOR:** required for a commercial truck with registered gross or actual weight over 4,500 kg (**verify** on ontario.ca). Under a lease the **operator who controls the truck (PorterChain as lessee)** is normally the CVOR holder, not the lessor; the lease agreement should be carried in the truck (**verify** HTA / lawyer).
- **Inspections and maintenance:** daily trip inspection = driver/operator duty (always). Annual inspection and maintenance: whoever the lease assigns; read the lease. Keep records 6 years with other records.
- **Insurance:** lessor usually requires PorterChain's commercial auto liability with the lessor as additional insured / loss payee, plus physical damage. Insurance is in place; confirm the lease wording matches the policy (**verify**).
- **BOL:** unchanged; PorterChain issues the bill of lading as carrier.
- **Gating (L-truck):** public truck price goes live only when CVOR (if over threshold), lease copy on file, insurance certificate naming the truck, and BOL template are all checked in admin.
- **Costs for the truck price card (week 3):** monthly lease + km charge over allowance + insurance share + fuel + driver pay + maintenance (if lessee) + CVOR/plates as charged. Ravi provides the lease numbers; the 50/35 margin bands apply.
- **ELD:** still open — legal check whether federal/Ontario ELD rules apply (they target hours-of-service-regulated carriers; local short-haul may be exempt, **verify**).

## GPU stays 6 GB: re-check of doc 27 with 10+ drivers

**VRAM budget (GTX 1660 SUPER, 6,144 MiB):** Qwen3.5-0.8B Q8 ≈ 1.0 GB + Qwen3.5-4B Q4_K_M ≈ 3.4 GB + LoRA ≈ 0.1 GB + KV cache (8K ctx, q8_0, 2 slots) ≈ 0.6 GB + CUDA overhead ≈ 0.4 GB ≈ **5.5 GB**. Phi-4-mini Q4 (≈ 2.5 GB) **does not fit alongside** these.

**Change:** Phi-4-mini runs the second check **on CPU** (llama.cpp, 8 threads, Q4) instead of swapping on the GPU. Its verdicts are short (yes/no + reason, ≤ 64 tokens), so CPU at an estimated 6–12 tok/s gives roughly 5–15 s per check, without evicting the 4B model. Swapping on GPU (reload 3–10 s each way) stays as a fallback for batches at night.

**Load at pilot (estimate):** 10–15 drivers ≈ 60–200 jobs/day. Dispatch, pricing, tax and routing are deterministic code (T0) and never wait on the GPU. Agent calls ≈ 5–8 per job → ≈ 300–1,600 calls/day. One 4B call (1–2K prompt, ~200 output tokens) ≈ 6–10 s estimated → 6–10 calls/min at concurrency 1–2 → peak-hour backlog of a few minutes, fine for suggest-rung work, **not fine for customer-facing live chat**.

**Queueing rules:** DBOS queue `gpu` concurrency 2; priority 1 = customer-facing drafts and dispatch exceptions, 2 = merchant/ops, 3 = back-office/batch (night). Timeout 60 s → fall back to template reply or human. Training (QLoRA) only 23:00–06:00 with serving moved to CPU 0.8B.

**Autonomy expectation (adjusted):** the 99% over 500 jobs bar (L23) stays the gate, but on 6 GB expect most agents to remain at **suggest** through the proven window; plan for **2–3 hours/day of Ravi review** at pilot volume. Money and customer-text agents need both verifier and Phi agreement, so their pass rate will be lower. Low-volume agents won't reach 500 jobs by week 22.

**Risks (honest):** (1) 4B quantized tool-calling accuracy is the main limit — a bigger model would raise autonomy; (2) one GPU = single point of failure; if Ubuntu is off, agents stop and humans do the work (system still runs on droplet/Oracle); (3) latency spikes at peak; (4) the 1660 has no tensor cores, so nightly fine-tunes are slow. Revisit the GPU upgrade if review load exceeds 3 h/day for 2 weeks.

## 10+ pilot drivers: capacity check

| Area          | Need at 10–20 drivers                                                                      | Plan                                                               | Verdict                                            |
| ------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | -------------------------------------------------- |
| GPS → Redis   | 1 ping / 5–10 s each ≈ 2–4 writes/s                                                        | Redis latest-position keys on droplet                              | trivial                                            |
| Live map push | 20 positions/5 s to a few admin screens                                                    | SSE/WebSocket from droplet                                         | trivial                                            |
| Push          | ≤ few thousand/day                                                                         | Expo push (free) + web-push + ntfy                                 | fine                                               |
| Dispatch      | 20 drivers × ~200 stops/day                                                                | OR-Tools + OSRM matrix on Ubuntu, Oracle fallback, haversine ×1.35 | fine (matrix 220×220 < 1 s)                        |
| Onboarding    | 10+ drivers × police check + abstract + contractor agreement + DPWRA notices + app install | schedule weeks 10–13, 2–3 drivers/week, admin checklist            | needs Ravi time; police checks can take days–weeks |
| Postgres      | < 10k rows/day                                                                             | droplet 8 GB                                                       | fine                                               |

## Oracle signed up (Toronto): next setup steps

U28-3 partly resolved (account + home region exist; A1 capacity confirmed only when the instance is created). Next steps (Ravi or approved agent, no paid upgrade):

1. Set a $0 budget alert; stay on Always Free (do not upgrade to Pay-As-You-Go unless A1 capacity requires; that would need Ravi's OK).
2. Create compartment `porterchain`, VCN + subnet, security list (22 from Ravi IP only, 51820/udp WireGuard, 80/443).
3. Create VM.Standard.A1.Flex (up to 4 OCPU / 24 GB, Ubuntu 24.04 arm64, 200 GB block total).
4. Add as WireGuard peer of Ubuntu `wg0` and droplet.
5. Install Postgres replica, Caddy, Uptime Kuma, OSRM (GTA+150 km), encrypted backup target; check Valhalla arm64 image (U28-4).
6. Run the four drills from doc 28.
