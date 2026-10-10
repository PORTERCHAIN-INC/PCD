# Shopify embedded app — droplet deploy + test checklist

Not deployed. Run this when Ravi ships to the droplet.

## 1. Before deploy

- [ ] `alembic upgrade head` includes `m1i2n3t4e5r6` (drops `merchants.stripe_enabled`).
- [ ] API env: `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET` (the app's client secret; it signs App Bridge session tokens).
- [ ] Merchant portal env: `SHOPIFY_API_KEY` (server-side, rendered as the `shopify-api-key` meta tag), `NEXT_PUBLIC_SITE_URL=https://merchant.<domain>`, `NEXT_PUBLIC_PORTERCHAIN_API_URL`.
- [ ] API CORS allows the merchant portal origin (the embedded page calls `POST /v1/integrations/shopify/session` from the browser).
- [ ] `integrations/shopify/app.toml`: `application_url = https://merchant.<domain>/shopify-app`, `embedded = true`, `use_legacy_install_flow = false`, no `[auth]` redirect URLs. Run `shopify app deploy` so Shopify manages scopes.
- [ ] Partner dashboard: listing pricing = **Free**. No Billing API charges. Delivery invoices go out monthly, paid by Interac e-Transfer.
- [ ] Valhalla (or OSRM) reachable from the API (`VALHALLA_URL`). The FSA rate card refuses to build without road routing.

## 2. Smoke tests (dev store)

1. Install from the Partner dashboard "Test on development store". Shopify grants scopes; no OAuth redirect screen of ours.
2. App opens inside Shopify admin at `/shopify-app`: "Checkout rates are live" + "Link to my PorterChain account".
   - `curl -I https://merchant.<domain>/shopify-app` → CSP `frame-ancestors https://admin.shopify.com https://*.myshopify.com`, no `X-Frame-Options: DENY`.
   - Every other portal page still sends `X-Frame-Options: DENY`.
3. Click Link → portal opens `/shopify?link=…` → sign in / sign up → "Store linked to this account".
4. Reopen the app in Shopify admin → shows "Linked to <company>".
5. Settings → Shipping and delivery → Canada: PorterChain carrier listed; a checkout to a GTA address shows the rate and delivery promise.
6. Place a test order → appears in merchant portal → fulfil → tracking syncs back to Shopify.
7. Uninstall → reinstall → open app: rates heal, link stays with the same company.
8. Link token from store A pasted into another company's portal → "already linked to another PorterChain account".
9. Expired link (>15 min) → "That store link expired… press Link again".
10. GDPR webhooks (`customers/data_request`, `customers/redact`, `shop/redact`) → 200 with valid HMAC, 401 without.

## 3. Money

- [ ] Merchant portal Billing: no "Pay now" / card buttons anywhere; Payments tab says Interac e-Transfer.
- [ ] Admin merchant settings: no Stripe toggle.
- [ ] Customer (retail) Stripe checkout still works end to end.

## 4. FSA rate card

- [ ] Admin → Merchant → Pricing (model FSA) → "Rebuild from pickup": ~230 GTA FSAs priced in a few seconds.
- [ ] Edit a cell in the FSA table → rebuild → the edited cell is kept.
- [ ] PDF and CSV export download; merchant portal Billing → Rates shows "Rate card PDF / CSV".
- [ ] Change the merchant's default pickup → next card read regenerates from the new pickup.

## Rollback

Previous image + `alembic downgrade r4planinputs7a8b` (re-adds `stripe_enabled` as false). Shopify config rollback: `shopify app deploy` from the previous commit's `app.toml`.
