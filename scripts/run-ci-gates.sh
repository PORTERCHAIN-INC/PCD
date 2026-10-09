#!/usr/bin/env bash
# Ordered static gates for GitHub Actions CI (pnpm validate:ci).
# Keep lint / format / lockfiles / build as separate CI steps for clearer failures.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

run() {
  echo "::group::$1"
  shift
  "$@"
  echo "::endgroup::"
}

run "D2 contracts" pnpm validate:d2
run "D3 Phase 1 matrix" pnpm validate:d3
run "List pagination" pnpm validate:pagination
run "Router audit" pnpm validate:router-audit
run "Architecture boundaries" pnpm validate:architecture
run "Golden rules" pnpm validate:golden-rules
run "Observability" pnpm validate:observability
run "Notifications + billing" pnpm validate:notifications-billing
run "Enterprise security" pnpm validate:enterprise-security
run "Deploy plan" pnpm validate:deploy-plan
run "Enterprise identity" pnpm validate:enterprise-identity
run "Doc governance" pnpm validate:doc-governance
run "Phase 2 scaffold" pnpm validate:phase2-scaffold
run "Investor + monopoly" pnpm validate:investor-monopoly
run "Integration adapter" pnpm validate:integration-adapter
run "POD media" pnpm validate:pod-media
run "Mobile appendix" pnpm validate:mobile-appendix
run "Mobile Maestro smoke" pnpm validate:mobile-smoke
run "Mobile design" pnpm validate:mobile-design
run "Portal UX" pnpm validate:portal-ux
run "Tracking maps" pnpm validate:tracking-maps
run "Admin tablet" pnpm validate:admin-tablet
run "Booking a11y" pnpm validate:booking-a11y
run "Design" pnpm validate:design
run "Developer portal" pnpm validate:developer-portal
# Sitemap manifest freshness + single-hop redirect / no-chain contract (GSC clean-up).
run "Website SEO" pnpm validate:website-seo
run "Customer Stripe return" pnpm validate:customer-stripe-return
run "Product vision" pnpm validate:product-vision
run "AI governance" pnpm validate:ai-governance
run "Construction site access" pnpm validate:construction-site-access
run "Liftgate pricing" pnpm validate:liftgate-pricing
run "Vertical onboarding" pnpm validate:vertical-onboarding
run "Medical / food verticals" pnpm validate:medical-food-verticals
run "Integration marketplace" pnpm validate:integration-marketplace
run "Phase 2 flags" pnpm validate:phase2-flags
run "OAuth" pnpm validate:oauth

echo "CI gates passed"
