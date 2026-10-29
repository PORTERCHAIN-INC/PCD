# 48 · Merchant onboarding and offboarding SOPs

## Onboarding (target: same day)

1. Lead → qualified (Sales agent drafts, human approves at suggest).
2. KYB: legal name, BN RT checked against the CRA format and registry (A07), director contact, Ontario address, inside the 150 km service area.
3. Sign the merchant agreement + DPA + rate card tier (e-sign with a free tool: Documenso self-hosted).
4. Keycloak org + users invited (business realm); API keys if needed; Shopify install link if Shopify.
5. Interac payment set-up and invoice terms (L10, no COD); HST on invoices if registered.
6. Restricted goods declaration (L3: no DG); cooler/box truck eligibility.
7. Test order in a sandbox → first live order watched by staff.

Done check: checklist in admin with every box ticked and logged.

## Offboarding

1. Merchant request or termination notice (per agreement).
2. Stop new orders; finish in-flight deliveries.
3. Final invoice / credit notes; settle Interac balance.
4. Revoke API keys, Keycloak users, Shopify access token. Process the app-uninstall plus `shop/redact` GDPR webhooks within 48 h / 30 days.
5. Data export (CSV + POD archive) on request (PIPEDA access).
6. Retention clock: keep invoices/POD for 6 years (CRA), delete or anonymize the rest after 90 days.
7. Close in the CRM with a reason.

Weeks: onboarding 6, offboarding 9.

**L30-8:** a pilot merchant exists (name TBD from Ravi).
