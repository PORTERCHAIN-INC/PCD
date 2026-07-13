# PorterChain Website & GTM Execution Plan

**Type:** CANONICAL (execution — website & GTM only)  
**Parent SSOT:** [PORTERCHAIN_CHARTER.md](./PORTERCHAIN_CHARTER.md) — company identity, product gate, review standard  
**Style:** Martin Fowler — bounded contexts, ubiquitous language, evolutionary delivery  
**Last updated:** 2026-07-09 (Waves 1–2 shipped · W2.8b/W2.12 · `4a0a008`+)  
**Audience:** Founders, product, marketing, engineering (website only)  
**Cross-refs:** [WEBSITE_SEO_STRATEGY.md](./WEBSITE_SEO_STRATEGY.md) · [ICP.md](./ICP.md) · [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md) · [PRIORITY_TODOS.md](./PRIORITY_TODOS.md)

---

## Executive summary

Independent audits (positioning, first-100-customer lens, IA, strategic failure modes) converge on one diagnosis:

> **The website was optimized for Phase 3 (AI logistics OS) and Series A investors while revenue comes from Phase 1 (transportation capacity).** Excellent engineering cannot overcome selling a product customers cannot buy.

**Fowler rule:** Do not add features to a confused model. **Stabilize ubiquitous language for today's bounded context first** (Capacity), then evolve SEO and operations storytelling without selling tomorrow's product.

| Verdict                                                                | Source                      |
| ---------------------------------------------------------------------- | --------------------------- |
| Positioning: **software company on site, capacity company in revenue** | Product architecture review |
| IA: Platform + Developers before the service customers pay for         | CPO navigation audit        |
| First 100 customers: **homepage fails 15-second test**                 | Capacity platform audit     |
| Investor screen: premature enterprise/trust theater                    | Strategic honesty review    |
| Prior GTM batches (1–4): **shipped wrong category**                    | Implementation sync         |

### What PorterChain is (charter — final)

See [PORTERCHAIN_CHARTER.md](./PORTERCHAIN_CHARTER.md). Summary:

PorterChain is **not** a courier, trucking, dispatch/SaaS/fleet software, or marketplace company.

PorterChain **is**:

> A **Transportation Capacity Network** powered by intelligent software — we orchestrate businesses, independent drivers, commercial vehicles, and logistics operations through one intelligent platform.

| Layer              | Role                                                                  |
| ------------------ | --------------------------------------------------------------------- |
| **Transportation** | The service customers pay for today                                   |
| **Software**       | The engine — makes the network faster, smarter, larger, more reliable |
| **AI**             | The intelligence — only when it solves real operational problems      |
| **Network**        | The moat — density, relationships, data, trust, execution             |

### Canonical positioning (one sentence — Phase 1, customer-facing)

> PorterChain is your **transportation capacity partner** in Ontario — reliable vehicle-and-driver capacity when your own logistics can't keep up, orchestrated through our capacity network.

**Never lead with:** “Book a courier.”  
**Always lead with:** “Your transportation capacity partner” · “An extension of your logistics operation” · “Capacity whenever your business needs it.”

### Company evolution (sell today, build tomorrow)

| Phase       | Name                                    | Website weight                                          |
| ----------- | --------------------------------------- | ------------------------------------------------------- |
| **1 (now)** | Transportation Capacity Network         | **100% of customer-facing GTM**                         |
| **2**       | Business Logistics Platform             | Footnote + `/how-porterchain-works` when revenue exists |
| **3**       | AI Logistics Operating System           | Company vision only — **not sold on homepage**          |
| **4**       | Global Physical Commerce Infrastructure | Investor narrative only                                 |

### Canonical ICP (first 100 customers)

Ops manager / owner at Ontario B2B shipper who already has vehicles and drivers but needs **overflow, backup, and same-day capacity** when normal operations fail.

**Pain moments:** driver sick · vehicle breakdown · urgent order · peak season · construction emergency · pharmacy same-day · forgotten material · customer address change.

**Not primary ICP today:** Enterprise procurement evaluating dispatch SaaS · API integrators · consumers booking parcels.

---

## Implementation status (2026-07-09)

**Commit:** `4a0a008` — Reposition website GTM from Dispatch OS to transportation capacity (Waves 1–2).

### Wave 1 — Capacity clarity ✅ shipped

