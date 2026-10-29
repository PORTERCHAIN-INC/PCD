# 41 · UI page specs — Website (public marketing + tools)

Generated from code (72 `page.tsx` under `website/src/app`) and cross-checked against doc 29 inventory. Read-only on code. Design tokens and components: doc 40. Flows: doc 42.

Default role: **Public visitor (guest), SEO**.

## Every page on this surface inherits

| Concern        | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| States         | **Loading:** skeleton matching layout (no spinners > 300 ms without skeleton). **Empty:** `EmptyState` with icon, one-line reason, primary action. **Error:** inline `Alert` with plain message + Retry + support ref id. **Offline:** top banner "You're offline — changes will sync"; writes queued (TanStack Query persist) or disabled with tooltip. **Permission-denied:** 403 card "You don't have access to this page. Ask an admin." + link home; nav item hidden when SpiceDB denies.               |
| Accessibility  | WCAG 2.2 AA + AODA: contrast >= 4.5:1 text / 3:1 UI, focus ring 2 px secondary, target >= 24x24 (44 on touch), skip link, landmark roles, labels on every input, errors linked via `aria-describedby`, status via `aria-live`, no colour-only meaning (margin badges carry text + icon), keyboard path for every action, reduced motion honoured, focus not obscured (2.4.11), dragging has a button alternative (2.5.7), no re-entry of known data (3.3.7), accessible auth without cognitive test (3.3.8). |
| Language       | EN/FR from day one: next-intl message keys, no hard-coded strings, `lang` attribute, fr-CA number/currency/date (`12,50 $`), French text +30 % width budget, language switch in header and profile, choice persisted to account.                                                                                                                                                                                                                                                                             |
| Breakpoints    | phone < 640, tablet 640–1023, laptop 1024–1439, desktop 1440–1919, large >= 1920. Tables → stacked cards on phone; side panels → bottom sheets; nav → drawer on phone/tablet, rail on laptop, full sidebar on desktop+.                                                                                                                                                                                                                                                                                      |
| Theme          | Light only for admin/super-admin (Ravi rule). Other web surfaces light default; dark optional later via tokens.                                                                                                                                                                                                                                                                                                                                                                                              |
| Margin colours | Wherever margin shows (admin/super-admin only): green >= 50 %, yellow < 50 %, red <= 35 %. Never blocks a quote. Badge = colour + icon + text ("Margin 42 % · Low").                                                                                                                                                                                                                                                                                                                                         |

## Page specs (72)

### 1.1 `/[locale]/[...rest]`

- **File:** `website/src/app/[locale]/[...rest]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.2 `/[locale]/[city]/[industrySlug]`

- **File:** `website/src/app/[locale]/[city]/[industrySlug]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.3 `/[locale]/accessibility`

- **File:** `website/src/app/[locale]/accessibility/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.4 `/[locale]/authors/[id]`

- **File:** `website/src/app/[locale]/authors/[id]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.5 `/[locale]/authors`

- **File:** `website/src/app/[locale]/authors/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.6 `/[locale]/blog/[slug]`

- **File:** `website/src/app/[locale]/blog/[slug]/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Public visitor (guest), SEO
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.7 `/[locale]/blog/category/[category]`

- **File:** `website/src/app/[locale]/blog/category/[category]/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Public visitor (guest), SEO
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.8 `/[locale]/blog`

- **File:** `website/src/app/[locale]/blog/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Public visitor (guest), SEO
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.9 `/[locale]/blog/preview/[slug]`

- **File:** `website/src/app/[locale]/blog/preview/[slug]/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Public visitor (guest), SEO
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.10 `/[locale]/book/continue`

- **File:** `website/src/app/[locale]/book/continue/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Public visitor (guest), SEO
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.11 `/[locale]/book`

- **File:** `website/src/app/[locale]/book/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Public visitor (guest), SEO
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.12 `/[locale]/book/success`

- **File:** `website/src/app/[locale]/book/success/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Public visitor (guest), SEO
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.13 `/[locale]/box-truck-delivery`

- **File:** `website/src/app/[locale]/box-truck-delivery/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.14 `/[locale]/business`

- **File:** `website/src/app/[locale]/business/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.15 `/[locale]/campaigns/[slug]`

