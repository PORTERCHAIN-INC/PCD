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

Stack, charter, and Fleetbase-first rules live in `.cursor/rules/`. PorterChain↔Fleetbase permanent bond SSOT: [docs/FLEETBASE_PERMANENT_BOND.md](docs/FLEETBASE_PERMANENT_BOND.md).

## Local before production

Test on this Mac, then build the touched images locally, then push and start CI/CD. Deploy builds the pushed commit, not the working tree. Full order: `.cursor/rules/local-before-production.mdc`.
