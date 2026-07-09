# PorterChain Charter

**Type:** CANONICAL (company)  
**Status:** Final — supersedes all conflicting positioning, GTM, and product docs  
**Last updated:** 2026-07-09  
**Audience:** Founders, engineering, product, marketing, operations  
**Cross-refs:** [WEBSITE_GTM_EXECUTION_PLAN.md](./WEBSITE_GTM_EXECUTION_PLAN.md) · [WEBSITE_SEO_STRATEGY.md](./WEBSITE_SEO_STRATEGY.md) · [ICP.md](./ICP.md)

---

## Role of this document

This is the **single source of truth** for what PorterChain is, what we build, what we sell, and how we decide.

When any doc, page, API, or feature conflicts with this charter, **the charter wins**.

Review lens: Fowler · Evans · Beck · DHH · Thiel · Graham · Collison · Huang · Bezos · Jobs.

**Default behavior:** Validate before generating code. Challenge assumptions. Separate **today** from **vision**.

---

## Company identity

### PorterChain is NOT

- Courier company
- Trucking company
- Dispatch software
- Fleet management software
- SaaS company
- Delivery marketplace

### PorterChain IS

> **A Transportation Capacity Network powered by intelligent software.**

We orchestrate businesses, independent drivers, commercial vehicles, and logistics operations through one intelligent platform.

| Layer              | Role                                                                  |
| ------------------ | --------------------------------------------------------------------- |
| **Transportation** | The service customers pay for today                                   |
| **Software**       | The engine — makes the network faster, smarter, larger, more reliable |
| **AI**             | The intelligence — only when it solves real operational problems      |
| **Network**        | The moat — supply, demand, trust, data, execution quality             |

---

## Mission

Remove transportation bottlenecks from businesses.

**Businesses should never stop operating because transportation is unavailable.**

Whenever a company needs movement of goods, PorterChain should become the **default operating layer**.

---

## Today's business (Phase 1)

**Revenue:** Transportation services. Customers buy **reliable transportation capacity** — not software.

### Vehicle network (current + future)

| Available today                                                                                                                   | Future                                            |
| --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Sedan · SUV · Pickup Truck · Cargo Van · Minivan · Sprinter Van · Cube Van · Box Truck · Flatbed Truck · Dry Van · Straight Truck | Tractor Trailer · Specialized commercial vehicles |

### Use cases

Emergency deliveries · fleet overflow · scheduled distribution · construction logistics · electrical supply · pharmacy · laboratory transport · manufacturing logistics · marketplace pickups · commercial transportation

### Customer pain (when they call us)

Driver sick · vehicle breakdown · urgent order · overflow demand · peak season · forgotten material · address change · construction emergency · same-day request

### What we sell (outcomes)

Reliability · business continuity · transportation capacity · logistics execution · operational confidence

### What we do NOT sell

Software subscriptions · dispatch OS · AI demos · enterprise procurement theater

---

## Long-term vision (never market as today's product)

| Phase       | Name                                    | Customer-facing weight       |
| ----------- | --------------------------------------- | ---------------------------- |
| **1 (now)** | Transportation Capacity Network         | **100%**                     |
| **2**       | Business Logistics Platform             | Footnote when revenue exists |
| **3**       | AI Logistics Operating System           | Company vision only          |
| **4**       | Global Physical Commerce Infrastructure | Investor narrative only      |

**Rule:** Today's messaging reflects today's reality. Future phases are sequenced, not sold.

---

## Software philosophy

Software exists to make the transportation network:

- Faster
- Smarter
- Larger
- More reliable
- Easier to join
- Easier to operate
- Harder to replace

**Software is never the goal. Software enables the business.**

Never optimize software in isolation. **Always optimize the network.**

---

## AI philosophy

**Do NOT build AI for marketing.**

Build AI only when it:

- Automates operations
- Saves time
- Improves decisions
- Prevents failures
- Predicts demand
- Improves utilization
- Increases customer value

AI must solve real operational problems. **Never build demo AI.**

---

## Engineering principles

- Domain-Driven Design
- Modular monolith first
- Clean / hexagonal architecture where justified
- SOLID · thin controllers · rich domain models
- CQRS and event-driven architecture **where justified** (not by default)
- API-first · testable components · idempotent APIs
- Repository pattern where appropriate · dependency injection
- Background jobs · observability · ADR documentation

**Never introduce complexity without measurable business value.**

---

## Product gate (before any feature)

Answer all six. If weak on multiple dimensions and fails the 10-customer test → **reject or postpone**.

### 1. Which customer problem does this solve?

Name the business pain — not the technical gap.

### 2. Who benefits?

Merchant · Driver · Dispatcher · Admin · Receiver · Partner — at least one must benefit materially.

### 3. Does it increase at least one of?

- Revenue
- Customer retention
- Trust
- Network utilization
- Automation
- Operational efficiency
- Customer satisfaction

### 4. Does it strengthen our moat?

Moat assets (not UI or routing alone):

- Transportation network density
- Business relationships
- Operational data
- Customer trust
- Logistics intelligence
- Workflow integrations
- Execution quality

### 5. Would we still build this with only 10 paying customers?

If **no** → postpone unless blocking a current paying customer.

### 6. Does it make PorterChain harder to replace?

Repeat routes, proof history, dispatch relationship, integrated quote→delivery→POD→billing.

---

## Website principles

The site must answer in **under 15 seconds**:

1. What is PorterChain?
2. Who is it for?
3. Why does it exist?
4. Why is it different?
5. Why should customers trust it?
6. What should visitors do next?

**Order:** Customer problem first · technology second · AI last.

**Primary CTA:** Get a quote / request capacity — not demo, not explore platform.

**Never confuse customers with future vision.**

---

## Moat (what we optimize)

### NOT the moat alone

Better UI · better routing · better AI chatbot · better dispatch screen

### IS the moat

Transportation network · business relationships · operational data · customer trust · logistics intelligence · workflow integrations · execution quality · network density

Everything should strengthen **one or more** of these assets.

---

## Customer obsession

Optimize for the **first 100 paying customers**.

Every release should make PorterChain **easier to understand** and **easier to use**.

Reject features that increase complexity without significantly increasing customer value.

---

## Reality check

Always separate **TODAY** from **VISION**.

Never allow future ambitions to confuse today's customers.

---

## Founder challenge (every review)

Challenge assumptions. Identify:

- Unnecessary features · missing opportunities
- Customer · engineering · product · GTM · architectural · scaling · security · operational risks

**Never simply agree with the founder.**

Explain why something is weak, what evidence supports that conclusion, and propose a better alternative.

---

## Code / architecture review standard

Whenever reviewing code, architecture, UX, APIs, content, or product:

1. Business alignment
2. Software architecture
3. Scalability · maintainability · security · performance
4. Developer experience · customer experience
5. Investor perception (secondary to customer clarity)
6. Long-term strategic fit

### Output format

| Priority | Meaning                    |
| -------- | -------------------------- |
| **P0**   | Critical — fix before ship |
| **P1**   | High — fix before scale    |
| **P2**   | Medium                     |
| **P3**   | Nice-to-have               |

For every recommendation: **why it matters · business impact · technical impact · risk if ignored · recommended implementation**

Be brutally honest. Do not preserve poor decisions because they already exist.

---

## Canonical one-liners

**Company (internal):** Transportation Capacity Network powered by intelligent software.

**Customer (Phase 1):** Your transportation capacity partner — reliable vehicle-and-driver capacity when your own logistics can't keep up.

**Mission:** Remove transportation bottlenecks so businesses never stop operating.

---

_Sell today's capability. Build tomorrow's network. Customer understanding always wins._
