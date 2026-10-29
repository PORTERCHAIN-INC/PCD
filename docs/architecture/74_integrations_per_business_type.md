# 74. Integrations per business type (Phase 0, L35)

Cross-checked with doc 44 (API/data) and doc 24/51 (Shopify). New API lives under `/v1` (versioned), org-scoped.

## 1. Connection options

| Type              | Shopify app   | REST API + webhooks | CSV/Sheet upload | Email-to-order                      | Partner portal | EDI-lite                                          |
| ----------------- | ------------- | ------------------- | ---------------- | ----------------------------------- | -------------- | ------------------------------------------------- |
| Shopify merchant  | **primary**   | optional            | fallback         | —                                   | —              | —                                                 |
| Warehouse/3PL     | —             | primary             | primary          | —                                   | if partner     | optional                                          |
| Small shop        | if on Shopify | —                   | optional         | **primary** (orders@) + portal form | —              | —                                                 |
| Courier partner   | —             | job API optional    | —                | —                                   | **primary**    | —                                                 |
| Logistics partner | —             | optional            | —                | —                                   | primary        | **primary** (CSV over SFTP, 214-like status file) |
| Supply chain      | —             | primary             | optional         | —                                   | —              | primary                                           |
| CHA               | —             | optional            | optional         | —                                   | if partner     | primary (container/CAD refs)                      |

EDI-lite = fixed-column CSV (orders in, status out) over SFTP or email attachment, mapping to X12 204/214 and EDIFACT IFTMIN/IFTSTA fields without an EDI VAN cost.

## 2. TOP PRIORITY (Phase 0 weeks 1–2): Shopify review fix

**L36 login decision (Ravi, 29 Oct 2026, locked).** The rejections had one cause: **reviewers cannot log in through Clerk** (Ravi confirmed the reason). The decision:

- **Clerk is removed.** Self-hosted **Keycloak** is the only identity provider.
- **Sign-in methods:** social login with **Google** (built-in Keycloak IdP) and **Sign in with Apple**, plus email + password and **passkeys** (WebAuthn). Apple needs the free Apache-2.0 `keycloak-apple-social-identity-provider` extension; Apple's Services ID and key come with the existing Apple Developer membership. Both are free.
- **TOTP 2FA is required only for the admin and super admin roles** (staff realm, conditional flow).
- **Normal login has no OTP and no CAPTCHA.** Cloudflare Turnstile (free) runs invisibly and **only on risk signals**: repeated failures, a new device plus impossible travel, or an IP on a deny list. Keycloak brute-force detection (temporary lockout) and per-IP and per-account rate limits run at the edge and in Keycloak.
- **Shopify:** session token + token exchange, no login (§2).
- **Mobile:** a permanent reviewer account (password only), Sign in with Apple, and in-app deletion (§3).
- **Driver accounts are invite-only**, with a reviewer demo driver.

**Finding (code, 29 Oct 2026):** the manifest is already right (`integrations/shopify/shopify.app.custom.toml`: `embedded = true`, `use_legacy_install_flow = false`, compliance topics, session token posted to `POST /v1/integrations/shopify/session` with token exchange), and `/shopify-app` is a Clerk-public route (`apps/merchant-portal/src/middleware.ts`). What blocks reviewers is **after** install: an unlinked store shows "Last step: link this store to your PorterChain account" and opens `{PORTAL}/shopify?link=…` in a **new tab** (`apps/merchant-portal/src/lib/shopifyEmbed.ts:92`). That page is Clerk-gated: redirect to `/sign-in` (outside the Shopify iframe), Clerk hosted sign-up with email verification code and Clerk bot protection (CAPTCHA) — a reviewer or automated test bot cannot pass it, and nothing useful is visible inside Shopify admin before it. The four-click onboarding that avoids this is behind `SHOPIFY_FOUR_CLICK_ONBOARDING_ENABLED` (default off, `shopify-app/route.ts`). Line 118 still tells merchants to "sign in to the PorterChain portal" for invoices.