| Area                                                                             | Status                         |
| -------------------------------------------------------------------------------- | ------------------------------ |
| Homepage hero + metadata + body copy                                             | ✅ Capacity / network language |
| Nav order (Services first; Platform/Developers in Resources dropdown)            | ✅                             |
| Global CTA `Get a quote` → `intent=quote` (no `intent=demo` sitewide)            | ✅                             |
| Pricing (Occasional / Recurring / Dedicated — not SaaS tiers)                    | ✅                             |
| `/business` capacity hero + fleet `#fleet` anchor                                | ✅                             |
| Lane B bridge → vehicles + quote (`PlatformBridgeSection`)                       | ✅                             |
| Homepage schema (`DeliveryService` / `LocalBusiness`, not `SoftwareApplication`) | ✅                             |
| Guards (`verify_product_vision_pages.py`)                                        | ✅ Capacity-first              |
| Build                                                                            | ✅ ~773 routes                 |

### Wave 2 — Network reframe ✅ shipped

| Area                                                                 | Status                       |
| -------------------------------------------------------------------- | ---------------------------- |
| `/platform` → how network runs delivery (EN/FR)                      | ✅                           |
| `/company`, `/customers`, `/enterprise`, `/solutions`, `/developers` | ✅ Capacity-first copy EN/FR |
| `/business` fleet grid **above fold** (directly under hero)          | ✅                           |
| Legal intros (`legal-en.json`, `legal-fr.json`)                      | ✅ Delivery services first   |
| Company FAQ: vs own driver / vs ad-hoc courier                       | ✅                           |
| Trust hub + exhibits — COI-first copy (EN/FR)                        | ✅ W2.8b                     |
| Trust nav demotion (footer/resources only)                           | ✅                           |
| Vehicle SKU naming (`Sprinter Van` = ops `sprinter_van`)             | ✅ W2.12                     |
| SEO views + `internal-linking.ts`                                    | ✅ Quote + fleet bridge      |
| `schema.ts` / `config.ts` / site metadata                            | ✅ Capacity network language |

**Wave 2 exit gate (engineering):** ✅ Pass — guards green, no Dispatch OS on Lane A or trust exhibits.

**Wave 2 exit gate (human):** Run 15-second test with 3 ICP personas post-deploy.

### Remaining repositioning debt (Wave 3+)

| Area                                                     | Status                                  |
| -------------------------------------------------------- | --------------------------------------- |
| Lane B bulk body copy (~700 URLs in `en.json`/`fr.json`) | ⚠️ Not bulk-rewritten                   |
| `WEBSITE_SEO_STRATEGY.md` full sync                      | ⚠️ G0.1 partial (`ICP.md` ✅)           |
| Blog/case studies — capacity language pass               | ⚠️ Partial (construction case study ✅) |

### What's next — execution waves

| Wave                          | ID  | Scope                                                                  | Priority        |
| ----------------------------- | --- | ---------------------------------------------------------------------- | --------------- |
| **Wave 2 — Network reframe**  | W2  | Complete — trust copy + vehicle names shipped                          | **Done**        |
| **Wave 3 — SEO + governance** | W3  | Lane B bulk copy, `WEBSITE_SEO_STRATEGY.md`, blog pass, checklist §1.1 | **P2 — next**   |
| **Deferred (Series A)**       | —   | Status page, investor facts sheet, portal picker, dashboard demo       | After first 100 |

**Guards (run before deploy):**

```bash
apps/api/.venv/bin/python scripts/verify_product_vision_pages.py
apps/api/.venv/bin/python scripts/verify_i18n_parity.py
pnpm --filter @porterchain/website build
```

_Charter + cursor rule: `docs/PORTERCHAIN_CHARTER.md`, `.cursor/rules/porterchain-charter.mdc`_

---

## Part 1 — Martin Fowler execution principles

Apply these before any large copy or SEO expansion.

| Principle                          | PorterChain application                                                                                                                                                                                                                                                      |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ubiquitous language**            | Customer copy: _capacity_, _vehicle + driver_, _capacity partner_, _overflow_, _proof of delivery_. Internal code may keep `dispatch`, `merchant`, `fleet`. **Never** “Dispatch OS” or “platform subscription” on Lane A until Phase 2 revenue                               |
| **Bounded contexts**               | **Lane A (Capacity)** = brand, nav, pricing, CTAs — what customers buy. **Lane B (SEO)** = programmatic local/industry inbound — must bridge to **quote**, not platform. **Lane C (Operations)** = how we run delivery (`/how-porterchain-works`) — demoted; not primary nav |
| **Strangler fig**                  | Reposition homepage and nav first; bulk-rewrite Lane B incrementally — no big-bang 737 URL rewrite                                                                                                                                                                           |
| **Evolutionary architecture**      | Wave 1 ✅ messaging + IA + pricing. Wave 2 ✅ reframe platform/developers/company/customers/enterprise + `DeliveryService` on home. Wave 3: Lane B SEO body + governance docs                                                                                                |
| **Build only what you can verify** | Remove or source all stats; no fake SaaS tiers, ACV targets, or enterprise SLAs for software not sold                                                                                                                                                                        |
| **Simplify the decision tree**     | One primary CTA: **Get a quote** / **Request capacity**. One sales motion: **transportation request** → quote → first delivery → recurring program                                                                                                                           |

### Homepage must answer (in order)

1. **What is PorterChain?** — Transportation capacity partner
2. **Who is it for?** — B2B shippers in Ontario (construction, pharmacy, labs, manufacturing, distribution)
3. **What problem?** — When normal ops fail (driver sick, breakdown, overflow, urgent)
4. **Why different?** — Extension of your logistics operation — tracking, proof, accountable execution (not “book a courier”)
5. **Why trust?** — Service areas, vehicles, insurance/COI, live track, POD
6. **What next?** — Get a quote / request capacity

**Do not** introduce AI before capacity. **Do not** introduce enterprise software before the service.

### Sales principles (outcomes, not features)

| Sell                       | Do not sell           |
| -------------------------- | --------------------- |
| Extra van today            | Software              |
| Urgent delivery            | AI                    |
| Overflow / backup capacity | Dispatch algorithm    |
| Same-day transportation    | Platform subscription |
| Recurring distribution     | Demo (as default CTA) |

### Moat (honest sequencing)

| Now (real moat)                           | Later (amplifier)               |
| ----------------------------------------- | ------------------------------- |
| Growing driver + vehicle network          | AI planning                     |
| Repeat B2B shipper demand                 | Multi-fleet orchestration       |
| Operational data from executed deliveries | Autonomous                      |
| Execution quality + customer trust        | Global infrastructure narrative |

**AI is not the moat today.** AI eventually strengthens the moat.

---

## Part 2 — Top strategic failure modes (revised)

_Assumes excellent engineering. Failure drivers = positioning, GTM, pricing, website honesty._

| #   | Failure mode                                     | Evidence on site today                                   | P×I | Prevention                                                 |
| --- | ------------------------------------------------ | -------------------------------------------------------- | --- | ---------------------------------------------------------- |
| 1   | **Selling software customers can't buy**         | Dispatch OS hero, SaaS pricing, demo CTA                 | H×H | Wave 1: capacity-first copy + quote CTA                    |
| 2   | **15-second test failure**                       | Hero has no sedan→box truck; no pain moment              | H×H | Hero = capacity partner + vehicle SKUs                     |
| 3   | **Fake SaaS pricing destroys trust**             | $2k–$4k/mo platform tiers, $24k ACV                      | H×H | Per-vehicle/zone/route pricing framework                   |
| 4   | **Wrong leads from demo motion**                 | `intent=demo` sitewide                                   | H×M | `intent=quote` + ops handoff                               |
| 5   | **Enterprise theater before enterprise revenue** | Trust/DPA/MSA/SLA as GTM front door                      | M×H | COI + delivery commitments; legal on request               |
| 6   | **Platform nav implies API is the product**      | Developers in top nav                                    | M×M | Footer tier; “integrations by request”                     |
| 7   | **SEO bridge wastes high-intent traffic**        | Lane B → explore platform / demo                         | H×H | Bridge → get quote + vehicle fit                           |
| 8   | **Anti-courier positioning confuses category**   | FAQ “not a courier” while selling capacity               | M×M | “Capacity partner” — premium B2B, not consumer app         |
| 9   | **Split identity (OS vs fleet)**                 | `/business` fleet below fold; home = OS                  | H×H | Single Capacity narrative; fleet above fold on `/business` |
| 10  | **Schema says software company**                 | `SoftwareApplication` on Lane A                          | M×M | `DeliveryService` + `LocalBusiness` on home                |
| 11  | **Investor optimization before customer #100**   | Phase 4 status page, facts sheet prioritized             | M×H | Defer investor track until Wave 1–2 pass                   |
| 12  | **Guard rails enforce wrong vision**             | `verify_product_vision_pages.py` checks Dispatch OS      | M×M | Update guards for Capacity language                        |
| 13  | **Legal intro inverted**                         | “Dispatch orchestration software” first                  | M×M | “Commercial delivery services” first                       |
| 14  | **No “vs own employee” decision content**        | Compare pages vs TMS, not vs Sarah in the SUV            | M×H | FAQ + compare strip for SMB B2B                            |
| 15  | **Founder narrative drift**                      | This doc previously said Dispatch OS; revenue = capacity | H×H | **This revision** + sync `ICP.md`, SEO strategy            |

---

## Part 3 — Audit findings (capacity platform lens)

### 3.1 Positioning (15-second test: **PASS on Lane A** — verify with humans post-deploy)

