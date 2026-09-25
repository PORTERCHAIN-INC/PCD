#!/usr/bin/env bash
# GSC → KEYWORDS monthly loop checklist (ops — needs Search Console login).
set -euo pipefail

cat <<'EOF'
GSC keyword loop — monthly
==========================

1. Google Search Console → property porterchain.com → Performance
2. Date range: last 28 days
3. Export Queries + Pages (CSV)
4. Promote into KEYWORDS when impressions ≥ 50 and CTR ≥ site median:
   Edit: website/src/lib/seo/seo-content/industries.ts (`KEYWORDS`)
5. Demote / keep draft (noindex) niches with 0 impressions for 90 days
6. Regenerate paid-align dump:
   python3 scripts/export_keywords_paid_align.py
7. Commit KEYWORDS + docs/ops/KEYWORDS_PAID_ALIGN.md together; note pull date in PR body

SSOT ownership: docs/WEBSITE_MARKETING_OPS_LOOPS.md
EOF
