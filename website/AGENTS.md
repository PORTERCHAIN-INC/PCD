<!-- BEGIN:nextjs-agent-rules -->

**Type:** CANONICAL
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

<!-- END:nextjs-agent-rules -->

# Porterchain Website — Agent Rules

Rules for AI agents and contributors editing `website/`.

---

## Scope

This app is the **public marketing site + retail booking funnel** only. It is **not** the admin, merchant, driver, or customer portals (those live under `apps/`).

---

## Hard Rules (masterrule)

1. **No Fleetbase** — never call Fleetbase HTTP from this app. Use Porterchain API (`/v1/*`) only.
2. **No business logic duplication** — authoritative quotes, bookings, and payments are decided by `apps/api`. Client code validates UX; server decides outcomes.
3. **Clerk only** — no legacy auth. Public flows may be anonymous; authenticated flows use Clerk.
4. **i18n required** — all user-facing routes live under `[locale]` (`en`, `fr`). Update `messages/en.json` and `messages/fr.json` together.
5. **Do not modify** `apps/fleetbase/**` (upstream vendor).

---

## Stack

| Tech       | Notes                                             |
| ---------- | ------------------------------------------------- |
| Next.js 16 | App Router, `output: "standalone"`                |
| React 19   |                                                   |
| next-intl  | Locale routing in `src/i18n/`                     |
| Clerk      | `@clerk/nextjs` via `AppClerkProvider`            |
| Maps       | `@porterchain/maps` + `@vis.gl/react-google-maps` |
| Env        | `@porterchain/config/monorepo-env.mjs`            |

---

## Key Paths

| Path                                    | Purpose                         |
| --------------------------------------- | ------------------------------- |
| `src/app/[locale]/`                     | Pages                           |
| `src/lib/api.ts`, `src/lib/api-base.ts` | Porterchain API client          |
| `src/app/api/quote/route.ts`            | Server-side quote/geocode proxy |
| `content/blog/{en,fr}/`                 | Blog markdown                   |
| `messages/{en,fr}.json`                 | i18n strings                    |
| `src/data/portal-links.ts`              | Links to other portals          |

---

## Booking Flow

1. User completes booking widget → `POST /v1/quotes` (or draft via `/v1/booking-drafts`)
2. Authenticated checkout → `POST /v1/bookings` → Stripe hosted URL
3. Confirmation via server webhook — poll `GET /v1/bookings/confirmation`
4. Do **not** add client-side "I've paid" bypasses

---

## When Editing

- Match existing component patterns in `src/components/`.
- Prefer `@porterchain/maps` over ad-hoc Google Maps setup.
- Blog posts: frontmatter in `content/blog/`; do not break slug URLs without redirects.
- Run `pnpm --filter @porterchain/website lint` after TS changes.
- Production build: `pnpm --filter @porterchain/website build`.

---

## Related Docs

- [README.md](./README.md) — setup and routes
- [../masterrule.md](../masterrule.md) — platform rules
- [../docs/architecture/BOOKING_FLOW.md](../docs/architecture/BOOKING_FLOW.md)

---

## Governance

| Document                                      | Role              |
| --------------------------------------------- | ----------------- |
| [masterrule.md](../masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../CTO_AUDIT_REPORT.md) | Doc vs code audit |
