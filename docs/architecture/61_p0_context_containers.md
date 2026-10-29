# 61 · Now vs Phase 0: system context and containers

Same diagrams as 01/02 (as-built) and 12 (planned), redrawn for the Phase 0 target (doc 60). Phase 0 has **no agentic mode**: no LLM, no agents. Tag **(P0)** = built in Phase 0. Unknowns are marked `?` and listed in 98.

## Context: now (from 01)

```mermaid
flowchart LR
  RC([Retail customer]) -->|web/app| PCD
  MER([Merchant staff]) -->|portal / API key / Shopify| PCD
  DRV([Contractor driver]) -->|driver portal + Expo app| PCD
  STF([Staff / super-admin]) -->|admin portal, public| PCD
  PCD{{PCD}}
  PCD --> CLERK[[Clerk]]
  PCD --> STRIPE[[Stripe: retail + merchants]]
  PCD --> IMAP[[Bank mailbox: Interac notices]]
  PCD --> ZEPTO[[ZeptoMail]]
  PCD --> FCM[[FCM / Web Push]]
  PCD --> TWILIO[[Twilio SMS]]
  PCD --> SENTRY[[Sentry]]
  PCD --> GMAPS[[Google Maps / Places]]
  PCD --> NIM[[NVIDIA NIM / OpenAI LLM]]
  PCD --> SHOP[[Shopify]]
  PCD --> CHECKR[[Checkr]]
  PCD --> ERP[[NetSuite / Zapier]]
  PCD --> GEO[[Valhalla, OSRM, Photon, PMTiles]]
  PCD --> DOP[[Doppler secrets]]
```

## Context: Phase 0 target

```mermaid
flowchart LR
  RC([Retail customer]) -->|web / App Store + Play app| PCD
  MER([Merchant staff]) -->|portal / API key / Shopify custom app| PCD
  DRV([Contractor driver]) -->|driver app, own phone| PCD
  STF([Staff / super-admin]) -->|admin over WireGuard only| PCD
  PCD{{PCD Phase 0: deterministic, no LLM}}
  PCD --> KC[Keycloak self-hosted P0]
  PCD --> STRIPE[[Stripe: retail customers only]]
  PCD --> IMAP[[Bank mailbox: Interac matching, merchants]]
  PCD --> ZEPTO[[ZeptoMail]]
  PCD --> PUSH[[FCM / APNs / Web Push]]
  PCD --> GT[GlitchTip self-hosted P0]
  PCD --> GEO[Valhalla, OSRM?, Photon, PMTiles self-hosted]
  PCD --> SHOP[[Shopify]]
  PCD --> STORES[[App Store, Google Play]]
  PCD --> WA[[wa.me links only, human sends]]
```

Removed in Phase 0: Clerk, Twilio, Sentry cloud, Google Maps/Places, Mapbox, OpenAI, NVIDIA NIM, Doppler, Stripe for merchants. Checkr is not called (L30 manual checks). NetSuite/Zapier adapters stay unused until Phase 2. `OSRM?` = kept only if it wins the matrix benchmark (D-P0-6).

## Containers: now (from 02)

```mermaid
flowchart TB
  subgraph EDGE[Caddy 80/443 on one 4 GB droplet]
    WEB[website :3000]
    MERCH[merchant-portal :3001]
    ADMIN[admin :3002 public]
    DRVP[driver-portal BFF :3003]
    CUST[customer :3004]
  end
  API[FastAPI api :8001]
  WRK[worker run.py: 5 processors + 22 polling sweeps]
  PG[(Postgres 18 public schema, 129 tables)]
  RD[(Redis: stream + lists + GPS)]
  SDB[(SpiceDB)]
  VAL[Valhalla :8002]
  OSRM[OSRM :5000]
  PH[Photon]
  WEB & MERCH & ADMIN & DRVP & CUST --> API
  API --> PG & RD & SDB & VAL & OSRM & PH
  WRK --> PG & RD
```

## Containers: Phase 0 target

```mermaid
flowchart TB
  subgraph DROPLET[Droplet 8 GB TOR1]
    WEB[website]
    MERCH[merchant-portal]
    DRVP[driver-portal BFF]
    CUST[customer]
    API[FastAPI api + DBOS workflows P0]
    KC[Keycloak P0]
    RP[(Redpanda 1 node P0, D-P0-2)]
    PG[(Postgres primary, domain schemas P0)]
    RD[(Redis: live GPS only)]
    SDB[(SpiceDB)]
  end
  subgraph UBUNTU[Ubuntu 32 GB, WireGuard]
    ADMIN[admin + super-admin P0]
    VALU[Valhalla full Ontario]
    GT[GlitchTip P0]
    GAR[(Garage POD archive)]
  end
  subgraph ORACLE[Oracle Always Free, Toronto]
    REP[(PG replica + Redpanda mirror)]
    VALO[Valhalla GTA+150 km]
    UK[Uptime Kuma DNS switch]
  end
  WEB & MERCH & DRVP & CUST --> API
  ADMIN -->|wg0| API
  API --> PG & RD & SDB & KC
  API -->|outbox relay| RP
  API --> RT{{routing adapter P0: Ubuntu, Oracle, haversine x1.35}}
  RT --> VALU & VALO
  PG -.replication.-> REP
```

No worker polling loop: the 22 sweeps are DBOS scheduled workflows or Redpanda consumers inside the API process group (31). No LLM container exists in Phase 0.
