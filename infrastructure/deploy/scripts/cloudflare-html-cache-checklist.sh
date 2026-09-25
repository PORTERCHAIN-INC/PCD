#!/usr/bin/env bash
# Cloudflare HTML edge-cache checklist for marketing/blog (ops — no API keys in repo).
# Run after DNS/proxy is on Cloudflare for porterchain.com.
set -euo pipefail

cat <<'EOF'
Cloudflare HTML cache — marketing / blog
========================================

Goal: edge HIT on public HTML; bypass dynamic quote/book/auth paths.

0. Prerequisite (required): DNS for porterchain.com / www must be
   Proxied (orange cloud) through Cloudflare. Today prod responds
   `via: 1.1 Caddy` with no `cf-cache-status` — origin Caddy already sets
   s-maxage HTML headers. Skip this checklist until orange-cloud is on.

1. Dashboard → porterchain.com → Caching → Cache Rules (or Configuration Rules)
2. Create rule "Marketing HTML cache":
   - If: Hostname is porterchain.com (and www) AND URI Path does not start with
     /api/ OR /book OR /track OR /sign-in OR /sign-up OR /admin
   - Then: Eligible for cache + Edge TTL = 2 hours (or respect origin Cache-Control)
3. Create rule "Blog ISR respect":
   - If: URI Path contains /blog
   - Then: Cache everything + Edge TTL = 30 minutes (website uses tagged revalidate)
4. Bypass rule (higher priority):
   - If: URI Path starts with /api/ OR Cookie contains __session (Clerk)
   - Then: Bypass cache
5. Verify:
   bash scripts/verify_website_cf_cache.sh
   # Expect cf-cache-status present (HIT on second request)
6. After admin blog publish, confirm revalidate still busts: open post URL, edit title, save,
   hard-refresh — new title without waiting for Edge TTL.

Do not cache authenticated portal hosts (admin/merchant/driver/customer apps).
EOF
