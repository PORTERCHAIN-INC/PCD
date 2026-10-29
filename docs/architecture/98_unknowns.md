# 98 — Unknowns (not verified; nothing here is drawn as fact)

| ID   | Unknown                                                                                                      | How to resolve                            |
| ---- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| U-01 | Live DB schema vs migrations (local 55632 not compared for every table)                                      | read-only diff on 55632                   |
| U-02 | OpenAPI for 20 handlers missing from snapshot                                                                | regenerate offline                        |
| U-03 | Where the 50 % / 35 % margin bands are computed in code (warn-only)                                          | grep pricing engine; add test             |
| U-04 | Prod deployment topology beyond compose/Caddy                                                                | ops confirm                               |
| U-05 | Driver status transitions (no map)                                                                           | define in 17                              |
| U-06 | Outbox: confirmed absent; event delivery guarantees unknown                                                  | design step 2                             |
| U-07 | Shopify embedded app UI scope                                                                                | product decision                          |
| U-08 | DBOS vs LangGraph-only durability                                                                            | RESOLVED L18: DBOS + LangGraph            |
| U-09 | Whether `lead_consent` storage can serve CASL proof for all channels                                         | review schema                             |
| U-10 | PCI SAQ type (Stripe hosted fields assumed)                                                                  | confirm frontend integration              |
| U-11 | Staff MFA enforcement in IdP                                                                                 | check IdP config                          |
| U-12 | CVOR weight threshold for the box truck                                                                      | read ontario.ca CVOR page/HTA             |
| U-13 | GUI-0069 exact URL and transport/temperature record requirements                                             | fetch Health Canada page                  |
| U-14 | Whether O. Reg. 643/05 s.2 local-municipality exemption covers in-Toronto runs                               | legal review                              |
| U-15 | Retention period for driver documents and Checkr results                                                     | legal review                              |
| U-16 | PIPEDA breach-record retention period                                                                        | read OPC guidance                         |
| U-17 | CPA 2002 internet-agreement section numbers (not read)                                                       | read statute                              |
| U-18 | Unread official pages marked ○ in 19/20 (ETA, ITA, CPA, PIPEDA, CASL, ESA, HTA, TDG, AODA, ECA, CRA records) | open each link                            |
| U-19 | Kafka need                                                                                                   | RESOLVED L19: Kafka via Redpanda + outbox |
| U-20 | Rendering SVG/PNG: mmdc install blocked by safety check                                                      | render on approval                        |

Resolved Oct 28 2026: live GPS path verified as Redis hash/GEO + Pub/Sub `porterchain:ops:live`, not Redis Streams (evidence in 12).

## Hybrid deployment (file 28)

- U28-1 Ubuntu `wg0` 10.66.0.1/24 peers unknown (`/etc/wireguard` permission denied).
- U28-2 Real droplet size and RAM use today (only `bootstrap-droplet.sh:34` "4GB" comment).
- U28-3 Oracle A1 capacity in ca-toronto-1.
- U28-4 Valhalla arm64 image tag for Oracle.
