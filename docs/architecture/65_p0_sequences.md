# 65 · Now vs Phase 0: key sequences

## Event emission: now (10)

```mermaid
sequenceDiagram
  participant API
  participant DB as Postgres
  participant BUS as Redis Stream porterchain:events
  participant W as worker
  API->>DB: COMMIT order change
  API->>BUS: XADD (separate, can be lost)
  W->>BUS: XREADGROUP
  W->>W: route to lists emails/sms/push
  Note over W: plus 22 polling sweeps
```

## Event emission: Phase 0

```mermaid
sequenceDiagram
  participant API
  participant DB as Postgres
  participant R as DBOS outbox relay
  participant K as Redpanda
  participant C as consumer (notify, billing)
  API->>DB: BEGIN, change + INSERT event_outbox, COMMIT
  R->>DB: read unsent (DBOS step, idempotent)
  R->>K: produce pc.order.v1 (key = order_id)
  R->>DB: mark sent
  K->>C: consume, dedupe on event id
```

## Staff sign-in: now vs Phase 0

```mermaid
sequenceDiagram
  participant S as Staff browser
  participant A as admin (public)
  participant CL as Clerk
  participant API
  S->>A: open admin.porterchain.com
  A->>CL: hosted sign-in
  CL-->>A: session JWT
  A->>API: Bearer Clerk JWT + SpiceDB check
```

```mermaid
sequenceDiagram
  participant S as Staff laptop (WireGuard)
  participant A as admin on Ubuntu
  participant KC as Keycloak staff realm
  participant API as API on droplet
  S->>A: open admin over wg0
  A->>KC: OIDC code + PKCE, passkey or TOTP
  KC-->>A: tokens
  A->>API: Bearer Keycloak JWT over wg0 + SpiceDB check (one checker with retry, A13)
```

## Merchant payment: Phase 0 (Interac only)

```mermaid
sequenceDiagram
  participant B as billing workflow (DBOS)
  participant M as Merchant
  participant MB as Bank mailbox
  participant MT as interac matcher (DBOS schedule)
  B->>M: invoice email with Interac instructions + reference
  M->>MB: e-Transfer (notice email arrives)
  MT->>MB: read notices (IMAP)
  MT->>B: match amount + reference, mark paid, or raise exception
```

## Routing with failover: Phase 0

```mermaid
sequenceDiagram
  participant P as Plan page
  participant API
  participant RA as routing adapter
  participant VU as Valhalla Ubuntu
  participant VO as Valhalla Oracle
  P->>API: optimise plan
  API->>RA: matrix + route
  RA->>VU: request (timeout 3 s)
  alt Ubuntu down
    RA->>VO: request
    alt Oracle down
      RA-->>API: haversine x1.35, flagged estimated
    end
  end
  API-->>P: plan + diff + reasons
```

**L32 (29 Oct):** in "Routing with failover", the routing adapter calls VROOM after building the matrix; VROOM falls back to Oracle VROOM, then to the `vrp.py` heuristic on the estimated matrix (doc 60 §13.3).
