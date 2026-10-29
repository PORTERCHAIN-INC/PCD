# 41 · UI page specs — Merchant portal

Generated from code (24 `page.tsx` under `apps/merchant-portal/src/app`) and cross-checked against doc 29 inventory. Read-only on code. Design tokens and components: doc 40. Flows: doc 42.

Default role: **Merchant owner / merchant staff**.

## Every page on this surface inherits

| Concern        | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| States         | **Loading:** skeleton matching layout (no spinners > 300 ms without skeleton). **Empty:** `EmptyState` with icon, one-line reason, primary action. **Error:** inline `Alert` with plain message + Retry + support ref id. **Offline:** top banner "You're offline — changes will sync"; writes queued (TanStack Query persist) or disabled with tooltip. **Permission-denied:** 403 card "You don't have access to this page. Ask an admin." + link home; nav item hidden when SpiceDB denies.               |
| Accessibility  | WCAG 2.2 AA + AODA: contrast >= 4.5:1 text / 3:1 UI, focus ring 2 px secondary, target >= 24x24 (44 on touch), skip link, landmark roles, labels on every input, errors linked via `aria-describedby`, status via `aria-live`, no colour-only meaning (margin badges carry text + icon), keyboard path for every action, reduced motion honoured, focus not obscured (2.4.11), dragging has a button alternative (2.5.7), no re-entry of known data (3.3.7), accessible auth without cognitive test (3.3.8). |
| Language       | EN/FR from day one: next-intl message keys, no hard-coded strings, `lang` attribute, fr-CA number/currency/date (`12,50 $`), French text +30 % width budget, language switch in header and profile, choice persisted to account.                                                                                                                                                                                                                                                                             |
| Breakpoints    | phone < 640, tablet 640–1023, laptop 1024–1439, desktop 1440–1919, large >= 1920. Tables → stacked cards on phone; side panels → bottom sheets; nav → drawer on phone/tablet, rail on laptop, full sidebar on desktop+.                                                                                                                                                                                                                                                                                      |
| Theme          | Light only for admin/super-admin (Ravi rule). Other web surfaces light default; dark optional later via tokens.                                                                                                                                                                                                                                                                                                                                                                                              |
| Margin colours | Wherever margin shows (admin/super-admin only): green >= 50 %, yellow < 50 %, red <= 35 %. Never blocks a quote. Badge = colour + icon + text ("Margin 42 % · Low").                                                                                                                                                                                                                                                                                                                                         |

## Page specs (24)

### 2.1 `/api`

- **File:** `apps/merchant-portal/src/app/(portal)/api/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Merchant owner / merchant staff
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.2 `/billing/invoices/[invoice_id]`

- **File:** `apps/merchant-portal/src/app/(portal)/billing/invoices/[invoice_id]/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Merchant owner / merchant staff
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** `/v1/merchant/billing/invoices/{id}`
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.3 `/billing`

- **File:** `apps/merchant-portal/src/app/(portal)/billing/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Merchant owner / merchant staff
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** `/v1/merchant/billing/invoices`, `/v1/merchant/billing/overview`
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.4 `/book`

- **File:** `apps/merchant-portal/src/app/(portal)/book/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Merchant owner / merchant staff
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.5 `/bulk`

- **File:** `apps/merchant-portal/src/app/(portal)/bulk/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Merchant owner / merchant staff
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.6 `/dashboard`

- **File:** `apps/merchant-portal/src/app/(portal)/dashboard/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Merchant owner / merchant staff
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** `/v1/merchant/bulk/upload`, `/v1/merchant/bulk/{id}/confirm`, `/v1/merchant/dashboard`, `/v1/merchant/memberships`, `/v1/merchant/orders/{id}/delivery-options`, `/v1/merchant/orders/{id}/parcels`, `/v1/merchant/pricing/route-pricing`, `/v1/merchant/route-import-profiles`, `/v1/merchant/route-imports`, `/v1/merchant/route-imports/upload`, `/v1/merchant/route-imports/{id}`, `/v1/merchant/route-imports/{id}/confirm`
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.7 `/help`

