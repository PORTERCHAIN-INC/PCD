# Caddy changes for porterchain.com (Oct 2026)

File: `infrastructure/deploy/Caddyfile`, `porterchain.com` block. Not deployed by this PR.

## 1. Permanent root redirect (in this PR)

Before: `/` returned a 307 from the Next.js middleware, then `/en`. After: one permanent hop at the edge.

```
@root path /
redir @root /en{?query} 308
```

`{?query}` carries UTM / gclid parameters. Validated with `caddy adapt` (caddy:2.11.4-alpine).

## 2. Removed and retired pages

These are handled in the app (`website/src/lib/seo/redirects.ts`, `focusConsolidationRedirects`) as single-hop 301s, so they are covered by the url-policy tests in CI. No Caddy rules are needed for them.

## 3. Caching

HTML already sends `public, max-age=0, s-maxage=60, stale-while-revalidate=300`; `/_next/static` is immutable for a year; media is a week. Keep these. Cloudflare honours them once it is in front (see `cloudflare-free-setup.md`). Caddy has no response cache without a custom image plugin; not worth it.

## 4. Rate safety

Nothing built in. Use the Cloudflare free-plan rate-limiting rule (see `cloudflare-free-setup.md`).

## Deploy checklist (for Ravi)

1. Merge the PR.
2. Deploy as usual. Caddy reloads with the new Caddyfile.
3. Check: `curl -sI https://porterchain.com/` shows `308` and `location: /en`.
