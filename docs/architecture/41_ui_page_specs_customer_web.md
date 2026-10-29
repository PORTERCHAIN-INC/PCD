# 41 · UI page specs — Customer web

Generated from code (17 `page.tsx` under `apps/customer/src/app`) and cross-checked against doc 29 inventory. Read-only on code. Design tokens and components: doc 40. Flows: doc 42.

Default role: **Retail customer / guest**.

## Every page on this surface inherits

| Concern        | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| States         | **Loading:** skeleton matching layout (no spinners > 300 ms without skeleton). **Empty:** `EmptyState` with icon, one-line reason, primary action. **Error:** inline `Alert` with plain message + Retry + support ref id. **Offline:** top banner "You're offline — changes will sync"; writes queued (TanStack Query persist) or disabled with tooltip. **Permission-denied:** 403 card "You don't have access to this page. Ask an admin." + link home; nav item hidden when SpiceDB denies.               |
| Accessibility  | WCAG 2.2 AA + AODA: contrast >= 4.5:1 text / 3:1 UI, focus ring 2 px secondary, target >= 24x24 (44 on touch), skip link, landmark roles, labels on every input, errors linked via `aria-describedby`, status via `aria-live`, no colour-only meaning (margin badges carry text + icon), keyboard path for every action, reduced motion honoured, focus not obscured (2.4.11), dragging has a button alternative (2.5.7), no re-entry of known data (3.3.7), accessible auth without cognitive test (3.3.8). |
| Language       | EN/FR from day one: next-intl message keys, no hard-coded strings, `lang` attribute, fr-CA number/currency/date (`12,50 $`), French text +30 % width budget, language switch in header and profile, choice persisted to account.                                                                                                                                                                                                                                                                             |
| Breakpoints    | phone < 640, tablet 640–1023, laptop 1024–1439, desktop 1440–1919, large >= 1920. Tables → stacked cards on phone; side panels → bottom sheets; nav → drawer on phone/tablet, rail on laptop, full sidebar on desktop+.                                                                                                                                                                                                                                                                                      |
| Theme          | Light only for admin/super-admin (Ravi rule). Other web surfaces light default; dark optional later via tokens.                                                                                                                                                                                                                                                                                                                                                                                              |
| Margin colours | Wherever margin shows (admin/super-admin only): green >= 50 %, yellow < 50 %, red <= 35 %. Never blocks a quote. Badge = colour + icon + text ("Margin 42 % · Low").                                                                                                                                                                                                                                                                                                                                         |

## Page specs (17)

### 5.1 `/account`

- **File:** `apps/customer/src/app/account/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Retail customer / guest
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/customers/me/support`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.2 `/book`

- **File:** `apps/customer/src/app/book/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Retail customer / guest
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.3 `/book/success`

- **File:** `apps/customer/src/app/book/success/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Retail customer / guest
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.4 `/dashboard`

- **File:** `apps/customer/src/app/dashboard/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Retail customer / guest
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.5 `/impersonate`

- **File:** `apps/customer/src/app/impersonate/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Retail customer / guest
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.6 `/invoices/[invoice_id]`

- **File:** `apps/customer/src/app/invoices/[invoice_id]/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Retail customer / guest
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** `/v1/customers/me/invoices/{id}`
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.7 `/invoices`

- **File:** `apps/customer/src/app/invoices/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Retail customer / guest
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** `/v1/customers/me/invoices`
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.8 `/notifications`

- **File:** `apps/customer/src/app/notifications/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Retail customer / guest
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/notifications/inbox`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.9 `/onboarding`

- **File:** `apps/customer/src/app/onboarding/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Retail customer / guest
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.10 `/orders`

- **File:** `apps/customer/src/app/orders/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Retail customer / guest
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.11 `/`

- **File:** `apps/customer/src/app/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Retail customer / guest
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** `/v1/notifications/inbox`, `/v1/public/region`
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.12 `/send`

- **File:** `apps/customer/src/app/send/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Retail customer / guest
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.13 `/sign-in/[[...sign-in]]`

- **File:** `apps/customer/src/app/sign-in/[[...sign-in]]/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Retail customer / guest
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.14 `/sign-up/[[...sign-up]]`

- **File:** `apps/customer/src/app/sign-up/[[...sign-up]]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Retail customer / guest
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.15 `/track/[trackingNumber]`

- **File:** `apps/customer/src/app/track/[trackingNumber]/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Retail customer / guest
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** `/v1/customers/me/track-link/{id}`
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.16 `/track`

- **File:** `apps/customer/src/app/track/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Retail customer / guest
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 5.17 `/welcome`

- **File:** `apps/customer/src/app/welcome/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Retail customer / guest
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR
