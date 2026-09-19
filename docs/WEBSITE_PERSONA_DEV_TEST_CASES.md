# Website + GTM — development test cases

**Entry SSOT:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).  
**Ripwire Moment C:** [RIPWIRE_QUOTE_VISITOR_OPTIMIZE.md](RIPWIRE_QUOTE_VISITOR_OPTIMIZE.md) · registry [testing/website_p0_registry.json](testing/website_p0_registry.json).  
**Playwright:** `website/e2e/money-loop.p0.spec.ts` — all money-loop IDs implemented (no skeletons).

```bash
# website must be on :3000
WEBSITE_RUN_LIVE=1 pnpm --filter @porterchain/website test:e2e:p0
```

If Cursor agent sandbox kills Chromium (`kill EPERM`), run that command in a **host terminal**. Config auto-picks arm64 Chrome for Testing from `~/Library/Caches/ms-playwright` when present.

**Retail depth after handoff:** [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md) (`:3004/book` is the real book UI; website `/book` redirects).  
**Merchant/driver partner CTAs:** [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md) · [DRIVER_ADMIN_DEV_TEST_CASES.md](DRIVER_ADMIN_DEV_TEST_CASES.md).  
**Policy:** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) · charter [PORTERCHAIN_CHARTER.md](PORTERCHAIN_CHARTER.md).

**Status:** living catalog for local/CI development (not prod Doppler / SEO soak alone).  
**Mapped:** 2026-09-17 via **Graphify only** (one sensor / session) + `ARCHITECTURE.md` leaf website + `find website/src/app -name page.tsx` (**77** pages).  
**Graphify anchors:** `visitor_tracking_service.py`, `visitor_intelligence.py`, `Quote`, `BookingDraftService`, `HomeChooser`, `CapacityGuideChat`, Places (Fleetbase modules — UX only).

| Next moment | Tool                          | Use for                                                          |
| ----------- | ----------------------------- | ---------------------------------------------------------------- |
| B           | CodeGraph `explore`           | Quote/booking-draft/visitor session Pydantic fields              |
| C           | Ripwire `--for` / `--callers` | Website `lib/api` → `:8001` quotes/bookings; thin public routers |

**Charter / 15-second test:** what · who · why exist · why different · why trust · what next. Primary CTA = **get a quote / request capacity** — not demo or platform tour. Problem first · technology second · AI last. Never sell Phase 3 as today.

**Existing seeds:** `test_visitor_intelligence.py`, `test_public_inquiries.py`, booking/quote suites, `pnpm validate:website-seo` / product-vision validators (if present).

---

## 0. ID scheme & layers

| Prefix     | Layer                                              |
| ---------- | -------------------------------------------------- |
| `W-UI-*`   | Website pages `:3000` (locale-aware)               |
| `W-GTM-*`  | Messaging / CTA / charter copy                     |
| `W-API-*`  | Public quote/book/track/contact → `:8001`          |
| `W-VIS-*`  | Visitor session + intelligence handoff             |
| `W-SPA-*`  | Valhalla/OSRM distance · Google Places/tiles only  |
| `W-SEO-*`  | Locale · sitemap · hreflang · perf budget          |
| `W-AUTH-*` | Login/sign-up continue → customer/merchant portals |
| `W-INT-*`  | Contact / lead ingest / vehicle-partner inquiry    |
| `W-ARCH-*` | Negatives / intentional holds                      |

**Priority:** P0 = money/trust CTA loop · P1 = handoff integrity · P2 = SEO/locale polish · P3 = long-tail SEO leaves.

---

## 1. Surface inventory (77 `page.tsx`)

### 1.1 Money / capacity loop (P0)

| Route                                                          | Job                                                 |
| -------------------------------------------------------------- | --------------------------------------------------- |
| `/` (locale home)                                              | Brand + one CTA group — CapacityGuide / HomeChooser |
| `/quote`                                                       | Get a quote                                         |
| `/book`, `/book/continue`, `/book/success`                     | Book capacity + continue draft                      |
| `/track`, `/track/[tracking]`                                  | Public track                                        |
| `/business`, `/enterprise`, `/local-delivery`, `/construction` | Vertical entry → quote                              |
| `/vehicle-partner`, `/drive`                                   | Driver/capacity-partner inquiry                     |

### 1.2 Trust / legal

`/trust` + children (`claims`, `corrections`, `dpa`, `editorial-policy`, `founder`, `insurance`, `msa`, `research-methodology`, `security`, `service-standards`, `sla`, `subprocessors`) · `/privacy` · `/terms` · `/cookies` · `/accessibility`

### 1.3 Product education (Phase 1 only)

`/platform` · `/how-porterchain-works` · `/capabilities`, `/capabilities/[slug]` · `/solutions`, `/solutions/[vertical]` · `/vehicles` · vehicle SKUs (`sedan|suv|cargo-van|trade-van|pickup-truck|box-truck`-delivery) · `/integrations` · `/integrations-education/[slug]` · `/onboarding-education/[slug]` · `/developers`, `/developers/docs`, `/docs/[slug]` · `/faq`, `/faq/[slug]` · `/compare`, `/compare/[slug]`

### 1.4 Content / SEO leaves

`/blog` · `/blog/[slug]` · `/blog/category/[category]` · `/authors` · `/authors/[id]` · `/guides` · `/guides/[slug]` · `/success-stories` · `/success-stories/[slug]` · `/campaigns` · `/campaigns/[slug]` · `/service-areas` · `/service-areas/[slug]` · `/industry/[slug]` · `/[city]/[industrySlug]` · `/research` · `/careers` · `/company` · `/contact` · `/customers`

### 1.5 Auth bridges

`/login/[[...sign-in]]` · `/login/continue` · `/sign-up/[[...sign-up]]`

### 1.6 Engines / libs (Graphify neighbors)

| Area            | Path                                                                                     |
| --------------- | ---------------------------------------------------------------------------------------- |
| Visitor session | `booking_engine/visitor_tracking_service.py`, `visitor_intelligence.py`                  |
| Quote / draft   | `booking_engine/quote_service.py`, `booking_draft_service.py`                            |
| Public track    | `booking_engine/public_tracking_snapshot.py`                                             |
| Distance        | `MapsService` / `resolve_route_distance` (Valhalla→OSRM)                                 |
| Contact / leads | public inquiries + lead ingest bus                                                       |
| Website         | `website/src/lib/env.ts`, SEO `sitemap-entries.ts`, `analytics.ts`, Places on quote/book |

---

## 2. Charter / GTM (`W-GTM-*`)

| ID        | P   | Case                                                                                                                       |
| --------- | --- | -------------------------------------------------------------------------------------------------------------------------- |
| W-GTM-001 | P0  | First viewport: brand + one headline + one supporting line + CTA group + dominant visual — no Phase-3 metric strip as hero |
| W-GTM-002 | P0  | Primary CTA labels = quote / request capacity (not “book a demo” / “tour the platform”)                                    |
| W-GTM-003 | P0  | Customer-path pages never sell Phase 3 AI/dispatch SaaS as today’s SKU                                                     |
| W-GTM-004 | P0  | Copy frames Transportation Capacity Network — not courier / fleet SaaS / marketplace                                       |
| W-GTM-005 | P1  | CapacityGuideChat is assistive; never auto-applies Valhalla/Fleetbase/Stripe writes                                        |
| W-GTM-006 | P1  | `/platform` education stays Phase 1; deep “orchestrator/VROOM” not sold as self-serve product                              |
| W-GTM-007 | P2  | Compare pages fair; no false Google-routing claims                                                                         |

---

## 3. Page smokes (`W-UI-*`)

### 3.1 Loop pages

| ID       | P   | Route                         | Assert                                                                                              |
| -------- | --- | ----------------------------- | --------------------------------------------------------------------------------------------------- |
| W-UI-001 | P0  | `/[locale]`                   | Renders; CTA to quote/book; no Fleetbase `:8000`                                                    |
| W-UI-002 | P0  | `/quote`                      | **Redirect** → `/sign-up?intent=quote` (Ripwire + live page); Places/quote UI is on customer portal |
| W-UI-003 | P0  | `/book`                       | **Redirect** → `customerPortalBookUrl` (`:3004/book`); no inline BookingWidget on website           |
| W-UI-004 | P0  | `/book/continue`              | Forwards query (`quote_id`, etc.) to portal book                                                    |
| W-UI-005 | P0  | `/book/success`               | Portal/success path — website may redirect; assert no Fleetbase host                                |
| W-UI-006 | P0  | `/track`                      | Search by tracking number                                                                           |
| W-UI-007 | P0  | `/track/[tracking]`           | Public snapshot; map tiles OK; GPS not invented client-side                                         |
| W-UI-008 | P0  | `/contact`                    | Inquiry submits; Mailpit or lead ingest row                                                         |
| W-UI-009 | P1  | `/vehicle-partner` · `/drive` | Inquiry → CRM/lead path (`website_driver_partner` source)                                           |
| W-UI-010 | P1  | `/business` · `/enterprise`   | CTA to quote; no admin console deep-links as product                                                |

### 3.2 Trust / legal (P1 smoke)

| ID       | P   | Case                                                      |
| -------- | --- | --------------------------------------------------------- |
| W-UI-020 | P1  | Each `/trust/*` page 200 + meaningful body                |
| W-UI-021 | P1  | `/privacy` · `/terms` · `/cookies` · `/accessibility` 200 |
| W-UI-022 | P2  | Trust subpages linked from footer                         |

### 3.3 Long-tail SEO (P2–P3 smoke)

| ID       | P   | Case                                                                    |
| -------- | --- | ----------------------------------------------------------------------- |
| W-UI-030 | P2  | Vehicle delivery SKU pages render + internal CTA to quote               |
| W-UI-031 | P2  | `/service-areas/[slug]` · `/industry/[slug]` · `/[city]/[industrySlug]` |
| W-UI-032 | P2  | Blog / guides / success-stories / campaigns slug pages                  |
| W-UI-033 | P2  | `/developers/docs/[slug]` public docs                                   |
| W-UI-034 | P3  | Compare / FAQ / education slug leaves                                   |

---

## 4. API / handshakes (`W-API-*` / `W-VIS-*` / `W-SPA-*`)

| ID        | P   | Case                                                                                 |
| --------- | --- | ------------------------------------------------------------------------------------ |
| W-API-001 | P0  | `POST /v1/quotes` from website uses Valhalla→OSRM distance — never Google DM         |
| W-API-002 | P0  | Out-of-GTA / uncovered postal fails with actionable coverage error                   |
| W-API-003 | P0  | Book → Stripe Checkout URL when prepaid retail path                                  |
| W-API-004 | P0  | Public `GET /v1/orders/{tracking_number}` no auth; no PII leak beyond track contract |
| W-API-005 | P1  | Contact/inquiry endpoint rate-limited + stored                                       |
| W-VIS-001 | P0  | Anonymous visitor session created on quote                                           |
| W-VIS-002 | P0  | `/book/continue` rehydrates same visitor + draft                                     |
| W-VIS-003 | P1  | Sign-up/login continue attaches visitor → customer without orphan quotes             |
| W-VIS-004 | P1  | Visitor intelligence fuse does not invent Fleetbase order IDs                        |
| W-SPA-001 | P0  | Places autocomplete only; tiles for any embedded map                                 |
| W-SPA-002 | P0  | **Anti-case:** website never imports Fleetbase HTTP / SocketCluster / VROOM          |
| W-SPA-003 | P1  | Quote `distance_source` ∈ {valhalla, osrm} (or labeled fallback)                     |

---

## 5. Auth bridges (`W-AUTH-*`)

| ID         | P   | Case                                                                                       |
| ---------- | --- | ------------------------------------------------------------------------------------------ |
| W-AUTH-001 | P0  | `/login` Clerk customer (or continue) — not staff IdP                                      |
| W-AUTH-002 | P0  | `/sign-up` → onboarding / customer portal handoff                                          |
| W-AUTH-003 | P1  | `/login/continue` preserves book draft intent                                              |
| W-AUTH-004 | P0  | Portal links from website hit `:3004` / `:3001` — never Fleetbase console as customer path |

---

## 6. SEO / i18n (`W-SEO-*`)

| ID        | P   | Case                                                                |
| --------- | --- | ------------------------------------------------------------------- |
| W-SEO-001 | P0  | Locale routing works for default + secondary locale                 |
| W-SEO-002 | P1  | Sitemap entries cover money-loop + trust hubs                       |
| W-SEO-003 | P1  | Hreflang pairs consistent                                           |
| W-SEO-004 | P2  | Perf budget / web-vitals report gates (MATRIX_CITY_SLUGS neighbors) |
| W-SEO-005 | P2  | No soft-404 empty SEO leaves for generated slugs                    |
| W-SEO-006 | P1  | `pnpm validate:website-seo` (or successor) green                    |

---

## 7. Integrations / leads (`W-INT-*`)

| ID        | P   | Case                                                        |
| --------- | --- | ----------------------------------------------------------- |
| W-INT-001 | P0  | Contact → lead ingest bus / public inquiries                |
| W-INT-002 | P1  | Vehicle-partner inquiry tagged for admin drivers/leads      |
| W-INT-003 | P1  | Analytics `track()` does not send secrets (API keys, Clerk) |
| W-INT-004 | P2  | Meta/CAPI style events only when lead flags on              |

---

## 8. Architecture negatives (`W-ARCH-*`)

| ID         | P   | Assert hold                                                 |
| ---------- | --- | ----------------------------------------------------------- |
| W-ARCH-001 | P0  | No Google Distance Matrix / Directions for quote distance   |
| W-ARCH-002 | P0  | No PorterChain VROOM client from website                    |
| W-ARCH-003 | P0  | No Fleetbase `:8000` / SocketCluster in `website/src`       |
| W-ARCH-004 | P0  | No Phase-3-as-SKU on customer paths                         |
| W-ARCH-005 | P1  | Firebase Auth not used for website login                    |
| W-ARCH-006 | P1  | AI chat propose-only — no auto Stripe pay / Fleetbase write |

---

## 9. Suggested execution order

1. **W-GTM-001…004** + **W-UI-001…007** (charter + money loop).
2. **W-API-*** + **W-VIS-*** + **W-SPA-*** handshakes.
3. **W-AUTH-*** continue/attach.
4. **W-UI-008…010** + **W-INT-***.
5. Trust smokes **W-UI-020…022**.
6. SEO **W-SEO-*** + long-tail **W-UI-030…**.
7. Negatives **W-ARCH-*** in CI grep/guards where possible.

---

## 10. Related

- [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md) · [DEV_TEST_CASES_FULL_STACK.md](DEV_TEST_CASES_FULL_STACK.md)
- [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md)
- [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md)
- [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md) (website does **not** call VROOM; retail distance ≠ TSP)
