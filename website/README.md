# Porterchain Website

**Type:** README
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Public marketing site and retail booking funnel. Next.js 16 with `next-intl` (EN/FR).

| Item        | Value                                  |
| ----------- | -------------------------------------- |
| **Package** | `@porterchain/website`                 |
| **Port**    | **3000**                               |
| **Path**    | `website/` (pnpm workspace root entry) |
| **Output**  | `standalone` (Docker production build) |

> Path alias doc: [../apps/website/README.md](../apps/website/README.md)

---

## Setup

```bash
cp env/website.env.example website/.env.local
pnpm dev:website
```

Open [http://localhost:3000](http://localhost:3000) (locales: `/en/`, `/fr/`).

---

## Architecture

```
Website (:3000)
    ↓ Clerk (optional) + Porterchain API calls
Porterchain API (:8001) /v1/*
    ↓
booking_engine, quotes, orders, Stripe webhooks
```

- **No direct Fleetbase** from the website.
- **Pricing display** may use client-side estimate helpers; authoritative quotes come from `POST /v1/quotes`.
- **Server quote proxy:** `website/src/app/api/quote/route.ts` (geocoding with server Maps key when configured).

Env loading: `@porterchain/config/monorepo-env.mjs` reads `env/.env` in `next.config.ts`.

---

## Project Layout

```
website/
├── src/app/[locale]/     # Localized App Router pages
├── src/components/       # UI sections, booking, blog, portal
├── src/lib/              # API client, quote engine, maps helpers
├── content/blog/         # Markdown posts (en/, fr/)
├── messages/             # next-intl strings (en.json, fr.json)
├── Dockerfile            # Production image
├── AGENTS.md             # AI agent rules for this app
└── CLAUDE.md             # Pointer to AGENTS.md
```

---

## Key Routes

All routes under `[locale]` (e.g. `/en/`, `/fr/`):

| Route                                           | Purpose                                                              |
| ----------------------------------------------- | -------------------------------------------------------------------- |
| `/`                                             | Home                                                                 |
| `/book/continue`                                | Booking wizard continuation                                          |
| `/book/success`                                 | Post-checkout confirmation                                           |
| `/track/[tracking]`                             | Public tracking                                                      |
| Customer portal                                 | External link to `apps/customer` (`:3004`) — not embedded on website |
| `/login`                                        | Clerk sign-in                                                        |
| `/blog`, `/blog/[slug]`                         | Blog (24 posts EN+FR)                                                |
| `/business`, `/company`, `/contact`, `/careers` | Marketing                                                            |
| `/privacy`, `/terms`, `/cookies`                | Legal                                                                |

Legacy paths `/platform`, `/overview`, `/solutions` redirect to `/business`.

---

## Environment

Copy from `env/website.env.example`:

| Variable                            | Purpose                                 |
| ----------------------------------- | --------------------------------------- |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`   | API base                                |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk (booking/account)                 |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`   | Maps on booking/tracking                |
| `GOOGLE_MAPS_SERVER_API_KEY`        | Server geocoding in `/api/quote` (prod) |

Portal URL hints are injected in `next.config.ts` for admin, merchant, driver, customer links.

See [ENVIRONMENT_VARIABLES.md](../ENVIRONMENT_VARIABLES.md).

---

## Agent / IDE Docs

| File                     | Purpose                              |
| ------------------------ | ------------------------------------ |
| [AGENTS.md](./AGENTS.md) | Rules for AI agents editing this app |
| [CLAUDE.md](./CLAUDE.md) | Claude pointer to AGENTS.md          |

---

## Related Documents

| Document                                                                     | Purpose                 |
| ---------------------------------------------------------------------------- | ----------------------- |
| [../docs/architecture/BOOKING_FLOW.md](../docs/architecture/BOOKING_FLOW.md) | Booking flow            |
| [../apps/customer/README.md](../apps/customer/README.md)                     | Customer portal (:3004) |
| [../infrastructure/deploy/README.md](../infrastructure/deploy/README.md)     | Production deploy       |
| [../PRODUCT_REQUIREMENTS.md](../PRODUCT_REQUIREMENTS.md)                     | Product scope           |

---

## Governance

| Document                                                 | Role              |
| -------------------------------------------------------- | ----------------- |
| [../masterrule.md](../masterrule.md)                     | Architecture SSOT |
| [../REPOSITORY_STRUCTURE.md](../REPOSITORY_STRUCTURE.md) | Monorepo layout   |