| Finding                                                | Location                                  | Status (post `4a0a008`) | Wave |
| ------------------------------------------------------ | ----------------------------------------- | ----------------------- | ---- |
| Hero sells Dispatch OS, not capacity                   | `corporate-en.json` → `home.hero`         | ✅ Fixed                | W1   |
| Metadata: “Dispatch OS for Regional B2B Logistics”     | `corporate.metadata.home`                 | ✅ Fixed                | W1   |
| Homepage body = product tour (routing, API, analytics) | `HomePlatformBody`, `corporate.home`      | ✅ Fixed                | W1   |
| Fleet SKUs only on `/business` below fold              | `business-en.json` → `fleet`              | ✅ Above fold           | W2   |
| Nav CTA “Get a demo”                                   | `SiteNavbar`, `corporate.nav.bookNow`     | ✅ Fixed                | W1   |
| Company mission = “dispatch OS”                        | `corporate.company`                       | ✅ Fixed                | W2   |
| Pricing = software-led SaaS tiers                      | `corporate.pricing`                       | ✅ Fixed                | W1   |
| Trust exhibits still say “dispatch OS subscription”    | `corporate.trust.*` DPA/MSA/subprocessors | ⚠️ Procurement copy     | W2.8 |

### 3.2 Information architecture (**CORRECTED** on Lane A)

| Finding                                              | Target                                     | Status (post `4a0a008`) |
| ---------------------------------------------------- | ------------------------------------------ | ----------------------- |
| Platform + Developers before Services                | Services → Industries → Pricing → Contact  | ✅ Fixed                |
| `/business` without capacity hero / fleet prominence | Capacity hero + fleet above fold           | ✅ Fixed                |
| Trust Center in primary nav                          | Footer + Resources dropdown; COI-first hub | ✅ Nav fixed; body W2.8 |
| Lane B bridge → platform/demo                        | Bridge → quote + `/business#fleet`         | ✅ Fixed                |
| Breadcrumbs on L2+                                   | Keep                                       | ✅ Shipped              |

### 3.3 First 100 customers (**primary optimization target — re-test post-deploy**)

| Check                                                 | Status (post `4a0a008`)                     |
| ----------------------------------------------------- | ------------------------------------------- |
| Homepage shows vehicle + driver capacity              | ✅ Hero, body, `/business#fleet`            |
| “When to use PorterChain vs your own driver”          | ✅ Company FAQ (EN/FR)                      |
| CTA leads to **requesting transportation** (quote)    | ✅ `intent=quote` sitewide                  |
| Pricing attracts capacity buyers, not SaaS evaluators | ✅ Occasional / Recurring / Dedicated bands |

**Next:** Run live 15-second test with construction, pharmacy, and electrical personas; log pass/fail in ops.

### 3.4 Investor / enterprise (**defer sales motion; pages exist**)

- Trust/DPA/MSA/SLA pages exist — ✅ **footer/resources only**; do not lead GTM
- Exhibit copy still procurement-oriented — acceptable for inbound enterprise; reframe in W2.8 if it confuses capacity buyers
- Investor facts sheet, dashboard demo, status page: **Phase 4 deferred**

---

## Part 4 — Target information architecture

```
Marketing (porterchain.com) — Lane A: CAPACITY

├── Services (primary nav → /business)
│   ├── Vehicle catalog (sedan → box truck + driver)
│   ├── Use cases (overflow, urgent, recurring, backup)
│   └── Service areas / Ontario coverage
├── Industries (/solutions, /industry/*)
│   └── Construction · pharmacy · labs · manufacturing · wholesale
├── Pricing (/pricing)
│   └── Capacity economics (zone + vehicle + SLA bands) — NOT SaaS tiers
├── How it works (/how-porterchain-works or /guides/how-porterchain-works)
│   └── Book → dispatch → track → proof (technology second)
├── Company (/company, /careers, /contact)
│   └── Mission + phased vision (1→4) without selling Phase 3
└── Resources (footer)
    ├── /blog, /guides, /compare, /faq, /track
    ├── /platform          — REFRAMED: “How we run your delivery” (Lane C)
    ├── /developers        — Footer: integrations by request (Lane C)
    └── Programmatic SEO (Lane B) — capacity bridge → quote

Applications (separate hosts — unchanged)
├── merchant.*  merchant portal (internal ops — not marketed as SKU)
├── customer.*  retail book (:3004 only)
├── driver.*
└── api.*
```

**Primary CTA (Lane A + Lane B):** Get a quote · Request capacity · Talk to dispatch  
**Secondary CTA:** See vehicles · Service areas · Track a shipment  
**Retired as default:** Get a demo · Explore platform · Book a delivery (consumer)

