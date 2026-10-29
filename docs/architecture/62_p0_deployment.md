# 62 · Now vs Phase 0: deployment and network

## Now (02, 28 §1)

```mermaid
flowchart LR
  NET((Internet)) --> CF[Cloudflare DNS]
  CF --> DROP[Droplet 4 GB?: Caddy, 5 Next apps, API, worker, PG, Redis, SpiceDB, Valhalla, OSRM, Photon]
  UB[Ubuntu desktop: dev + local stacks 55632, 56679, 55251] -.-|wg0 10.66.0.1, peers unknown| DROP
```

Admin is public on the droplet. Droplet size from `bootstrap-droplet.sh:34` comment only (U28-2).

## Phase 0 target (L28, Ravi D-* 28 Oct)

```mermaid
flowchart LR
  NET((Internet)) --> CF[Cloudflare DNS-only]
  CF -->|A record| DROP
  UK[Uptime Kuma on Oracle] -->|Cloudflare API switch, only if Ubuntu agrees| CF
  subgraph DROP[Droplet 8 GB TOR1]
    CADDY[Caddy /healthz /readyz]
    APPS[website, merchant, customer, driver BFF, API+DBOS, Keycloak]
    DATA[(PG primary, Redpanda, Redis GPS, SpiceDB)]
  end
  subgraph UB[Ubuntu 32 GB]
    ADM[admin + super-admin]
    VAL[Valhalla Ontario]
    GT[GlitchTip]
    GAR[(Garage archive 6 y)]
    BK[backups + monthly USB copy]
  end
  subgraph OR[Oracle A1 Toronto]
    REP[(PG replica, Redpanda mirror)]
    VO[Valhalla GTA+150 arm64?]
    EDGE[standby Caddy]
  end
  DROP <-->|WireGuard| UB
  DROP <-->|WireGuard| OR
  UB <-->|WireGuard| OR
  STAFF([Staff]) -->|WireGuard client| ADM
```

Phase 0 exit drill set (G15): Ubuntu off 24 h (business users unaffected; admin unavailable; routing falls back to Oracle then haversine "estimated"); Oracle off; droplet off (manual `promote.sh` on Oracle, customers see "please retry"); network split (no automatic promotion). Unknowns: wg0 peers (U28-1), Oracle A1 capacity (U28-3), Valhalla arm64 image (U28-4).