- **File:** `website/src/app/[locale]/campaigns/[slug]/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Public visitor (guest), SEO
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.16 `/[locale]/campaigns`

- **File:** `website/src/app/[locale]/campaigns/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Public visitor (guest), SEO
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.17 `/[locale]/careers`

- **File:** `website/src/app/[locale]/careers/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.18 `/[locale]/cargo-van-delivery`

- **File:** `website/src/app/[locale]/cargo-van-delivery/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.19 `/[locale]/company`

- **File:** `website/src/app/[locale]/company/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.20 `/[locale]/compare/[slug]`

- **File:** `website/src/app/[locale]/compare/[slug]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.21 `/[locale]/compare`

- **File:** `website/src/app/[locale]/compare/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.22 `/[locale]/contact`

- **File:** `website/src/app/[locale]/contact/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.23 `/[locale]/cookies`

- **File:** `website/src/app/[locale]/cookies/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.24 `/[locale]/delivery-cost-calculator`

- **File:** `website/src/app/[locale]/delivery-cost-calculator/page.tsx`
- **Purpose:** Build or show a price from the live rate card version
- **Role:** Public visitor (guest), SEO
- **Layout:** Two-column: form left, sticky price summary right (stacks on phone)
- **Components:** Form, AddressAutocomplete, VehiclePicker, QuoteLines, MarginBadge (admin only), Button
- **Key actions:** Get quote, edit lines, save draft, convert to order
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Address inside Toronto+150 km else "Outside service area"; weight/vehicle rule; dangerous goods refused
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.25 `/[locale]/delivery/[industry]/[area]`

- **File:** `website/src/app/[locale]/delivery/[industry]/[area]/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.26 `/[locale]/delivery/[industry]`

- **File:** `website/src/app/[locale]/delivery/[industry]/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.27 `/[locale]/delivery`

- **File:** `website/src/app/[locale]/delivery/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.28 `/[locale]/developers/docs/[slug]`

- **File:** `website/src/app/[locale]/developers/docs/[slug]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.29 `/[locale]/developers/docs`

- **File:** `website/src/app/[locale]/developers/docs/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.30 `/[locale]/developers`

- **File:** `website/src/app/[locale]/developers/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** `/v1/bookings`, `/v1/merchant-api/orders`, `/v1/orders/{tracking_number}/tracking`, `/v1/quotes`
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.31 `/[locale]/email-preferences`

- **File:** `website/src/app/[locale]/email-preferences/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.32 `/[locale]/enterprise`

- **File:** `website/src/app/[locale]/enterprise/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.33 `/[locale]/facts`

- **File:** `website/src/app/[locale]/facts/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.34 `/[locale]/faq`

- **File:** `website/src/app/[locale]/faq/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.35 `/[locale]/guides/[slug]`

- **File:** `website/src/app/[locale]/guides/[slug]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.36 `/[locale]/guides`

- **File:** `website/src/app/[locale]/guides/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.37 `/[locale]/industry/[slug]`

- **File:** `website/src/app/[locale]/industry/[slug]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.38 `/[locale]/integrations`

- **File:** `website/src/app/[locale]/integrations/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Public visitor (guest), SEO
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.39 `/[locale]/login/[[...sign-in]]`

- **File:** `website/src/app/[locale]/login/[[...sign-in]]/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Public visitor (guest), SEO
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.40 `/[locale]/login/continue`

- **File:** `website/src/app/[locale]/login/continue/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Public visitor (guest), SEO
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.41 `/[locale]/newsletter/confirm`

- **File:** `website/src/app/[locale]/newsletter/confirm/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.42 `/[locale]/onboarding-education/[slug]`

- **File:** `website/src/app/[locale]/onboarding-education/[slug]/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Public visitor (guest), SEO
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.43 `/[locale]/page-not-found`

- **File:** `website/src/app/[locale]/page-not-found/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.44 `/[locale]`

- **File:** `website/src/app/[locale]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.45 `/[locale]/pickup-truck-delivery`

- **File:** `website/src/app/[locale]/pickup-truck-delivery/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.46 `/[locale]/platform`

- **File:** `website/src/app/[locale]/platform/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.47 `/[locale]/privacy`

- **File:** `website/src/app/[locale]/privacy/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Public visitor (guest), SEO
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.48 `/[locale]/quote`

