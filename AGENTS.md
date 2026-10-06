# PorterChain — agent instructions

Navigation sensors are **mandatory**. Full pins: `.cursor/rules/graph-tools.mdc`.

```
mashed-up code
    │ Step 1
GRAPHIFY CLI          → ARCHITECTURE.md + FastAPI↔PHP map
    │ Steps 2–3
CODEGRAPH MCP         → Pydantic / ORM / Valhalla / OSRM extract
    │ Steps 4–6
RIPWIRE CLI           → thin routers, Stripe/Clerk adapters
```

| Moment                      | Tool                          | Do                                                                             |
| --------------------------- | ----------------------------- | ------------------------------------------------------------------------------ |
| A — architecture            | Graphify-Labs/`graphify` CLI  | `graphify query` / `path` / `explain` · then `ARCHITECTURE.md`                 |
| B — schemas & routing       | `@colbymchenry/codegraph` MCP | `codegraph_explore` (do **not** install `codegraph-ai/CodeGraph`)              |
| C — adapters & thin routers | redhat-et/`ripwire` CLI       | `ripwire . --cache=.ripwire --for="…"` / `--callers` / `--expand` / `--impact` |

One sensor per session. `.cursor/mcp.json` holds **CodeGraph only** — never Graphify MCP or Ripwire MCP. Grep/Read only after the sensor named the file.

Stack, charter, and dispatch rules live in `.cursor/rules/`. Dispatch ownership SSOT: [ARCHITECTURE.md](ARCHITECTURE.md) and [.cursor/rules/fleetbase-first-policy.mdc](.cursor/rules/fleetbase-first-policy.mdc) (PorterChain owns execution; Valhalla road cost; no Fleetbase adapter).

## Cursor Cloud specific instructions

- App Node is **24.18.0** at `/usr/local/node` (also linked from `/usr/local/cargo/bin`, which is first on PATH). Python **3.14.6** is the API interpreter in `apps/api/.venv`.
- Install: `bash .cursor/cloud-agent-install.sh`. Boot: `bash .cursor/cloud-agent-start.sh`. That start brings up Postgres 18, Redis 8.8, Mailpit, SpiceDB, the API on `:8001`, and the website on `:3000`.
- `apps/api/.env` is copied from `env/api.env.example` with `CLERK_DEV_BYPASS=true`. Stripe mock stays on. Clerk, Stripe, and Google keys are optional for the local quote path.
- Other portals, when needed: `pnpm dev:merchant` (`:3001`), `pnpm dev:admin` (`:3002`), `pnpm dev:driver` (`:3003`), `pnpm dev:customer` (`:3004`).
- The routing profile stays off. Local quotes use the haversine fallback. `pnpm docker:up:routing` is the optional Valhalla/OSRM path once the GTA extract exists.
- Hello-world: `GET http://127.0.0.1:8001/health/ready`, `GET /v1/booking-catalog`, then `POST /v1/quotes/preview`. Website: `http://127.0.0.1:3000`.

## Local before production

Test on this Mac, then build the touched images locally, then push and start CI/CD. Deploy builds the pushed commit, not the working tree. Full order: `.cursor/rules/local-before-production.mdc`.
