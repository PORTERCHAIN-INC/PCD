# 01 — System context (AS-BUILT)

```mermaid
flowchart LR
  RC([Retail customer]) -->|web/app book+track| PCD
  MER([Merchant staff]) -->|merchant portal / API key / Shopify| PCD
  DRV([Contractor driver]) -->|driver portal + Expo app, GPS| PCD
  STF([PorterChain staff / super-admin]) -->|admin portal| PCD
  PCD{{PorterChain PCD platform}}
  PCD --> CLERK[[Clerk]]
  PCD --> STRIPE[[Stripe]]
  PCD --> IMAP[[Bank mailbox: Interac e-Transfer notices via IMAP]]
  PCD --> ZEPTO[[ZeptoMail]]
  PCD --> FCM[[FCM / Web Push]]
  PCD --> SHOP[[Shopify]]
  PCD --> CHECKR[[Checkr]]
  PCD --> WA[[WhatsApp / lead channels]]
  PCD --> NIM[[NVIDIA NIM LLM]]
  PCD --> ERP[[NetSuite / Zapier adapters]]
  PCD --> GEO[[Valhalla, OSRM, Photon, PMTiles - self-hosted]]
```

| Element                                       | Evidence                                                                                         |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Clerk (merchant/driver/customer)              | `auth/dependencies.py` (`get_clerk_claims`), `apps/*/src/middleware.ts`                          |
| Staff IdP (passkey/magic link, Redis session) | `routers/auth_staff.py`, table `staff_webauthn_credentials`                                      |
| Stripe                                        | `billing_engine/stripe_money.py`                                                                 |
| Interac IMAP                                  | worker sweep `interac_inbox` (`apps/worker/run.py:695-721`)                                      |
| ZeptoMail                                     | route `POST /v1/public/mail/zeptomail` (06)                                                      |
| FCM / web-push                                | `notification_engine/*`, queue `porterchain:queue:push`                                          |
| Shopify                                       | `routers/shopify.py`, `integrations/shopify_orders.py:96`                                        |
| Checkr                                        | `routers/webhooks.py`, `routers/drivers_admin.py`                                                |
| WhatsApp                                      | `collaboration_engine/lead_channel_adapters.py:46-56` (lead intake only)                         |
| NIM                                           | `intelligence_engine/` client                                                                    |
| Geo                                           | `infrastructure/deploy/docker-compose.prod.yml` services valhalla/osrm/photon; Caddyfile PMTiles |
