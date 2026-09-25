#!/usr/bin/env bash
# Ads / LinkedIn keyword align checklist (ops — needs Ads Manager login).
set -euo pipefail

cat <<'EOF'
Paid keyword align — Ads / LinkedIn
===================================

1. Regenerate SSOT dump if KEYWORDS changed:
   python3 scripts/export_keywords_paid_align.py
2. Open docs/ops/KEYWORDS_PAID_ALIGN.md
3. Google Ads → active search campaigns → Keywords
   - Keep / add only Primary column terms
   - Pause or remove terms not in the table
4. LinkedIn Campaign Manager → interest / keyword lists
   - Mirror Primary column only (no separate Ads thesaurus)
5. Record align date in the next marketing ops note / PR

SSOT: website/src/lib/seo/seo-content/industries.ts
EOF
