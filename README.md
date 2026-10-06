# PorterChain

Transportation Capacity Network. Customers pay for capacity (vehicle + driver). Software is the engine, not the SKU.

**Living map:** [ARCHITECTURE.md](ARCHITECTURE.md) · [docs/PORTERCHAIN_CHARTER.md](docs/PORTERCHAIN_CHARTER.md)

## Run locally

```bash
pnpm install
pnpm docker:up
pnpm db:migrate
pnpm dev:api          # FastAPI :8001
pnpm dev:website      # :3000
pnpm dev:merchant     # :3001
pnpm dev:admin        # :3002
```

Routing tiles (GTA ±150 km): `pnpm docker:up:routing` (Valhalla `:8002`, OSRM `:5000`). Day plan: OR-Tools in `dispatch_engine` (no VROOM, no vendor console).

Partner API: [docs/api/PARTNER_GUIDE.md](docs/api/PARTNER_GUIDE.md). OpenAPI snapshot: `pnpm docs:openapi`.

Do not restore `masterrule.md`, `core/`, `backend/`, or `personas/`. Folder law is in ARCHITECTURE.md.
