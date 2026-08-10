<!-- BEGIN:nextjs-agent-rules -->

**Type:** CANONICAL
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-08-08

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

<!-- END:nextjs-agent-rules -->

# Porterchain Website — Agent Rules

Rules for AI agents and contributors editing `website/`.

---

## Scope

This app is the **public marketing site** only. It is **not** the admin, merchant, driver, or customer portals (those live under `apps/`).

**Retail quote / book / pay:** `apps/customer` (:3004) only. Do **not** reintroduce a booking wizard, `POST /v1/quotes` from the website UI, or `/api/quote` on this app.

---

## Hard Rules (masterrule)

1. **No Fleetbase** — never call Fleetbase HTTP from this app. Use Porterchain API (`/v1/*`) only when needed (e.g. guest track).
2. **No website booking** — capacity CTAs → `/sign-up?intent=quote` → customer portal. Legacy `/book*` = redirect to portal only.
3. **Clerk only** — Platform Clerk for login/sign-up CTAs. Authenticated retail booking is on the customer portal.
4. **i18n required** — all user-facing routes live under `[locale]` (`en`, `fr`). Update `messages/en.json` and `messages/fr.json` together.
5. **Do not modify** `apps/fleetbase/**` (upstream vendor).

---

## Stack

| Tech       | Notes                                         |
| ---------- | --------------------------------------------- |
| Next.js 16 | App Router, `output: "standalone"`            |
| React 19   |                                               |
| next-intl  | Locale routing in `src/i18n/`                 |
| Clerk      | `@clerk/nextjs` via `AppClerkProvider`        |
| Maps       | `@porterchain/maps` for **public track** only |
| Env        | `@porterchain/config/monorepo-env.mjs`        |

---

## Key Paths

| Path                                    | Purpose                                 |
| --------------------------------------- | --------------------------------------- |
| `src/app/[locale]/`                     | Pages                                   |
| `src/lib/api.ts`, `src/lib/api-base.ts` | Guest track API client only             |
| `src/data/portal-links.ts`              | Links to customer/merchant/admin/driver |
| `content/blog/{en,fr}/`                 | Blog markdown                           |
| `messages/{en,fr}.json`                 | i18n strings                            |

---

## Capacity CTA Flow (not on-site booking)

1. Marketing CTA → `/sign-up?intent=quote&from=…`
2. After Platform Clerk → customer portal `/book`
3. Do **not** add `BookingWidget`, quote engine, or booking-draft clients here

---

## When Editing

- Match existing component patterns in `src/components/`.
- Prefer `@porterchain/maps` over ad-hoc Google Maps setup (track only).
- Blog posts: frontmatter in `content/blog/`; do not break slug URLs without redirects.
- Run `pnpm --filter @porterchain/website lint` after TS changes.
- Production build: `pnpm --filter @porterchain/website build`.

---

## Related Docs

- [README.md](./README.md)
- [../apps/customer/README.md](../apps/customer/README.md)
- [../docs/PORTERCHAIN_CHARTER.md](../docs/PORTERCHAIN_CHARTER.md)
