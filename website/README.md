# Porterchain Website

**Type:** README
**masterrule:** [§21](../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-08-08

Public marketing site. Retail **quote/book** is the **customer portal** (`apps/customer`, :3004) — not this app. Next.js 16 with `next-intl` (EN/FR).

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
Website (:3000)  →  marketing + CTA → Platform Clerk sign-up
                 →  customer portal (:3004) for quote / book / pay
                 →  guest track via Porterchain API (:8001)
```

- **No website booking wizard** — legacy `/book*` routes redirect to the customer portal.
- **No direct Fleetbase** from the website.
- Capacity CTAs use `/sign-up?intent=quote` → customer portal `/book`.

Env loading: `@porterchain/config/monorepo-env.mjs` reads `env/.env` in `next.config.ts`.

---

## Project Layout

```
website/
├── src/app/[locale]/     # Localized App Router pages
├── src/components/       # Marketing UI, track, blog
├── src/lib/              # API (track), maps helpers
├── content/blog/         # Markdown posts (en/, fr/)
├── messages/             # next-intl strings (en.json, fr.json)
├── Dockerfile            # Production image
├── AGENTS.md             # AI agent rules for this app
└── CLAUDE.md             # Pointer to AGENTS.md
```

---

## Key Routes

All routes under `[locale]` (e.g. `/en/`, `/fr/`):

| Route                                           | Purpose                                                  |
| ----------------------------------------------- | -------------------------------------------------------- |
| `/`                                             | Home                                                     |
| `/book`, `/book/continue`, `/book/success`      | **Redirect only** → customer portal book                 |
| `/quote`                                        | Redirect → `/sign-up?intent=quote`                       |
| `/track/[tracking]`                             | Public guest tracking                                    |
| Customer portal                                 | `apps/customer` (`:3004`) — sole retail book/pay surface |
| `/login`, `/sign-up`                            | Platform Clerk                                           |
| `/blog`, `/blog/[slug]`                         | Blog                                                     |
| `/business`, `/company`, `/contact`, `/careers` | Marketing                                                |
| `/privacy`, `/terms`, `/cookies`                | Legal                                                    |

Legacy paths `/platform`, `/overview`, `/solutions` redirect to `/business`.

---

## Environment

Copy from `env/website.env.example`:

| Variable                            | Purpose                      |
| ----------------------------------- | ---------------------------- |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL`   | API base (guest track)       |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Platform Clerk sign-up/login |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`   | Maps on public tracking      |

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
| [../docs/architecture/BOOKING_FLOW.md](../docs/architecture/BOOKING_FLOW.md) | Booking flow (portal)   |
| [../apps/customer/README.md](../apps/customer/README.md)                     | Customer portal (:3004) |
| [../infrastructure/deploy/README.md](../infrastructure/deploy/README.md)     | Production deploy       |
| [../docs/PORTERCHAIN_CHARTER.md](../docs/PORTERCHAIN_CHARTER.md)             | Product charter         |

---