---

## Part 5 — SEO strategy (facade to capacity, not platform)

_Update [WEBSITE_SEO_STRATEGY.md](./WEBSITE_SEO_STRATEGY.md) in Wave 3 (G0.1)._

### 5.1 Dual-lane model (revised)

| Lane                     | Purpose                         | Index strategy                   | Brand weight                            |
| ------------------------ | ------------------------------- | -------------------------------- | --------------------------------------- |
| **A — Capacity (brand)** | First 100 customers, conversion | Index, nav, sitemap priority 1.0 | **Defines brand**                       |
| **B — Programmatic**     | Local/industry inbound          | Index with **capacity bridge**   | Lead gen only — must not redefine brand |

**Bridge rule (mandatory on every Lane B template — replace current platform bridge):**

```text
[Heading] Need {industry} delivery capacity in Ontario?
- Professional drivers · Sedan through box truck · Tracking and proof of delivery
[CTA] Get a quote → /contact?intent=quote&from={page}
[CTA] See vehicles → /business#fleet
```

Implement in: `PlatformBridgeSection.tsx` (rename to `CapacityBridgeSection` optional), `IndustryLandingView.tsx`, `CityIndustryLandingView.tsx`, `ContentClusterView.tsx`.

### 5.2 Keyword strategy

| Priority | Intent cluster                                          | Action                                                 |
| -------- | ------------------------------------------------------- | ------------------------------------------------------ |
| **P0**   | B2B capacity + overflow + same-day                      | Hero, `/business`, pricing                             |
| **P1**   | Construction/pharmacy/lab delivery Ontario              | Lane B industry + city×industry                        |
| **P2**   | Vehicle-class delivery (sprinter, cargo van, box truck) | `/business#fleet` + selective SEO — index where honest |
| **P3**   | Dispatch software (non-geo)                             | **Defer** — not Phase 1 revenue                        |
| **P4**   | Consumer parcel / “courier app”                         | Noindex or exclude from nav                            |

### 5.3 Schema strategy (revised)

| Page type                  | Schema                                               | Notes                                                   |
| -------------------------- | ---------------------------------------------------- | ------------------------------------------------------- |
| `/`, `/business`           | `Organization` + `DeliveryService` + `LocalBusiness` | **Stop** leading with `SoftwareApplication` on homepage |
| `/platform`, `/developers` | `WebPage` only or demoted                            | No software-product schema until Phase 2                |
| Lane B industry/city       | `Service` + `FAQPage`                                | `provider` → Organization                               |
| `/contact`                 | `LocalBusiness`                                      | Keep for local trust                                    |

### 5.4 Measurement (GA4) — retarget events

| Event              | Trigger                                           |
| ------------------ | ------------------------------------------------- |
| `quote_request`    | `/contact` submit `intent=quote`                  |
| `capacity_explore` | `/business#fleet` CTA clicks                      |
| `track_shipment`   | `/track` engagement                               |
| `seo_bridge_click` | Capacity bridge on Lane B pages                   |
| Attribution        | `from=` + UTM → Zoho (`PCD From`) — **keep P2.6** |

---

## Part 6 — Master execution checklist

_Terminology: **Company Phase** = 1–4 evolution. **Execution Wave** = website work._

### Phase 0 — Governance (Week 0)

- [x] **G0.0** Rewrite this doc SSOT for Phase 1 capacity platform (2026-07-09)
- [ ] **G0.1** Sync [WEBSITE_SEO_STRATEGY.md](./WEBSITE_SEO_STRATEGY.md) + masterrule §21 to capacity positioning — [ICP.md](./ICP.md) ✅ synced 2026-07-09
- [ ] **G0.2** Assign DRI: Lane A (capacity GTM) vs Lane B (SEO)
- [x] **G0.3** Update `verify_product_vision_pages.py` to enforce Capacity language (block Dispatch OS hero, require quote CTA) — shipped `4a0a008`

### Wave 1 — Capacity clarity (P0) — **do before anything else**

#### Positioning & homepage

- [x] **W1.1** Homepage metadata: capacity partner, not Dispatch OS (`corporate.metadata.home`)
- [x] **W1.2** Homepage hero: pain moment → capacity SKUs → quote CTA (`corporate.home.hero`, `Hero.tsx`)
- [x] **W1.3** Replace `HomePlatformBody` software tour with: pain block · vehicles · how-it-works · trust · differentiation (tech one section)
- [x] **W1.4** Global nav CTA: `Get a quote` → `/contact?intent=quote` (retire `intent=demo` as default)
- [x] **W1.5** Nav order: Services (`/business`) · Industries · Pricing · Contact — demote Platform & Developers to footer

