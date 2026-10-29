# 53 · Accessibility (AODA / WCAG 2.1 AA) and French

## Accessibility

- **Target:** WCAG 2.1 AA for the website, all portals and both apps. AODA's Integrated Accessibility Standards require it for public websites of larger organizations. Confirm the size threshold and reporting duty for Porterchain Inc. with the lawyer, but build to AA anyway.
- **Week 2:** axe-core checks in Playwright (nightly lane) for every portal. `verify_booking_a11y.py` is kept as a gate.
- **Weeks 2–5:** design system tokens: contrast ≥ 4.5:1. Margin colours are not colour-only, because each green/yellow/red band also gets an icon and text (L2).
- **Mobile:** accessibility labels and Dynamic Type; Maestro checks labels.
- **Week 13:** manual audit with NVDA (free) + VoiceOver, plus an accessibility statement page and a feedback form.

## French

- **Website:** already bilingual (`website/messages/*-fr.json`). `verify_i18n_parity.py` and `verify_fr_en_leakage.py` are kept as gates.
- **Week 11:** customer-facing emails, invoices, credit notes, tracking page and notifications in FR (`notification_template_copy` gets FR rows).
- **Help Centre + legal documents: Phase 0 (D-68-2, overrides L30-5 for that content).**
- **Portals and apps (L30-5):** FR in Phase 1 for everything customer-facing (website, customer/merchant/driver portals, customer + driver apps, Shopify app, emails/push/PDFs, legal docs). Admin console FR in Phase 2.
- **Agents:** reply drafts follow the customer's language (Qwen3.5 handles FR), and the verifier checks that amounts are identical.
- **Bill 96 (Quebec):** the service area is Toronto plus 150 km, so it likely doesn't apply. Confirm.
