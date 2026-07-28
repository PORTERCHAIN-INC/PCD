# Deferred and Owner Input Required

**Last updated:** 2026-07-22  
**Audit:** [PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md §17](./PORTERCHAIN_WEBSITE_AUTHORITY_AUDIT.md#17-content-gaps)  
**Evidence policy:** [CONTENT_EVIDENCE_POLICY.md](./CONTENT_EVIDENCE_POLICY.md)  
**Implementation log:** [WEBSITE_GAP_IMPLEMENTATION_LOG.md](./WEBSITE_GAP_IMPLEMENTATION_LOG.md)

---

## Purpose

Track website authority/SEO work that **cannot ship** without legal, founder, or content owner approval. Prevents accidental indexation of draft claims or non-compliant pages.

Classification tag for all items below: **Deferred** unless noted.

---

## Legal / trust pages

| Item                        | Route / file                                                               | Blocker                                                                | Owner               |
| --------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------- |
| Trust center copy refresh   | `/trust`, `/trust/sla`, `/trust/dpa`, `/trust/msa`, `/trust/subprocessors` | Legal review of SLA commitments, DPA terms, subprocessor list accuracy | Legal               |
| Privacy policy updates      | `/privacy`                                                                 | Privacy counsel — data processing descriptions, cookies                | Legal               |
| Terms of service            | `/terms`                                                                   | Contract language approval                                             | Legal               |
| Cookie policy vs CMP        | `/cookies`                                                                 | Policy must match actual tracking once CMP live                        | Legal + Engineering |
| Cookie consent banner (CMP) | Site-wide                                                                  | Vendor selection, consent mode v2, GA4/Zoho integration                | Legal + Engineering |

**Current state:** Legal pages exist and are in sitemap at low priority (`static` partition). Subprocessors/MSA/DPA routes live under `/trust/*` — verify copy matches production contracts before marketing push.

**Do not:** Add marketing claims to trust pages without legal redline.

---

## Content expansion gates

| Item                                                                                   | Module                                                      | Blocker                                                            | Owner             |
| -------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------ | ----------------- |
| Draft industry niches (HVAC, automotive, manufacturing, retail, food)                  | `draft-expansions.ts` + `nicheLanding` stubs                | Routes live **noindex**; full copy + ops verification before index | Founder + Content |
| Draft GTA boroughs (Richmond Hill, Scarborough, Etobicoke, North York, Milton, Whitby) | `SERVICE_AREA_SLUGS` not in CORE                            | Pages render; stay out of sitemap until CORE promotion             | Ops + Content     |
| GTA delivery benchmark report                                                          | `content/research.ts`                                       | `[REQUIRES REAL OPERATIONAL DATA]` — no aggregate metrics yet      | Founder + Ops     |
| Additional success stories with metrics                                                | `content/success-stories.ts`                                | Customer permission + `permissioned: true`                         | Sales + Content   |
| Named customer logos / quotes                                                          | Success stories, home testimonials                          | Trademark + publicity rights                                       | Legal + Customer  |
| FR compare/guides/FAQ slugs                                                            | `messages/seo-programmatic-fr.json`                         | Professional FR translation + review                               | Content/i18n      |
| FR service area hub                                                                    | `/fr/service-areas`                                         | Excluded from sitemap — needs FR body                              | Content/i18n      |
| Promote draft niches to index                                                          | Remove from `DRAFT_NICHE_SLUGS` + complete publishable copy | IA + charter review — 10-customer test                             | Founder           |

---

## E-E-A-T and claims

| Item                                   | Blocker                                               | Owner                 |
| -------------------------------------- | ----------------------------------------------------- | --------------------- |
| Aggregate rating schema                | No third-party verified review source                 | Deferred indefinitely |
| “AI-powered” marketing claims          | Must pass `verify_no_false_ai_marketing.py` + founder | Founder               |
| Delivery SLA numbers in public copy    | Must match operational reality + trust SLA page       | Ops + Legal           |
| Pharmacy/medical compliance statements | Regulated vertical — legal review                     | Legal                 |

---

## Product / engineering deferrals

| Item                                    | Notes                                                                 | Owner               |
| --------------------------------------- | --------------------------------------------------------------------- | ------------------- |
| Interactive quote/vehicle calculators   | Research hub + PostalCoverageChecker exist; full calculators deferred | Product             |
| Public `status.porterchain.com` UI      | Health endpoints + STATUS_PAGE.md; Phase 2 UI                         | Engineering         |
| Official SDKs                           | OpenAPI + Postman + generation guidance shipped                       | Engineering         |
| Cookie consent CMP                      | Policy page only                                                      | Legal + Engineering |
| IndexNow / Bing instant indexing        | Not configured                                                        | Engineering         |
| hreflang for future locales             | Only `en` + `fr` today                                                | Engineering         |
| FR translations for new guides/compares | EN indexes; FR 404 until seo-programmatic-fr entries                  | Content/i18n        |

---

## Cookie banner (detailed)

**Status:** Missing — **Partial** policy page only

Requirements before implementation:

1. Legal selects CMP (Cookiebot, OneTrust, or lightweight custom)
2. Inventory all cookies: GA4, Zoho SalesIQ, Clerk (auth routes), maps
3. Implement consent mode — block non-essential scripts until consent
4. Update `/cookies` to match categories
5. FR translation of banner strings
6. Do not block essential booking/API cookies on marketing pages

**Do not** add a cosmetic banner that does not gate scripts — creates compliance liability.

---

## Owner input checklist

Copy this section into a ticket when requesting sign-off:

```markdown
### Request

- [ ] Page/module:
- [ ] Change summary:
- [ ] Evidence attached (data source, customer email, legal doc version):

### Approvals needed

- [ ] Legal (trust/privacy/regulated vertical)
- [ ] Founder (strategy, metrics, new routes)
- [ ] Content (copy quality, FR parity)
- [ ] Ops (SLA/operational claims)

### Indexation

- [ ] Ready for index (status: published, index: true)
- [ ] Stay noindex until: ___
```

---

## When approved

1. Update content module — set `status: "published"`, `index: true` where appropriate
2. Add FR slug to `seo-programmatic-fr.json` if programmatic
3. Run `pnpm validate:product-vision` + evidence review
4. Log in [WEBSITE_GAP_IMPLEMENTATION_LOG.md](./WEBSITE_GAP_IMPLEMENTATION_LOG.md)
5. Resubmit sitemap if large batch of new URLs

---

## Related deferred docs (platform, not website-only)

- Enterprise security/compliance dossiers — `validate:compliance-dossier`
- Investor metrics — separate from public website claims

Website agents should **not** pull investor metrics into indexed marketing copy without founder approval.
