# 42 · UX flows (PLANNED)

Screens referenced are in 41_*; components in 40. All flows: EN/FR, offline-tolerant where marked, agent steps go through approval cards for the six human cases.

## 1. Booking (customer web/app, merchant portal, Shopify)

```mermaid
flowchart LR
  A[Start: Send / Book] --> B[Pickup + drop address]
  B -->|outside Toronto+150 km| X[Refuse: outside service area]
  B --> C[Items, weight, vehicle]
  C -->|dangerous goods| X2[Refuse: not allowed]
  C --> D[Time window]
  D --> E[Quote from live rate card]
  E --> F{Payer}
  F -->|retail| G[Stripe payment sheet]
  F -->|merchant| H[On account, Interac invoice]
  G --> I[Confirmed + tracking link]
  H --> I
  I --> J[Email/push booking_confirmed]
```

## 2. Quote with margin band (admin)

```mermaid
flowchart TD
  Q[Quote builder] --> L[Lines: base + km + add-ons + fuel 5%]
  L --> M["Margin = (price - cost) / price"]
  M -->|>= 50| G[Green Healthy]
  M -->|< 50| Y[Yellow Low]
  M -->|<= 35| R[Red At risk + alert]
  G & Y & R --> S[Save / send quote - never blocked]
```

## 3. Tracking

```mermaid
sequenceDiagram
  participant C as Customer
  participant W as Track page/app
  participant API as Droplet API
  participant RD as Redis GPS
  C->>W: open link / code
  W->>API: GET /v1/tracking/{code}
  API-->>W: status, timeline, ETA
  W->>RD: subscribe live position (WS)
  RD-->>W: position every 5-10 s
  W-->>C: map + ETA + Live Activity
```

## 4. Dispatch

```mermaid
flowchart LR
  O[New order event] --> P[Dispatch agent proposes driver]
  P -->|in autonomy| OF[Offer to driver, countdown]
  P -->|needs human| AC[Approval card]
  AC --> OF
  OF -->|accept| AS[Assigned]
  OF -->|decline/timeout| P
  AS --> LV[Live map + exceptions]
```

## 5. Proof of delivery (driver app, offline-first)

```mermaid
flowchart TD
  AR[Arrive - geofence] --> SC[Scan parcel]
  SC --> PH[Photo + GPS + time + hash]
  PH --> SG[Name / signature]
  SG --> Q{Online?}
  Q -->|yes| UP[Upload POD]
  Q -->|no| LQ[Encrypted local queue] --> UP
  UP --> AI[Local AI photo check]
  AI -->|ok| DL[Delivered + notify]
  AI -->|doubt| EX[Exception for admin]
  AR -->|can't deliver| FR[Fail reason + photo] --> EX
```

## 6. Invoicing

```mermaid
flowchart LR
  D[Delivered orders] --> B[Billing workflow DBOS]
  B --> I[Invoice draft]
  I --> R[Admin review]
  R --> S[Send PDF via ZeptoMail]
  S --> P{Paid?}
  P -->|Interac received| RC[Record payment]
  P -->|overdue| RM[Reminder emails]
```

## 7. Credit notes

```mermaid
flowchart TD
  CL[Claim / billing error] --> CN[Draft credit note]
  CN --> V{Amount <= remaining balance?}
  V -->|no| E[Error: exceeds balance]
  V -->|yes| A{Over approval cap?}
  A -->|yes| AC[Approval card]
  A -->|no| IS[Issue]
  AC --> IS --> PDF[Credit note PDF + email]
```

## 8. Onboarding (merchant, driver)

```mermaid
flowchart LR
  subgraph Merchant
   M1[Sign up Keycloak] --> M2[Business + HST no.] --> M3[Pickup address] --> M4[Admin approval] --> M5[First order / Shopify connect]
  end
  subgraph Driver
   D1[Apply: vehicle-partner page] --> D2[Docs upload] --> D3[Background check - decision: Checkr vs manual] --> D4[Consent ESA notice] --> D5[Training] --> D6[Activated]
  end
```

## 9. Claims

```mermaid
stateDiagram-v2
  [*] --> Opened: customer/merchant files claim + photos
  Opened --> Reviewing: agent gathers POD, GPS, photos
  Reviewing --> Approved
  Reviewing --> Rejected: reason shown
  Approved --> Refunded: credit note / refund (approval card if over cap)
  Refunded --> [*]
  Rejected --> [*]
```

## 10. Agent approval card

```mermaid
flowchart TD
  AG[Agent action outside autonomy bar or one of 6 human cases] --> CARD[Approval card in Today inbox]
  CARD --> V[Shows: what, why, evidence, confidence, money impact, margin badge]
  V --> A{Admin}
  A -->|Approve| X[Execute + audit]
  A -->|Edit + approve| X
  A -->|Reject + reason| F[Feedback to agent eval set]
  A -->|no action in SLA| ESC[Escalate push to super-admin]
```
