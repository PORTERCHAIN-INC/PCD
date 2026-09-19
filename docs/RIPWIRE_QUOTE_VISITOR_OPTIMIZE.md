# Ripwire Moment C — quote / visitor / optimize / website handoff

**Status:** living adapter/router blast map for P0 automation.  
**Sensor:** Ripwire 0.6.1 (`--for` / `--callers` / `--expand` / `--impact`) — 2026-09-17.  
**Prior:** [CODEGRAPH_QUOTE_VISITOR_OPTIMIZE_SCHEMAS.md](CODEGRAPH_QUOTE_VISITOR_OPTIMIZE_SCHEMAS.md).  
**Playwright:** `website/e2e/` · registry `docs/testing/website_p0_registry.json`.

Do not re-run Graphify or CodeGraph in a Ripwire session.

---

## 1. `--for="P0 quote visitor optimize handshakes website book"`

Low-confidence compact head (treat as starting set). Top symbols:

| Rank | Symbol                         | File                               | Note                                                         |
| ---- | ------------------------------ | ---------------------------------- | ------------------------------------------------------------ |
| 1    | `customerHomeUrl`              | `website/src/lib/auth.ts`          | Calls `withVisitorHandoff` + `readQuoteIntent` → portal book |
| 4    | `record_quote`                 | `visitor_tracking_service.py`      | Sole production caller: `QuoteService.create_quote`          |
| 5    | `CreateQuoteRequest`           | `schemas_booking.py`               | tested amp high                                              |
| 11   | `VisitorTrackingService`       | visitor_tracking_service.py        |                                                              |
| 13   | `merge_anonymous_session`      | `customer_service.py`              |                                                              |
| 14   | `customerPortalBookHandoffUrl` | `website/src/data/portal-links.ts` | Query → `:3004/book`                                         |

**Tail files (Playwright must touch):**

- `website/src/lib/visitor-tracking.ts` (`pc_vid`, `QUOTE_INTENT_KEY`)
- `website/src/app/[locale]/quote/page.tsx` — **redirect** → `/sign-up?intent=quote`
- `website/src/app/[locale]/book/page.tsx` (+ continue/success) — **redirect** → `customerPortalBookUrl`
- `website/src/app/[locale]/track/page.tsx` — live `GuestTrackLookup`
- `website/src/components/seo/VisitorIntelligenceBootstrap.tsx`
- `scripts/verify_anonymous_retail_surface.py` — SSOT: anonymous retail = quote CTA + track; **book on :3004**

---

## 2. `--callers=enqueue_run`

| Caller                                      | File                                   | Tested? |
| ------------------------------------------- | -------------------------------------- | ------- |
| `optimize_route`                            | `services/driver-platform/.../jobs.py` | yes     |
| `reoptimize_remaining`                      | `route_optimizer.py`                   | yes     |
| pytest HS-13 / optimize_run_queue / phase5c | `apps/api/tests/*`                     | yes     |

**Gap:** Admin OptimizePanel / operations thin router not in 1-hop caller list as a named `enqueue_run` call site (goes through HTTP → service). Keep `apps/admin/e2e/optimize.p0.spec.ts` for UI.

---

## 3. `--impact=VisitorTrackingService`

Reaches (7): batch3 booking test, wave4 merge tests, `public_guide._visitors`, `CustomerService.__init__`, `QuoteService.__init__`, `VisitorIntelligenceService.__init__`.

**radius_untested=7** on impact lens for production inits — pytest covers merge/ensure via other entrypoints; do not delete without those tests green.

---

## 4. `--expand=OptimizeRunBody` / `customerPortalBookHandoffUrl`

Confirmed bodies match CodeGraph SSOT (engine default `vroom`; handoff builds `:3004/book?…`).

---

## 5. Architecture implication for W-UI Playwright

| Route                         | Playwright assert                                                  |
| ----------------------------- | ------------------------------------------------------------------ |
| `/[locale]/quote`             | Redirect to sign-up with `intent=quote` (not an inline quote form) |
| `/[locale]/book` (+ continue) | Redirect toward customer portal `/book`                            |
| `/[locale]/track`             | Renders track hero + lookup (no Fleetbase host in page URL)        |
| `/[locale]/contact`           | 200 + contact surface                                              |
| Home CTA                      | “quote” / capacity language; no Phase-3 SKU strip as only CTA      |

Anonymous retail surface guard: `scripts/verify_anonymous_retail_surface.py`.

---

## 6. Follow-ups

```bash
ripwire . --cache=.ripwire --uses=enqueue_run
ripwire . --cache=.ripwire --uses=record_quote
ripwire . --cache=.ripwire --safe-delete=VisitorTrackingService
```

Run website P0:

```bash
pnpm --filter @porterchain/website test:e2e:install
WEBSITE_RUN_LIVE=1 pnpm --filter @porterchain/website test:e2e:p0
```