#### Pricing

- [x] **W1.6** Replace SaaS tiers with capacity bands: Occasional · Recurring routes · Dedicated capacity
- [x] **W1.7** Pricing FAQ: lead with per-vehicle/zone economics; footnote on internal software

#### Guards

- [x] **W1.8** Update `verify_product_vision_pages.py` + smoke tests in §Part 9

**Wave 1 exit gate:** 3 target buyers (construction, pharmacy, electrical) answer “what do I buy?” in 15 seconds · guards green on **new** vision

### Wave 2 — Reframe operations pages (P1)

- [x] **W2.1** `/business`: capacity hero; **fleet grid above fold**; CTA = request consultation / quote
- [x] **W2.2** `/platform` → “How we run your delivery” (operations facade, not product catalog)
- [x] **W2.3** `/developers` → footer nav; copy = “integrations by request for high-volume shippers”
- [x] **W2.4** `/enterprise` → dedicated capacity programs; remove RBAC/SSO as hero
- [x] **W2.5** `/customers`: “trust us to run deliveries” not “run dispatch on OS”
- [x] **W2.6** `/company`: mission = reduce friction moving goods; vision footnote Phases 1→4
- [x] **W2.7** Legal intros (`legal-en.json` / `legal-fr.json`): commercial delivery services first
- [x] **W2.8a** Trust pages: DPA/MSA/SLA live; **removed from primary nav** (footer + Resources dropdown)
- [x] **W2.8b** Trust hub + exhibit copy: COI-first hero; capacity-program framing on DPA/MSA/subprocessors/SLA (EN/FR)
- [x] **W2.9** `CapacityBridgeSection` (was `PlatformBridgeSection`): quote CTA, not demo/platform
- [x] **W2.10** JSON-LD: `DeliveryService` on home; remove `SoftwareApplication` from homepage layout
- [x] **W2.11** Add FAQ: PorterChain vs own employee / vs ad-hoc courier
- [x] **W2.12** Align vehicle names with ops (`Sprinter Van` customer-facing = `sprinter_van` in API/pricing)

**Wave 2 exit gate:** No page sells uninvoicable software · platform/developers unreachable from top nav

### Wave 3 — SEO body & governance (P2)

- [ ] **W3.1** Bulk Lane B copy (`en.json`/`fr.json` SEO namespaces) — capacity language
- [ ] **W3.2** Internal links: city×industry → `/business` + quote, not `/platform`
- [x] **W3.3** FR parity for corporate home + business + pricing + platform/company/customers/enterprise/solutions/developers — shipped W1–W2 (`corporate-fr.json`)
- [ ] **W3.4** Blog: customer stories (delivery outcomes), not platform posts
- [ ] **W3.5** Reconcile [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md) §1.1

### Deferred — Series A / investor (after first 100)

- [ ] **P4.1** Status page
- [ ] **P4.2** SSO/SAML roadmap on `/trust`
- [ ] **P4.3** RBAC public excerpt
- [ ] **P4.5** Investor facts sheet
- [ ] **P4.6** Portal picker at `/login`
- [ ] **P4.7** Dashboard demo on `/platform`

### Legacy checklist (batches 1–4) — reference only

_Items marked [x] shipped **Dispatch OS GTM** — superseded by Waves 1–3 above._

<details>
<summary>Prior Phase 1–3 items (Jul 2026 — do not treat as complete strategy)</summary>

- [x] P1.1–P1.4 Homepage Dispatch OS + demo CTA — **revert in W1**
- [x] P1.6–P1.10 Trust + enterprise expansion — **demote in W2**
- [x] P1.12 Developers top nav — **demote in W2**
- [x] P2.1–P2.3 SaaS pricing + software-first `/business` — **revert in W1/W2**
- [x] P2.6 Zoho attribution — **keep**
- [x] P2.7–P2.9 Hosted dev docs — **keep, demote**
- [x] P3.1–P3.6 Platform bridge + schema split — **reframe in W2/W3**

</details>

---

## Part 7 — Page-by-page action matrix

