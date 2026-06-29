# Porterchain Driver Platform

Web dashboard and mobile API for vetted driver partners.

| App | Path | Port |
|-----|------|------|
| **Driver portal (web)** | `apps/driver-portal/` | 3003 |
| **Mobile (planned)** | `apps/mobile-driver/` | Expo |

## API

- Base: `/driver-api/v1/*`
- Auth: Porterchain JWT (`POST /driver-api/v1/auth/login`)
- Docs: [DRIVER_PLATFORM.md](../../DRIVER_PLATFORM.md)

## Dev

```bash
pnpm dev:api      # API :8001
pnpm dev:driver   # Portal :3003
```

Fleetbase is **not replaced** — Porterchain extends it via the Fleetbase adapter for GPS, dispatch, and POD sync.
