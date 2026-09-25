#!/usr/bin/env bash
# GA4 quote funnel checklist (ops — needs GA4 Admin login).
# Website already fires cta_click → quote_request on primary quote paths.
set -euo pipefail

cat <<'EOF'
GA4 quote funnel — Explore bookmark
===================================

North star: cta_click → quote_request → LeadIngest → won merchant

1. GA4 → Explore → Funnel exploration
   Steps: cta_click → quote_request → (optional) business_inquiry_submit
2. Confirm Realtime / DebugView shows events after clicking Get a quote on /en/business
3. Admin → Events → Mark as conversions (from website/src/lib/seo/analytics.ts GA4_CONVERSION_EVENTS):
   - quote_request
   - contact_form_submit_success
   - business_inquiry_submit
   - booking_quote_success (when portal fires it)
4. Save Explore as "Quote funnel" → share with founder monthly review
5. Do not invent a second analytics product

Code paths already wired:
- QuoteSignupPanel + StickyCta
- Capacity guide capture_contact
- Contact form (inquiry_type=sales)
EOF
