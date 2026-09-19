# PorterChain ↔ Fleetbase permanent bond

**Type:** CANONICAL · **Verified:** 2026-09-17  
**Related:** [ARCHITECTURE.md](../ARCHITECTURE.md) · [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md) · [docs/PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) · `.cursor/rules/fleetbase-first-policy.mdc`

This is the SSOT for how PorterChain and Fleetbase stay connected. Treat Fleetbase as a **bonded capability**, not a fork, not a second product surface, and not something portals talk to directly.

---

## One-sentence model

**Identity (company UUID + API key) + contract (`fleetbase-adapter`) + resilience (circuit + RetryQueue) + self-heal (`pnpm fleetbase:bond`) = the permanent bond.**

Fleetbase files stay upstream under `apps/fleetbase/` (AGPL vendor). PorterChain never absorbs or patches them for product features. The bond is the wire, not a copy of the tree.

---

## What “bonded” means

| Layer          | Meaning                                                                                  | Where it lives                                                                                                                         |
| -------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Identity**   | One company UUID + one `flb_live_*` / `flb_test_*` API key shared by API + worker        | `FLEETBASE_API_KEY`, `FLEETBASE_DEFAULT_COMPANY_UUID` / `PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID` in `apps/api/.env` and `env/.env` |
| **Contract**   | All PorterChain → Fleetbase HTTP goes through `FleetbaseAdapter`                         | `services/fleetbase-adapter/` · factory `get_fleetbase_integration()`                                                                  |
| **Engine**     | Sync, retry, webhooks, ops mirror — never browser → `:8000`                              | `apps/api/.../fleetbase_engine/`                                                                                                       |
| **Handshake**  | Authenticated `GET /v1/orders?limit=1` proves the wire; resets shared circuit on success | `FleetbaseAdapter.verify_bond()` · `fleetbase_engine/bond.py`                                                                          |
| **Self-heal**  | Local schema drift, missing `OrderConfig key=transport`, broken credentials              | `infrastructure/docker/scripts/repair_fleetbase_local.py` → `pnpm fleetbase:bond`                                                      |
| **Resilience** | Transient failure → RetryQueue / DLQ; rate-limit treated as retryable                    | `ErrorQueue` / `RetryQueue` · adapter circuit breaker                                                                                  |
| **Hygiene**    | Do **not** mass-backfill dummy/unlinked seed into Fleetbase                              | `pnpm fleetbase:purge-seed` · Jeff Dean: purge pollution, keep linked rows                                                             |

---

## Request path (unbreakable direction)

```
Portals / website / mobile
        │  HTTPS :8001 only
   thin routers → *_engine
        │
   fleetbase_engine (BookingSync / WebhookProcessor / RetryQueue)
        │
   FleetbaseAdapter  ←── permanent bond (only legal wire)
        │
   Fleetbase API :8000  (+ VROOM inside Fleetbase orchestrator)
```

**Forbidden:** portal/mobile SocketCluster SDK; portal HTTP to `:8000`; engines bypassing the adapter; Google Distance Matrix for pricing/dispatch; a PorterChain VROOM client.

---

## Boot & observability

| Signal           | Behavior                                                                             |
| ---------------- | ------------------------------------------------------------------------------------ |
| API lifespan     | Best-effort `run_boot_handshake()` — never blocks boot; logs bonded / not bonded     |
| `/health/ready`  | `checks.fleetbase_bond` = `ok` \| `unbonded:…` \| `skipped` when bridge off          |
| Admin live probe | `_probe_fleetbase_adapter(live=True)` calls `verify_bond`, not a bare host ping      |
| G2 SLO           | Link rate ≥98% on eligible orders (`assess_fleetbase_sync`); `pnpm validate:p0:fast` |

When handshake fails locally: **`pnpm fleetbase:bond`** (then restart API so env picks up a rotated key).

---

## Operator commands

| Command                        | What it does                                                                                                         |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `pnpm fleetbase:bond`          | Ensure company + API credential, seed `OrderConfig` transport, heal missing tables, POST/GET smoke (`--skip-docker`) |
| `pnpm fleetbase:bond:full`     | Same + attempt Fleetbase `deploy.sh` when Docker is available                                                        |
| `pnpm docker:fleetbase:verify` | Container / port health (not auth bond)                                                                              |
| `pnpm fleetbase:purge-seed`    | Delete unlinked seed orders + their sync jobs; **keep** Fleetbase-linked rows                                        |
| `pnpm fleetbase:replay`        | Requeue + drain real outbound sync (rate-limit aware; do not use to backfill dummies)                                |
| `pnpm validate:p0:fast`        | Includes G2 link-rate check against local API                                                                        |

---

## Payload rules that keep the bond from breaking

1. **Order type** — default Fleetbase `type` / OrderConfig key is `transport` (repair seeds it per company).
2. **Entities / packages** — stock Fleetbase treats `destination_uuid` as a **places FK**. PorterChain stop UUIDs must **not** be sent as `destination_uuid` (that 500s with `entities_destination_uuid_*`). Use waypoint `_import_id` + entity `meta.destination_import_id` / `meta.porterchain_stop_id`. Non-UUID import keys (e.g. test `"s1"`) may still use `destination_uuid` for versions that resolve `_import_id`.
3. **Meta** — always carry `porterchain_order_id` (and tracking/order numbers) on outbound orders.
4. **Secrets** — never commit live keys; repair may rewrite local `FLEETBASE_API_KEY` into both env files — restart API/worker after bond repair.

---

## Mental model (Jeff Dean)

- **Permanent** = identity + contract + handshake + queue, not “copy Fleetbase into the monorepo.”
- **Unbreakable** = failures are visible (bond check), recoverable (repair + circuit reset), and durable (RetryQueue) — not silent swallows without status.
- **Fleetbase as PorterChain files** (ops metaphor only) = treat the adapter boundary as first-class PorterChain surface; still **do not fork** upstream PHP.

---

## Code map

| Concern                        | Path                                                            |
| ------------------------------ | --------------------------------------------------------------- |
| Bond handshake                 | `apps/api/src/porterchain_api/fleetbase_engine/bond.py`         |
| Adapter façade + `verify_bond` | `services/fleetbase-adapter/.../integration.py`                 |
| HTTP client + circuit          | `services/fleetbase-adapter/.../client/` · `circuit_breaker.py` |
| Order payload mapper           | `services/fleetbase-adapter/.../mappers.py`                     |
| Sync health / G2               | `apps/api/.../fleetbase_engine/sync_health.py`                  |
| Local repair                   | `infrastructure/docker/scripts/repair_fleetbase_local.py`       |
| Seed purge                     | `apps/api/scripts/purge_unlinked_seed_orders.py`                |
| Replay                         | `apps/api/scripts/replay_fleetbase_sync.py`                     |

---

## See also

- Module Use / Extend / Replace: [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md)
- Integration test cases: [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md) (`FB-HS-*`, `FB-ENG-*`)
- Intentional skips (no PC VROOM, no SC in web): [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md)