**Requirements (shopify.dev):** embedded apps must authenticate with App Bridge session tokens (https://shopify.dev/docs/apps/build/authentication-authorization/session-tokens) and get access tokens via token exchange (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/token-exchange) with Shopify-managed installation (https://shopify.dev/docs/apps/build/authentication-authorization/app-installation); App Store requirements: authenticate immediately after install, no separate login/sign-up before the app UI is usable, the UI must be inside admin, mandatory compliance webhooks (https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements, https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance).

**Fix (design):**

1. Install → session token → token exchange (offline token) → **auto-provision**: create `organisation` (business_type `shopify_merchant`, name/email/address/currency from Shop GraphQL), `integration(kind=shopify, external_account=shop domain)`, owner `membership` for the Shopify staff user (from session token `sub`, stored as `person` with `idp=shopify`), default operating profile, `b2b-std` rate card. Idempotent on shop domain (reinstall reuses the org).
2. The whole merchant experience for the pilot runs **inside the iframe**: setup (pickup address), rates status + deep link, orders list, invoices (PDF download), help. Make four-click onboarding the default; delete the "Link to my PorterChain account" step and the "sign in to the portal" sentence.
3. **No OTP, CAPTCHA, or top-level redirect** in the embedded path. Use App Bridge `open(…, "_top")` only for Shopify admin deep links.
4. Optional later: "Connect an existing PorterChain account" in Settings (Keycloak login in a new tab with Google, Apple, password or passkey; never required). The embedded app never shows a Clerk or Keycloak page (L36).
5. Compliance webhooks: `customers/data_request`, `customers/redact`, `shop/redact` verified with HMAC, handled within 30 days (DBOS job), logged; `app/uninstalled` → integration disabled, org kept 48 h then data per policy.
6. **Reviewer pack:** review notes ("No login is needed; the app opens set up. Use the PCDC store or any dev store. Steps: 1) open app 2) confirm pickup address 3) see a demo rate 4) open Orders: 3 demo orders"), screencast, a seeded demo mode for dev stores (`shop.plan = partner_test` → demo orders + sample invoice, never real dispatch), test card-free.
7. Tests: doc 76 §10 (A-SHR-*).

## 3. Mobile store review fix (weeks 1–2, mobile docs 25/26/50 refer here)

**Finding:** both apps sign in only through Clerk hosted auth (`useHostedAuth`, `apps/mobile-driver/src/screens/SignInScreen.tsx`); the profile flow uses `email_code` (`ProfilePage.tsx:366`); hosted pages carry Clerk bot protection; the driver app is invite-only, so a reviewer has no way in; account deletion exists in the driver app (`SettingsPage.tsx`/`MeScreen.tsx`) but not found in the customer app (U60-6).

**Requirements:** App Store Review Guideline 2.1 (provide a working demo account or full-featured demo mode), 4.8 (an app that offers a third-party or social login such as Google must also offer an equivalent privacy-focused login; **we offer Google, so Sign in with Apple is mandatory**), 5.1.1(v) (apps that support account creation must offer in-app account deletion) — https://developer.apple.com/app-store/review/guidelines/. Google Play: provide login credentials in App access (Play Console) and an in-app plus web account-deletion path (https://support.google.com/googleplay/android-developer/answer/9859455, https://support.google.com/googleplay/android-developer/answer/13327111).

**Fix:** a permanent **review account per app** in Keycloak (realm `porterchain`, attribute `review_account=true`): email + password, **no OTP, no CAPTCHA, no email verification step** for that flagged account only (Keycloak conditional flow), rate-limited, IP-agnostic (reviewers are outside Canada; do not geo-block sign-in). Customer review account belongs to the PCDC test org with seeded demo orders and tracking; driver review account gets **sandbox jobs** (fake addresses, dispatch never assigns real work, payouts disabled, GPS optional). Native in-app login replaces the Clerk hosted-browser hop (L36). The options are **Sign in with Apple** (native `expo-apple-authentication` on iOS, mandatory under 4.8 because Google is offered), Google, email + password, and passkey. Clerk is removed from both apps. The driver app is **invite-only**: Apple or Google sign-in only links to an invited driver, and a non-invited user sees "Ask your PorterChain contact for an invite". The **reviewer demo driver** is the exception. There is no OTP or CAPTCHA for anyone in normal login; Turnstile appears only on risk signals. In-app delete account in both apps + public web deletion page. App Review notes template: "Demo account: review.customer@porterchain.com / {password}. No code is sent. Area: Toronto. Steps…". Tests: doc 76 §11 (A-APR-*), run with Maestro (`apps/*/maestro/`).

## 4. API conventions (all types)

- **Auth:** API keys `pc_live_…`/`pc_test_…` (hash stored, prefix shown, scopes, per-org, rotate/revoke) for server-to-server; OAuth 2.0 client credentials via Keycloak for partners/enterprise; scopes `orders:write orders:read quotes:read labels:read tracking:read webhooks:manage partner_jobs:*`.
- **Sandbox:** every org gets a sandbox twin (`env=sandbox`) like PCDC; same API, fake dispatch, test labels watermarked "TEST".
- **Idempotency:** `Idempotency-Key` header required on POST; 24 h replay returns the same response; plus natural key `(org_id, ref_type, ref_value)` upsert (doc 70 §3).
- **Reference mapping:** every request may carry `external_refs: [{type:"order", value:"#1043"}, {type:"sku", value:"SOFA-3"}]`; every response, webhook and tracking lookup returns both `id: "PC-2611-7K3QX9"` and their refs. `GET /v1/orders?ref=#1043` works.
- **Webhooks:** events `order.created`, `order.picked_up`, `order.out_for_delivery`, `order.delivered`, `order.failed`, `label.ready`, `invoice.issued`, `partner_job.offered`, `order.price_changed, claim.opened`, `payout.sent` (doc 81 §2); signed `PC-Signature: t=…,v1=HMAC-SHA256(secret, t.body)`, 5-min tolerance, retries 24 h exp. backoff, delivery log in portal, replay button.
- **Versioning:** URL major `/v1`, dated minor header `PC-API-Version: 2026-11-01`; 12-month deprecation notice.
- **Errors:** RFC 9457 problem+json with plain-language `detail` and a `fix` field.

## 5. Their label vs our label

`label_mode` (doc 70 §4): **ours** → `GET /v1/orders/{id}/label?format=zpl|pdf` 4x6 (203/300 dpi ZPL, PDF for any printer), Code128 of PC id + QR to tracking; **theirs** → they POST their barcode value or the driver scans it at pickup (Code128, QR, GS1-128/SSCC) and it binds to the PC id as `external_ref(type=parcel)`; **both** → relabel rule (relabel if unreadable, non-whitelisted symbology, or multiple parcels need our sequence "1/3"). Tracking page accepts PC id, their order ref (+ postcode check), or a scanned barcode.

## 6. Developer portal outline

`developers.porterchain.com` (static docs from OpenAPI, G6): Quickstart (5 min, sandbox), Auth & keys, Orders, Quotes, Labels, Tracking, Webhooks (signature verify samples), Reference IDs, CSV/EDI-lite templates, Errors, Changelog, Status page link. Bilingual EN/FR headings, code samples curl/Python/JS.

## 7. Delta vs doc 44

Adds `org.*`, `integration.*`, `external_ref` (44 lists `merchant_api_keys`/`merchant_webhooks` → replaced); adds `PC-Signature`; Shopify routes unchanged except removal of the link-token step.
