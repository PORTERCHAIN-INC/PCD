# POINTER — use the master entry

**Superseded.** Do not grow this file.

**Start here:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md)

| Depth                         | Doc                                                                            |
| ----------------------------- | ------------------------------------------------------------------------------ |
| Full-stack soak               | [DEV_TEST_CASES_FULL_STACK.md](DEV_TEST_CASES_FULL_STACK.md)                   |
| Fleetbase + vendors           | [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md) |
| Valhalla / OSRM / VROOM       | [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md)   |
| VROOM spine + missed surfaces | [DEVELOPMENT_TEST_CASES_CATALOG.md](DEVELOPMENT_TEST_CASES_CATALOG.md)         |
| Admin                         | [ADMIN_SUPERADMIN_DEV_TESTCASES.md](ADMIN_SUPERADMIN_DEV_TESTCASES.md)         |
| Merchant                      | [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md)     |
| Customer                      | [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md)       |
| Driver                        | [DRIVER_ADMIN_DEV_TEST_CASES.md](DRIVER_ADMIN_DEV_TEST_CASES.md)               |
| Policy holds                  | [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md)                           |

**2026-09-17 sensor addendum (CodeGraph + Ripwire):** OSRM has **no directed edge** to `FleetbaseClient`. Pricing uses MapsService (Valhalla→OSRM). Optimize/VROOM uses `VROOM_ROUTER=valhalla` inside Fleetbase. See master **HS-25** / **MAP-11**.
