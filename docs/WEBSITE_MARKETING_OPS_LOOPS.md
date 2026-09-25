# Website marketing analytics + keyword loops (ops)

#

# These need live Google / Ads / Cloudflare credentials. Repo SSOT ownership:

# KEYWORDS → website/src/lib/seo/seo-content/industries.ts (KEYWORDS map)

# CTA north star → common.cta.quote + GA4 events cta_click → quote_request

# Lead → API LeadIngest (existing pixels/CMP already on website)

#

# Printable checklists (run any to print steps):

# bash infrastructure/deploy/scripts/gsc-keyword-loop-checklist.sh

# bash infrastructure/deploy/scripts/ga4-quote-funnel-checklist.sh

# bash infrastructure/deploy/scripts/paid-keyword-align-checklist.sh

# bash infrastructure/deploy/scripts/cloudflare-html-cache-checklist.sh

# bash infrastructure/deploy/scripts/r2-blog-media-checklist.sh

## GSC keyword loop (monthly)

Checklist: `infrastructure/deploy/scripts/gsc-keyword-loop-checklist.sh`

1. Search Console → porterchain.com → Performance → last 28 days
2. Export Queries + Pages (CSV)
3. Promote queries with impressions ≥ 50 and CTR above site median into
   `KEYWORDS` niches in `website/src/lib/seo/seo-content/industries.ts`
4. Demote / noindex matrix URLs with 0 impressions for 90 days (draft niches stay noindex)
5. `python3 scripts/export_keywords_paid_align.py` then commit with pull date in PR

## GA4 quote funnel

Checklist: `infrastructure/deploy/scripts/ga4-quote-funnel-checklist.sh`

North-star path (do not invent a second analytics product):

`cta_click` → `quote_request` → LeadIngest → won merchant

**Code (done):** website fires both events on primary quote paths:

- Business `QuoteSignupPanel` + `StickyCta` (Clerk quote sign-up)
- Capacity guide `capture_contact` success
- Contact form when `inquiry_type=sales`

1. GA4 → Explore → Funnel exploration with those event names
2. Confirm DebugView after clicking Get a quote on `/en/business`
3. Mark conversions from `GA4_CONVERSION_EVENTS` (`website/src/lib/seo/analytics.ts`)
4. Bookmark Explore as "Quote funnel" for monthly founder review

## Paid keyword align

Checklist: `infrastructure/deploy/scripts/paid-keyword-align-checklist.sh`  
Dump: `docs/ops/KEYWORDS_PAID_ALIGN.md` (`python3 scripts/export_keywords_paid_align.py`)

1. Google Ads + LinkedIn: pull active keyword / interest lists
2. Diff against KEYWORDS primaries — remove terms not in SSOT; add missing primaries only
3. No separate “Ads thesaurus”; paid mirrors organic SSOT

## Cloudflare HTML cache

**Status:** prod is origin Caddy (`via: 1.1 Caddy`, no `cf-cache-status`). Origin already sends `s-maxage` HTML headers. CF edge rules need orange-cloud DNS first.

Checklist: `infrastructure/deploy/scripts/cloudflare-html-cache-checklist.sh`  
Verify: `bash scripts/verify_website_cf_cache.sh`

## R2 blog media (optional CDN)

**Status:** Doppler `pcd/prd` has `WEBSITE_REVALIDATE_SECRET` + empty `BLOG_MEDIA_*` placeholders (scaffold done). Local disk is the intentional default until a bucket exists.

Checklist: `infrastructure/deploy/scripts/r2-blog-media-checklist.sh`  
Upload helper: `infrastructure/deploy/scripts/upload-blog-to-doppler.sh`  
Playbook: `docs/WEBSITE_PAGE_PLAYBOOK.md` § Blog media
