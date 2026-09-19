---
name: porterchain-graph-tools
description: Mandatory Graphify → CodeGraph → Ripwire navigation for PorterChain. Use when locating code, mapping architecture, extracting Pydantic/ORM/Valhalla/OSRM, or editing thin routers and Stripe/Clerk/Fleetbase adapters. Do not grep the monorepo first.
---

# PorterChain graph-tool flow

Follow `.cursor/rules/graph-tools.mdc`. One sensor per session.

| Moment | When                                                              | Tool                                                                           |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| A      | Mash-ups, “where does X live”, FastAPI ↔ Fleetbase PHP, god nodes | `graphify` CLI · then `ARCHITECTURE.md`                                        |
| B      | Pydantic/ORM extract, Maps/OSRM/Valhalla/Vroom                    | CodeGraph MCP `codegraph_explore` (`@colbymchenry/codegraph`)                  |
| C      | Thin routers, Stripe/Clerk adapters, portal/client views          | `ripwire . --cache=.ripwire --for="…"` / `--callers` / `--expand` / `--impact` |

Do not install `codegraph-ai/CodeGraph`. Do not add Graphify or Ripwire MCP. Grep/Read only after the moment’s sensor named the file.