- **File:** `website/src/app/[locale]/quote/page.tsx`
- **Purpose:** Build or show a price from the live rate card version
- **Role:** Public visitor (guest), SEO
- **Layout:** Two-column: form left, sticky price summary right (stacks on phone)
- **Components:** Form, AddressAutocomplete, VehiclePicker, QuoteLines, MarginBadge (admin only), Button
- **Key actions:** Get quote, edit lines, save draft, convert to order
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Address inside Toronto+150 km else "Outside service area"; weight/vehicle rule; dangerous goods refused
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.49 `/[locale]/rates`

- **File:** `website/src/app/[locale]/rates/page.tsx`
- **Purpose:** Build or show a price from the live rate card version
- **Role:** Public visitor (guest), SEO
- **Layout:** Two-column: form left, sticky price summary right (stacks on phone)
- **Components:** Form, AddressAutocomplete, VehiclePicker, QuoteLines, MarginBadge (admin only), Button
- **Key actions:** Get quote, edit lines, save draft, convert to order
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Address inside Toronto+150 km else "Outside service area"; weight/vehicle rule; dangerous goods refused
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.50 `/[locale]/research`

- **File:** `website/src/app/[locale]/research/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Public visitor (guest), SEO
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.51 `/[locale]/sedan-delivery`

- **File:** `website/src/app/[locale]/sedan-delivery/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.52 `/[locale]/service-areas/[slug]`

- **File:** `website/src/app/[locale]/service-areas/[slug]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.53 `/[locale]/service-areas`

- **File:** `website/src/app/[locale]/service-areas/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.54 `/[locale]/sign-up/[[...sign-up]]`

- **File:** `website/src/app/[locale]/sign-up/[[...sign-up]]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.55 `/[locale]/terms`

- **File:** `website/src/app/[locale]/terms/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.56 `/[locale]/track/[tracking]/manage`

- **File:** `website/src/app/[locale]/track/[tracking]/manage/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.57 `/[locale]/track/[tracking]`

- **File:** `website/src/app/[locale]/track/[tracking]/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** `/v1/bookings/mock-complete`, `/v1/bookings/sync-checkout`, `/v1/delivery-manage/{id}`, `/v1/email-preferences`, `/v1/email-preferences/delete-request`, `/v1/email-preferences/read`, `/v1/email-preferences/unsubscribe`, `/v1/express/checkout`, `/v1/express/confirmation`, `/v1/express/send-again`, `/v1/orders/{id}`, `/v1/orders/{id}/tracking`
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.58 `/[locale]/track`

- **File:** `website/src/app/[locale]/track/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.59 `/[locale]/trade-van-delivery`

- **File:** `website/src/app/[locale]/trade-van-delivery/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Public visitor (guest), SEO
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.60 `/[locale]/trust/claims`

- **File:** `website/src/app/[locale]/trust/claims/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Public visitor (guest), SEO
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.61 `/[locale]/trust/corrections`

- **File:** `website/src/app/[locale]/trust/corrections/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.62 `/[locale]/trust/editorial-policy`

- **File:** `website/src/app/[locale]/trust/editorial-policy/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Public visitor (guest), SEO
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.63 `/[locale]/trust/founder`

- **File:** `website/src/app/[locale]/trust/founder/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.64 `/[locale]/trust`

- **File:** `website/src/app/[locale]/trust/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.65 `/[locale]/trust/research-methodology`

- **File:** `website/src/app/[locale]/trust/research-methodology/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Public visitor (guest), SEO
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.66 `/[locale]/trust/security`

- **File:** `website/src/app/[locale]/trust/security/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Public visitor (guest), SEO
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.67 `/[locale]/trust/service-standards`

- **File:** `website/src/app/[locale]/trust/service-standards/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.68 `/[locale]/unsubscribe`

- **File:** `website/src/app/[locale]/unsubscribe/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.69 `/[locale]/vehicle-partner`

- **File:** `website/src/app/[locale]/vehicle-partner/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.70 `/[locale]/vehicles`

- **File:** `website/src/app/[locale]/vehicles/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.71 `/proof-of-resolution`

- **File:** `website/src/app/proof-of-resolution/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 1.72 `/ravi`

- **File:** `website/src/app/ravi/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Public visitor (guest), SEO
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR
