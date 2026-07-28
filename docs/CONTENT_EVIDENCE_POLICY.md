# Content Evidence Policy

**Applies to:** All public website copy, schema, success stories, research, and programmatic SEO  
**Audit:** [PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md §9](./PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md#9-e-e-a-t-and-trust)  
**Publishable gates:** [CONTENT_MODEL_AND_TAXONOMY.md § PublishableContent](./CONTENT_MODEL_AND_TAXONOMY.md#publishablecontent)

---

## Principles

1. **No invented metrics** — percentages, delivery counts, SLA figures, and benchmarks require verified operational or customer data
2. **Permissioned narratives** — named quotes, outcome metrics, and Review schema require explicit customer approval
3. **Draft/noindex until reviewed** — use `PublishableContent.status` and `index: false` until content + evidence sign-off
4. **Problem first, technology second** — capacity network positioning; do not overclaim AI/automation ([charter](../docs/PORTERCHAIN_CHARTER.md))
5. **Phase 1 messaging only** — do not publish Phase 3 vision as current capability on customer paths

---

## Placeholder markers

Use explicit markers in source until real data exists:

| Marker                             | Meaning                                               |
| ---------------------------------- | ----------------------------------------------------- |
| `[REQUIRES REAL CUSTOMER METRIC]`  | Outcome number needs verified customer data           |
| `[REQUIRES REAL OPERATIONAL DATA]` | Internal ops/dispatch data not yet aggregated         |
| `[REQUIRES FOUNDER APPROVAL]`      | Strategic or methodology claims need founder sign-off |

Example: `website/src/lib/seo/content/research.ts` — GTA benchmark report scaffold.

**Rule:** Pages with placeholders must remain `status: "draft"` and `index: false`. Do not ship placeholders to indexed production copy.

---

## PublishableContent gates

```typescript
// publishable.ts
(isPublished(content) === content.status) === "published" && content.index;
```

### Workflow

| Status                       | Index allowed | Sitemap  | Schema                |
| ---------------------------- | ------------- | -------- | --------------------- |
| `draft`                      | `false` only  | Excluded | None                  |
| `review`                     | `false` only  | Excluded | None                  |
| `published` + `index: true`  | Yes           | Included | Per type              |
| `published` + `index: false` | No            | Excluded | Optional noindex page |

Optional fields for audit trail:

- `authorId`, `reviewerId`
- `publishedAt`, `updatedAt`
- `sources[]` — URLs or internal doc refs
- `canonicalSlug` — when slug differs from URL

---

## Success stories

**File:** `website/src/lib/seo/content/success-stories.ts`

| Field                        | Policy                                                     |
| ---------------------------- | ---------------------------------------------------------- |
| `quote` / `quoteAttribution` | Anonymized unless customer approves naming                 |
| `outcomeMetric`              | Display + Review schema **only** when `permissioned: true` |
| `authorId`                   | Ops author from blog authors registry for E-E-A-T          |

```typescript
// Review schema gated in page component
permissioned === true → buildReviewSchema()
```

Do not add fabricated distributor names or metrics to fill the array.

---

## Research reports

**File:** `website/src/lib/seo/content/research.ts`

Required before publish:

- Documented `methodology` and `dataSource`
- Verified `sampleSize` and `dateRange`
- Legal/privacy review if customer data aggregated
- Founder approval on `[REQUIRES FOUNDER APPROVAL]` sections

`getIndexableResearchReports()` returns empty until entries pass all gates.

---

## Comparison pages

**File:** `website/src/lib/seo/content/comparison-pages.ts`

- Compare **categories** (in-house fleet, ad hoc courier) — not named competitors
- Claims must reflect actual PorterChain capabilities today
- Run through `verify_marketing_claims.py` in CI

---

## Schema and rich results

| Schema type               | Evidence requirement                               |
| ------------------------- | -------------------------------------------------- |
| `Review`                  | `permissioned: true` on success story              |
| `aggregateRating`         | **Do not use** without third-party verified source |
| `Article` author Person   | Real team member in authors registry               |
| `Organization.knowsAbout` | Approved capability list only                      |
| LocalBusiness hours/phone | Match operational reality + GBP                    |

See [STRUCTURED_DATA_MAP.md](./STRUCTURED_DATA_MAP.md).

---

## Programmatic SEO copy

FR translations in `messages/seo-programmatic-fr.json` must be human-reviewed — not machine-translated placeholders.

EN programmatic copy validated by:

- `verify_programmatic_en_playbook.py`
- `verify_marketing_claims.py`
- `verify_no_false_ai_marketing.py`

---

## Blog and editorial

- Frontmatter dates must reflect actual publish date
- Statistics in blog posts need citation or removal
- Construction/trades posts must align with primary vertical strategy

---

## CI enforcement

```bash
pnpm validate:product-vision   # includes verify_marketing_claims.py
pnpm validate:ai-governance    # verify_no_false_ai_marketing.py
```

Add human review for:

- New success stories
- Trust/legal pages
- Research publication

---

## Violations

If invented metrics ship to production:

1. Set `index: false` immediately
2. Remove or correct copy
3. Request GSC re-crawl
4. Log incident in [WEBSITE_GAP_IMPLEMENTATION_LOG.md](./WEBSITE_GAP_IMPLEMENTATION_LOG.md)

---

## Owner sign-off matrix

| Content type         | Engineering | Content | Legal | Founder      |
| -------------------- | ----------- | ------- | ----- | ------------ |
| Success story metric | —           | ✅      | —     | ✅           |
| Research report      | ✅          | ✅      | ✅    | ✅           |
| Trust/SLA/DPA        | —           | ✅      | ✅    | —            |
| New industry niche   | ✅          | ✅      | —     | Optional     |
| FAQ/guide claim      | —           | ✅      | —     | If strategic |

Deferred items: [DEFERRED_AND_OWNER_INPUT_REQUIRED.md](./DEFERRED_AND_OWNER_INPUT_REQUIRED.md).