| Page                      | Was (pre-W1)                  | Target action                            | Wave | Status (`4a0a008`) |
| ------------------------- | ----------------------------- | ---------------------------------------- | ---- | ------------------ |
| `/`                       | Dispatch OS hero; no vehicles | Capacity partner hero + pain + quote CTA | W1   | ✅                 |
| `/business`               | OS hero; fleet below fold     | Capacity hero; fleet above fold          | W2   | ✅                 |
| `/pricing`                | Fake SaaS tiers               | Vehicle/zone/route bands                 | W1   | ✅                 |
| `/platform`               | Sells uninvoicable software   | How we run your delivery                 | W2   | ✅                 |
| `/developers`             | Top nav; API as product       | Footer; integrations by request          | W2   | ✅                 |
| `/enterprise`             | Procurement theater           | Dedicated capacity programs              | W2   | ✅                 |
| `/customers`              | “Dispatch OS” social proof    | Delivery outcome stories                 | W2   | ✅                 |
| `/company`                | OS mission                    | Mission + phased vision                  | W2   | ✅                 |
| `/contact`                | `intent=demo` default         | `intent=quote` default                   | W1   | ✅                 |
| `/trust/*`                | Front-door enterprise GTM     | Footer only; COI-first hub               | W2   | ✅                 |
| `/industry/*`, city pages | Bridge to platform/demo       | Bridge to quote + fleet                  | W2   | ✅                 |
| Legal                     | Software-first intro          | Delivery services first                  | W2   | ✅                 |
| Nav/footer                | Platform, Developers, demo    | Services, quote, demoted ops links       | W1   | ✅                 |
| Lane B SEO templates      | Dispatch OS body copy         | Capacity language at scale               | W3   | ⚠️ Open            |

---

## Part 8 — Copy bank (shipped W1–W2 — reference in `corporate-en.json` + `corporate-fr.json`)

### Nav & CTAs

| Key            | Current (wrong)        | Target                       |
| -------------- | ---------------------- | ---------------------------- |
| `nav.bookNow`  | Get a demo             | **Get a quote**              |
| Primary href   | `/contact?intent=demo` | `/contact?intent=quote`      |
| `nav.business` | Programs               | **Services** or **Delivery** |

### Homepage metadata

| Field       | Target                                                                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Title       | `Porterchain \| Transportation Capacity Partner — Ontario B2B Delivery`                                                                     |
| Description | Reliable vehicle-and-driver capacity when your fleet isn't enough — sedan through box truck, tracking and proof of delivery across Ontario. |

### Homepage hero

| Field         | Target                                                                                                                                                                              |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Badge         | `Transportation capacity partner`                                                                                                                                                   |
| Title         | `Capacity for your business when logistics can't slow down`                                                                                                                         |
| Subtitle      | `Driver sick? Van down? Urgent order? Porterchain provides professional drivers and vehicles — sedan through box truck — across Ontario, with live tracking and proof of delivery.` |
| Primary CTA   | `Get a quote`                                                                                                                                                                       |
| Secondary CTA | `See vehicles` → `/business#fleet`                                                                                                                                                  |

### Capacity bridge (Lane B — replace platform bridge)

**Title:** Need delivery capacity in Ontario?  
**Bullets:** Professional drivers · Sedan through box truck · Tracking and proof of delivery  
**CTAs:** Get a quote · See vehicles

### Anti-positioning FAQ (replace “not a courier”)

**Q:** Is Porterchain just a courier?  
**A:** Porterchain is your **transportation capacity partner** — an extension of your logistics operation when you need backup vans, same-day runs, or recurring distribution without hiring. You get accountable execution, tracking, and proof — not a consumer parcel app.

### Footer tagline

**Target:** `Moving Commerce On-Chain`

### Explicitly retired (do not use customer-facing)

- Dispatch OS / dispatch operating system (hero)
- Software-led pricing
- Growth / Business / Enterprise platform tiers
- Get a demo (as global primary CTA)
- “We're not a courier” without capacity partner framing
- $24k ACV / platform subscription as default narrative

---

## Part 9 — Validation commands

```bash
# Product vision (capacity language — W1.8 shipped)
apps/api/.venv/bin/python scripts/verify_product_vision_pages.py

# i18n parity (corporate EN/FR — includes W2 FR parity)
apps/api/.venv/bin/python scripts/verify_i18n_parity.py

pnpm validate:product-vision
pnpm --filter @porterchain/website build

# Manual smoke (post Waves 1–2 — all should pass)
# 1. Open /en — title contains "Capacity" or "Delivery", NOT "Dispatch OS"
# 2. Scroll home — vehicle classes or pain moment above fold; no SaaS product tour
# 3. Nav CTA — "Get a quote" not "Get a demo"
# 4. /pricing — no "$2k/mo platform" tiers; Occasional / Recurring / Dedicated
# 5. /business — fleet grid visible without deep scroll
# 6. /platform — "How we run your delivery", not product SKU catalog
# 7. /industry/construction-materials — bridge CTA = quote, not explore platform
# 8. Top nav — no Developers or Platform as L1 (Resources dropdown OK)
# 9. /en/contact?intent=quote&from=industry/test — GA4 `quote_request` + attribution
# 10. /trust/dpa — optional: confirm procurement copy acceptable or schedule W2.8b
```

---

## Part 10 — What not to do

