# Website (path alias)

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

The public marketing and booking website lives at:

**[../../website/](../../website/)**

| Item               | Value                                                |
| ------------------ | ---------------------------------------------------- |
| **Canonical path** | `website/` (repo root)                               |
| **Package**        | `@porterchain/website`                               |
| **Port**           | **3000** (`pnpm dev:website`)                        |
| **API**            | Porterchain API `:8001` — quotes, bookings, tracking |

This `apps/website/` directory is a documentation alias only — the Next.js app is in `website/`.

---

## Quick Start

```bash
cp env/website.env.example website/.env.local
pnpm dev:website
```

Open [http://localhost:3000](http://localhost:3000).

---

## Key Routes (under `[locale]`)

| Route                               | Purpose                                           |
| ----------------------------------- | ------------------------------------------------- |
| `/`                                 | Marketing home                                    |
| `/book/continue`, `/book/success`   | Retail booking flow                               |
| `/track/[tracking]`                 | Public shipment tracking                          |
| `/portal/customer`                  | Customer portal entry (standalone app at `:3004`) |
| `/blog/*`                           | Content marketing                                 |
| `/business`, `/company`, `/contact` | Marketing pages                                   |

i18n: `next-intl` with locale prefix (e.g. `/en/`, `/fr/`).

---

## Related Documents

| Document                                                                           | Purpose                                                     |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| [../../website/README.md](../../website/README.md)                                 | App-local readme (update when migrating to `apps/website/`) |
| [../../USER_JOURNEYS.md](../../USER_JOURNEYS.md)                                   | Customer journeys                                           |
| [../../docs/architecture/BOOKING_FLOW.md](../../docs/architecture/BOOKING_FLOW.md) | Booking architecture                                        |

---
