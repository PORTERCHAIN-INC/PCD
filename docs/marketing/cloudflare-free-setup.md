# Cloudflare free plan in front of porterchain.com — steps for Ravi (DNS stays managed at SiteGround until step 6)

Why: the origin (one droplet behind Caddy) slowed to >20 s under ~24 simultaneous uncached requests on Oct 18. Cloudflare caches public pages at the edge and absorbs bursts and bots for free.

1. Sign up at dash.cloudflare.com (free) with admin@porterchain.com. Add site "porterchain.com", choose Free plan.
2. Cloudflare scans existing DNS. Check every record matches SiteGround's zone exactly: apex A, www, api, admin, merchant, driver, customer, accounts/clerk CNAMEs, MX, SPF/DKIM/DMARC TXT, any Shopify/Google verification TXT.
3. Proxy status (orange cloud): ON for porterchain.com and www only, at first. Leave api/admin/merchant/driver/customer and ALL Clerk (clerk., accounts.) and mail records grey (DNS only).
4. SSL/TLS → Full (strict). Edge Certificates → Always Use HTTPS ON, Min TLS 1.2, HSTS: leave as origin already sends it.
5. Caching → Configuration: Browser Cache TTL "Respect existing headers". Rules → Cache Rules → new rule "Public HTML": hostname eq porterchain.com AND URI path does not start with /v1/ , /webhooks/, /internal/, /health, /api/, and path does not contain /login, /book, /track, /email-preferences → Eligible for cache; Edge TTL "Use cache-control header if present" (origin sends s-maxage=60, stale-while-revalidate=300). Security → Bots: Bot Fight Mode ON. Security → WAF → Rate limiting rule (free tier allows 1): path starts with /v1/public/ → 30 requests / 10 s per IP → Block 10 s.
6. Only when steps 2–5 are verified: in SiteGround (Domain → Nameservers) replace the nameservers with the two Cloudflare gives you. Propagation: minutes to 24 h. Keep the SiteGround DNS zone untouched as rollback (switch nameservers back).
7. After switch: check https://porterchain.com/en returns "cf-cache-status: HIT" on the second request; check sign-in on merchant/admin portals, Stripe webhooks (api. grey cloud), email (MX unchanged), Shopify app callbacks.
8. Caddy note: once proxied, set Caddy `trusted_proxies cloudflare` (or static Cloudflare IP list) so logs and rate limits see real client IPs.
   Risks: wrong DNS copy breaks email or sign-in → that's why step 2/3 are explicit and mail/Clerk/api stay grey.
