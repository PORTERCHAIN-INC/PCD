# Porterchain Mobile Architecture

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

This document is a compact pointer. The canonical, detailed mobile architecture is:

**[MOBILE_ARCHITECTURE.md](MOBILE_ARCHITECTURE.md)**

---

## Current Status

The June scaffold status is obsolete. As of July 2026:

- `apps/mobile-driver` is a full Expo SDK 57 driver execution app with Clerk login, jobs, navigation, POD, shift, earnings, offline sync, push notifications, support, and SOS.
- `apps/mobile-customer` is a full Expo SDK 57 customer app with Clerk login, quotes, bookings, Stripe hosted checkout, tracking, notifications, support, claims, invoices, and receipts.
- Both apps use shared packages under `shared/` (`@porterchain/mobile-api`, `mobile-security`, `mobile-offline`, `mobile-notifications`, `mobile-performance`, `mobile-ui`, and related packages).
- Both apps call **Porterchain API only**: driver uses `/driver-api/v1/*`; customer uses `/v1/*`.
- Fleetbase remains server-side through the Porterchain API and Fleetbase adapter.

---

## Quick Links

| Document                                                                            | Purpose                                      |
| ----------------------------------------------------------------------------------- | -------------------------------------------- |
| [MOBILE_ARCHITECTURE.md](MOBILE_ARCHITECTURE.md)                                    | Canonical architecture and provider/API maps |
| [MOBILE_ARCHITECTURE.md](MOBILE_ARCHITECTURE.md)                                    | Release readiness, security, and performance |
| [MOBILE_DESIGN_SYSTEM.md](./docs/archive/redundant-2026-08/MOBILE_DESIGN_SYSTEM.md) | Shared tokens and components                 |
| [DRIVER_PLATFORM.md](./DRIVER_PLATFORM.md)                                          | Driver API and service architecture          |

---