- **File:** `apps/merchant-portal/src/app/(portal)/help/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Merchant owner / merchant staff
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.8 `/notifications`

- **File:** `apps/merchant-portal/src/app/(portal)/notifications/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Merchant owner / merchant staff
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/notifications/inbox`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.9 `/orders/[order_id]`

- **File:** `apps/merchant-portal/src/app/(portal)/orders/[order_id]/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Merchant owner / merchant staff
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/merchant/orders/{id}/360`, `/v1/merchant/orders/{id}/tracking`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.10 `/orders`

- **File:** `apps/merchant-portal/src/app/(portal)/orders/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Merchant owner / merchant staff
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/merchant/orders`, `/v1/merchant/orders/bulk`, `/v1/merchant/orders/dashboard`, `/v1/merchant/orders/labels/bulk`, `/v1/merchant/orders/pickup-list.pdf`, `/v1/merchant/orders/pickup-manifest.pdf`, `/v1/merchant/orders/{id}/360`, `/v1/merchant/orders/{id}/cancel`, `/v1/merchant/orders/{id}/compliance-dossier.pdf`, `/v1/merchant/orders/{id}/external-ids`, `/v1/merchant/orders/{id}/external-ids/{id}`, `/v1/merchant/orders/{id}/labels.pdf`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.11 `/pricing/how-we-price`

- **File:** `apps/merchant-portal/src/app/(portal)/pricing/how-we-price/page.tsx`
- **Purpose:** Build or show a price from the live rate card version
- **Role:** Merchant owner / merchant staff
- **Layout:** Two-column: form left, sticky price summary right (stacks on phone)
- **Components:** Form, AddressAutocomplete, VehiclePicker, QuoteLines, MarginBadge (admin only), Button
- **Key actions:** Get quote, edit lines, save draft, convert to order
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Address inside Toronto+150 km else "Outside service area"; weight/vehicle rule; dangerous goods refused
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.12 `/referrals`

- **File:** `apps/merchant-portal/src/app/(portal)/referrals/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Merchant owner / merchant staff
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/merchant/referrals`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.13 `/reports`

- **File:** `apps/merchant-portal/src/app/(portal)/reports/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Merchant owner / merchant staff
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** `/v1/merchant/reports/overview`, `/v1/merchant/reports/saved`
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.14 `/routes/[job_id]`

- **File:** `apps/merchant-portal/src/app/(portal)/routes/[job_id]/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Merchant owner / merchant staff
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/merchant/route-imports/{id}`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.15 `/routes`

- **File:** `apps/merchant-portal/src/app/(portal)/routes/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Merchant owner / merchant staff
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/merchant/route-imports`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.16 `/settings`

- **File:** `apps/merchant-portal/src/app/(portal)/settings/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Merchant owner / merchant staff
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** `/v1/merchant/settings/overview`
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.17 `/shopify`

- **File:** `apps/merchant-portal/src/app/(portal)/shopify/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Merchant owner / merchant staff
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.18 `/team`

- **File:** `apps/merchant-portal/src/app/(portal)/team/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Merchant owner / merchant staff
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/merchant/contacts`, `/v1/merchant/team`, `/v1/merchant/team/activity`, `/v1/merchant/team/overview`, `/v1/merchant/team/roles`, `/v1/merchant/team/two-factor`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.19 `/track`

- **File:** `apps/merchant-portal/src/app/(portal)/track/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Merchant owner / merchant staff
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** `/v1/merchant/tracking/dashboard`
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.20 `/impersonate`

- **File:** `apps/merchant-portal/src/app/impersonate/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Merchant owner / merchant staff
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.21 `/onboarding`

- **File:** `apps/merchant-portal/src/app/onboarding/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Merchant owner / merchant staff
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.22 `/`

- **File:** `apps/merchant-portal/src/app/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Merchant owner / merchant staff
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** `/v1/notifications/inbox`
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.23 `/sign-in/[[...sign-in]]`

- **File:** `apps/merchant-portal/src/app/sign-in/[[...sign-in]]/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Merchant owner / merchant staff
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.24 `/sign-up/[[...sign-up]]`

- **File:** `apps/merchant-portal/src/app/sign-up/[[...sign-up]]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Merchant owner / merchant staff
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 2.25 `/help + /settings/legal`

- **File:** `merchant-portal/src/app/(portal)/help/page.tsx (existing, now content-repo driven); settings/legal/page.tsx` (planned, doc 68)
- **Purpose:** In-portal help panel and Legal & billing settings: signed MSA/DPA/AUP versions, subprocessors, rate card, Interac instructions, re-consent prompt on material change
- **Role:** Merchant owner/admin
- **Layout:** PorterChain header, breadcrumb, left section nav (desktop) / section select (phone), article, "Last updated · version" line, related policies, Contact CTA
- **Components:** HelpPanel, SignedAgreementsTable, ReconsentModal
- **Key actions:** Accept new version (named signer), download DPA
- **Data (API):** content `GET /v1/trust/help?persona=&locale=` / `GET /v1/trust/policies/:slug?version=` (doc 68 §6)
- **Validation / errors:** Network error → cached copy with date
- **States:** loading; offline cached; re-consent required
- **Responsive:** Phone single column with sticky search; tablet 2 col; laptop+ 3 col (nav, article, on-this-page)
- **A11y / i18n / theme:** WCAG 2.2 AA, one `<h1>`, skip link, plain language; EN/FR from `content/trust/` (FR "translation pending" banner until D-68-2); legal text marked DRAFT until lawyer sign-off
