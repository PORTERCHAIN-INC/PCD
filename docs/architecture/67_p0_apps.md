# 67 · Now vs Phase 0: the apps (mobile, Shopify, portals)

## Customer + driver Expo apps: now

Evidence: `apps/mobile-customer`, `apps/mobile-driver`, Expo `~57.0.27`, RN `0.86.3`, version `1.0.0`, IDs `com.porterchain.customer` and `com.porterchain.PCD`; 8 customer screens, 12 driver screens; theme `packages/mobile-theme/src/tokens.ts`.

```mermaid
flowchart LR
  subgraph CUST[Customer app now]
    CS[SignIn: points at admin login] --> CH[Home/Book/Track]
    CH --> TC[test checkout: books without payment]
  end
  subgraph DRV[Driver app now]
    DS[SignIn: Clerk] --> DT[Today / Job / POD]
    DT --> GPS[background location]
  end
  CUST & DRV --> CLERK[[Clerk]]
  CUST & DRV --> GM[[Google Maps]]
  CUST & DRV --> API[(API)]
  CUST & DRV -.-> NS[No store listing yet]
```

## Expo apps: Phase 0

```mermaid
flowchart LR
  subgraph CUST[Customer app P0]
    CS[SignIn: Keycloak customer realm, passkey] --> CH[Home/Book/Track]
    CH --> PAY[Stripe payment sheet only]
    CH --> DEL[Account deletion]
  end
  subgraph DRV[Driver app P0, ID com.porterchain.PCD kept, L32]
    DS[SignIn: Keycloak driver realm] --> DT[Today / Job / POD]
    DT --> GPS[background location, declared]
    DT --> DEL2[Account deletion]
  end
  CUST & DRV --> TOK[one token source: design system 40]
  CUST & DRV --> ML[MapLibre + PMTiles]
  CUST & DRV --> API[(API)]
  CUST & DRV --> AS[[App Store]]
  CUST & DRV -.Phase 1.-> GP[[Google Play, target API 36, org account via D-U-N-S]]
```

## Shopify app: now vs Phase 0

```mermaid
flowchart LR
  subgraph NOW
    T1[app.toml + shopify.app.custom.toml] --> W1[webhooks incl. 3 compliance topics]
    W1 --> API1[(API /v1/integrations/shopify/webhooks)]
    note1[not installed on a live store?]
  end
  subgraph P0
    T2[one config: custom app, L30] --> W2[HMAC-verified webhooks + outbox ingest]
    T2 --> CS[CarrierService rates: contract price + merchant rule, needs Advanced/Plus or Grow + CCS]
    CS -.Basic plan.-> DP[flat/zone rates in delivery profiles]
    T2 --> INV[PorterChain bills merchant by Interac, no Shopify Billing]
    W2 --> API2[(API)]
    T2 --> PIL[installed on pilot store]
    T2 -.Phase 2.-> PUB[public listing review, doc 51]
  end
```

Two `.toml` files for one app are a clash: Phase 0 keeps one (`shopify.app.custom.toml` while unlisted) and documents the other as the public-listing config, or deletes it (U67-1).

## Web portals: now vs Phase 0

```mermaid
flowchart TB
  subgraph NOW
    A1[admin: public, 20 redirect stubs, dispatch + operations trees, Insights mixed into ops]
    M1[merchant-portal: Stripe + Interac billing]
    C1[customer]
    D1[driver-portal]
  end
  subgraph P0
    A2[admin on Ubuntu over WireGuard, IA 16, one dispatch tree, Insights removed]
    M2[merchant-portal: Interac only]
    C2[customer: Stripe only, French]
    D2[driver-portal: French]
  end
  NOW --> P0
```
