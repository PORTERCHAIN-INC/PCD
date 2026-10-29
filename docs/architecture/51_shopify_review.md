# 51 · Shopify app review checklist

**Decision first (week 7, Ravi):** a public listed app must charge merchants through Shopify Billing for app charges. Delivery fees invoiced by PorterChain (Interac, L10) are a service outside the app, so this should be allowed if the app itself is free. Confirm on Shopify's billing rules before submitting. The alternative is a custom/unlisted app per merchant, which needs no review.

## Checklist (submit week 9)

- Mandatory GDPR webhooks: `customers/data_request`, `customers/redact`, `shop/redact`, all handled with HMAC verify.
- Session-token auth, embedded App Bridge, no third-party cookies.
- Built for Shopify gaps from doc 24: Polaris web components, a home screen that meets the standards, performance (LCP < 2.5 s admin), dedupe of duplicate order webhooks (`X-Shopify-Webhook-Id`).
- Carrier rates (`shopify_carrier_rates`) return within 10 s with a fallback.
- Listing assets in `integrations/shopify/listing`, plus an updated privacy policy URL (doc 49).
- Uninstall cleans up the token and data (doc 48).
- Test store + reviewer instructions + demo video.