- Do **not** optimize homepage for investors before first 100 customers pass the 15-second test in production
- Do **not** sell Dispatch OS, AI, or platform subscriptions as today's product
- Do **not** use “Get a demo” as global primary CTA
- Do **not** lead legal/trust pages with procurement theater for seed-stage capacity sales
- Do **not** add programmatic URL types until capacity bridge ships
- Do **not** upgrade Next/React (dependency freeze until ~2026-10)
- Do **not** put consumer `BookingWidget` on marketing homepage
- Do **not** claim AI on website until a named shippable capability exists
- Do **not** fork homepage metadata between `corporate-en.json` and `en.json`
- Do **not** extend Dispatch OS guards — ✅ updated in W1.8 (`4a0a008`)

**Reject rule:** If a change makes the site look more “Silicon Valley” but reduces customer clarity in 15 seconds — **reject it**.

---

## Part 11 — Success metrics (90 days — first 100 customers)

| Metric                                                      | Baseline (pre-`4a0a008`) | Target (90d post-deploy)               |
| ----------------------------------------------------------- | ------------------------ | -------------------------------------- |
| 15-second test pass (3 ICP personas)                        | Fail                     | 3/3 can name vehicle + driver capacity |
| Primary CTA click → quote intent                            | Demo-led                 | >80% quote/capacity                    |
| Sales disqualification: “thought you were software”         | High                     | Rare                                   |
| Sales disqualification: “thought you were consumer courier” | Medium                   | Rare                                   |
| Quote requests / month                                      | ? (set at deploy)        | +50% vs post-deploy baseline           |
| Repeat shipper conversion (2nd delivery within 30d)         | ?                        | Track in ops                           |
| Lane B bridge → quote CTR                                   | ?                        | > historical bridge → platform         |
| `validate:product-vision`                                   | Enforces OS              | ✅ Enforces Capacity (shipped)         |

_Investor metrics (`/platform` organic, enterprise inbound “software”) — track but **do not optimize** until 15-second test passes in production._

---

## Appendix A — Source audits

1. **Capacity platform audit** — first 100 customers, 15 evaluation questions, P0/P1/P2 issue register
2. **Product architecture principles** — technology-enabled capacity platform; Phases 1–4; moat sequencing
3. **Prior GTM batches 1–4** — Dispatch OS implementation (superseded by this revision)
4. **Strategic failure modes** — §Part 2 revised table

---

## Appendix B — Document ownership

| Document                                                                         | Role after this revision                                                 |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **[PORTERCHAIN_CHARTER.md](./PORTERCHAIN_CHARTER.md)**                           | **Parent SSOT** — identity, mission, product gate, moat, review standard |
| **This file**                                                                    | Website/GTM execution — waves, checklists; must align with charter       |
| [WEBSITE_SEO_STRATEGY.md](./WEBSITE_SEO_STRATEGY.md)                             | Technical SEO — **update in G0.1** (schema, bridge, keywords)            |
| [ICP.md](./ICP.md)                                                               | First-100-customer ICP — overflow/backup capacity; synced to charter ✅  |
| [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md) | Investor readiness — **defer** until customer gate                       |

## Appendix C — Key implementation files

| Area             | Primary files                                                                                                   |
| ---------------- | --------------------------------------------------------------------------------------------------------------- |
| Homepage         | `website/src/app/[locale]/page.tsx`, `HomePlatformBody.tsx`, `Hero.tsx`, `corporate-*.json`                     |
| Nav / CTA        | `SiteNavbar.tsx`, `navbar-navigation.ts`, `footer-navigation.ts`                                                |
| Business / fleet | `business-*.json`, `/business` page components                                                                  |
| Pricing          | `corporate.pricing`, `PricingPageView`                                                                          |
| SEO bridge       | `PlatformBridgeSection.tsx`, `IndustryLandingView.tsx`, `CityIndustryLandingView.tsx`, `ContentClusterView.tsx` |
| Schema           | `schema.ts`, `HomeDeliverySchema.tsx`, `LaneASoftwareSchema.tsx` (demoted from home)                            |
| Trust            | `website/src/app/[locale]/trust/*`, `TrustDocumentsSection.tsx` — W2.8b copy optional                           |
| Attribution      | `attribution.ts`, `zoho-attribution.ts`, `AttributionCapture.tsx`                                               |
| Guards           | `verify_product_vision_pages.py`, `verify_i18n_parity.py` — capacity-first ✅                                   |
| Charter          | `docs/PORTERCHAIN_CHARTER.md`, `.cursor/rules/porterchain-charter.mdc`                                          |

---

_Sell today's capability. Build tomorrow's vision. Customer understanding always wins._
