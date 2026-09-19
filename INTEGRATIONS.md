# Integrations matrix

**Type:** CANONICAL · **Verified:** 2026-09-15

SSOT registry: [`integrations.yaml`](integrations.yaml). Guard: `pnpm validate:integrations-matrix` (`scripts/verify_integrations_matrix.py`).

| Key                 | Role                                                |
| ------------------- | --------------------------------------------------- |
| `porterchain_api`   | FastAPI `:8001`                                     |
| `postgres`          | PostgreSQL 18                                       |
| `redis`             | Redis 8.8                                           |
| `fleetbase`         | Execution console + adapter (`:8000`)               |
| `google_maps`       | Places + tiles only                                 |
| `valhalla`          | Primary routing `:8002` (GTA ±150 km)               |
| `osrm`              | Local fallback `:5000` (same extract)               |
| `stripe`            | Checkout + COD/Connect via `sdk.py`                 |
| `clerk`             | Identity for every persona                          |
| `merchant_api_keys` | Merchant API keys — partner `/v1/merchant-api`      |
| `merchant_webhooks` | Merchant outbound webhooks                          |
| `oauth_third_party` | OAuth third-party providers (merchant integrations) |

Tree: [ARCHITECTURE.md](ARCHITECTURE.md).
