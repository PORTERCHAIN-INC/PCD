# 41 · UI page specs — Admin and super-admin

Generated from code (54 `page.tsx` under `apps/admin/src/app`) and cross-checked against doc 29 inventory. Read-only on code. Design tokens and components: doc 40. Flows: doc 42.

Default role: **Admin (ops staff); super-admin where marked**.

## Every page on this surface inherits

| Concern        | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| States         | **Loading:** skeleton matching layout (no spinners > 300 ms without skeleton). **Empty:** `EmptyState` with icon, one-line reason, primary action. **Error:** inline `Alert` with plain message + Retry + support ref id. **Offline:** top banner "You're offline — changes will sync"; writes queued (TanStack Query persist) or disabled with tooltip. **Permission-denied:** 403 card "You don't have access to this page. Ask an admin." + link home; nav item hidden when SpiceDB denies.               |
| Accessibility  | WCAG 2.2 AA + AODA: contrast >= 4.5:1 text / 3:1 UI, focus ring 2 px secondary, target >= 24x24 (44 on touch), skip link, landmark roles, labels on every input, errors linked via `aria-describedby`, status via `aria-live`, no colour-only meaning (margin badges carry text + icon), keyboard path for every action, reduced motion honoured, focus not obscured (2.4.11), dragging has a button alternative (2.5.7), no re-entry of known data (3.3.7), accessible auth without cognitive test (3.3.8). |
| Language       | EN/FR from day one: next-intl message keys, no hard-coded strings, `lang` attribute, fr-CA number/currency/date (`12,50 $`), French text +30 % width budget, language switch in header and profile, choice persisted to account.                                                                                                                                                                                                                                                                             |
| Breakpoints    | phone < 640, tablet 640–1023, laptop 1024–1439, desktop 1440–1919, large >= 1920. Tables → stacked cards on phone; side panels → bottom sheets; nav → drawer on phone/tablet, rail on laptop, full sidebar on desktop+.                                                                                                                                                                                                                                                                                      |
| Theme          | Light only for admin/super-admin (Ravi rule). Other web surfaces light default; dark optional later via tokens.                                                                                                                                                                                                                                                                                                                                                                                              |
| Margin colours | Wherever margin shows (admin/super-admin only): green >= 50 %, yellow < 50 %, red <= 35 %. Never blocks a quote. Badge = colour + icon + text ("Margin 42 % · Low").                                                                                                                                                                                                                                                                                                                                         |

## Page specs (54)

### 3.1 `/account/security`

- **File:** `apps/admin/src/app/(ops)/account/security/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** `/v1/auth/staff/passkey/register/options`, `/v1/auth/staff/passkey/register/verify`, `/v1/auth/staff/passkeys`, `/v1/auth/staff/passkeys/{id}`, `/v1/auth/staff/sessions`, `/v1/auth/staff/sessions/revoke-others`, `/v1/auth/staff/sessions/{id}`
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.2 `/blog/[id]`

- **File:** `apps/admin/src/app/(ops)/blog/[id]/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/blog/posts/{id}`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.3 `/blog/authors`

- **File:** `apps/admin/src/app/(ops)/blog/authors/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/blog/authors`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.4 `/blog/new`

- **File:** `apps/admin/src/app/(ops)/blog/new/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.5 `/blog`

- **File:** `apps/admin/src/app/(ops)/blog/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/blog/posts`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.6 `/booking-drafts/[id]`

- **File:** `apps/admin/src/app/(ops)/booking-drafts/[id]/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/admin/booking-drafts/{id}`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.7 `/booking-drafts`

- **File:** `apps/admin/src/app/(ops)/booking-drafts/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/admin/booking-drafts`, `/v1/admin/booking-drafts/analytics`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.8 `/claims/[id]`

- **File:** `apps/admin/src/app/(ops)/claims/[id]/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** `/v1/admin/claims/{id}`
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.9 `/claims`

- **File:** `apps/admin/src/app/(ops)/claims/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** `/v1/admin/claims`, `/v1/admin/claims/dashboard`
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.10 `/customers/[id]`

- **File:** `apps/admin/src/app/(ops)/customers/[id]/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/admin/customers/{id}`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.11 `/customers`

- **File:** `apps/admin/src/app/(ops)/customers/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/admin`, `/v1/admin/customers`, `/v1/admin/customers/stats`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.12 `/dashboard`

- **File:** `apps/admin/src/app/(ops)/dashboard/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** `/v1/admin/dashboard/center`
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.13 `/dispatch/[view]`

- **File:** `apps/admin/src/app/(ops)/dispatch/[view]/page.tsx`
- **Purpose:** Plan and run jobs, offers and vehicles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Split: queue list | map | detail panel; keyboard shortcuts
- **Components:** Kanban/List, MapLibre, DriverCard, OfferButton, ConfirmDialog, Toast
- **Key actions:** Assign, re-offer, unassign, mark exception, open driver
- **Data (API):** `/v1/admin/operations/dispatch`
- **Validation / errors:** Capacity/vehicle-class checks; box truck blocked without BOL/CVOR/insurance
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.14 `/dispatch`

- **File:** `apps/admin/src/app/(ops)/dispatch/page.tsx`
- **Purpose:** Plan and run jobs, offers and vehicles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Split: queue list | map | detail panel; keyboard shortcuts
- **Components:** Kanban/List, MapLibre, DriverCard, OfferButton, ConfirmDialog, Toast
- **Key actions:** Assign, re-offer, unassign, mark exception, open driver
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Capacity/vehicle-class checks; box truck blocked without BOL/CVOR/insurance
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.15 `/drivers/[id]`

- **File:** `apps/admin/src/app/(ops)/drivers/[id]/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** `/v1/admin/drivers/{id}`
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.16 `/drivers`

- **File:** `apps/admin/src/app/(ops)/drivers/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.17 `/finance/analytics`

- **File:** `apps/admin/src/app/(ops)/finance/analytics/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.18 `/finance/cash`

- **File:** `apps/admin/src/app/(ops)/finance/cash/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.19 `/finance/driver-pay`

- **File:** `apps/admin/src/app/(ops)/finance/driver-pay/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.20 `/finance/invoices/[id]`

- **File:** `apps/admin/src/app/(ops)/finance/invoices/[id]/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** `/v1/admin/finance/invoices/{id}`
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.21 `/finance/invoices`

- **File:** `apps/admin/src/app/(ops)/finance/invoices/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.22 `/finance`

- **File:** `apps/admin/src/app/(ops)/finance/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.23 `/finance/payments`

- **File:** `apps/admin/src/app/(ops)/finance/payments/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.24 `/finance/reports`

- **File:** `apps/admin/src/app/(ops)/finance/reports/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.25 `/finance/tax-registration`

- **File:** `apps/admin/src/app/(ops)/finance/tax-registration/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.26 `/inbox`

- **File:** `apps/admin/src/app/(ops)/inbox/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.27 `/leads/[id]`

- **File:** `apps/admin/src/app/(ops)/leads/[id]/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/leads/{id}`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.28 `/leads/agent`

- **File:** `apps/admin/src/app/(ops)/leads/agent/page.tsx`
- **Purpose:** Supervise in-house AI agents and approve the six human cases
- **Role:** Super-admin
- **Layout:** Inbox list + ApprovalCard detail with evidence
- **Components:** ApprovalCard, DiffView, ConfidenceMeter, KillSwitch, AuditTrail
- **Key actions:** Approve, reject with reason, edit then approve, pause agent
- **Data (API):** `/v1/admin/leads/agent`
- **Validation / errors:** Reason required on reject; kill switch needs confirm + 2FA
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.29 `/leads/attribution`

- **File:** `apps/admin/src/app/(ops)/leads/attribution/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/marketing/lead-attribution`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.30 `/leads/calendar`

- **File:** `apps/admin/src/app/(ops)/leads/calendar/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/leads/calendar`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.31 `/leads`

- **File:** `apps/admin/src/app/(ops)/leads/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/leads`, `/v1/admin/leads/agent`, `/v1/admin/leads/bulk`, `/v1/admin/leads/calendar{id}`, `/v1/admin/leads/metrics`, `/v1/admin/leads/pipeline{id}`, `/v1/admin/leads/privacy/ropa`, `/v1/admin/leads/referral-credits{id}`, `/v1/admin/leads/reply-channels`, `/v1/admin/leads/rescore`, `/v1/admin/leads/speed`, `/v1/admin/leads/suppressions/{id}`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.32 `/leads/pipeline`

- **File:** `apps/admin/src/app/(ops)/leads/pipeline/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/admin/leads/pipeline`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.33 `/leads/today`

- **File:** `apps/admin/src/app/(ops)/leads/today/page.tsx`
- **Purpose:** Plan and run jobs, offers and vehicles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Split: queue list | map | detail panel; keyboard shortcuts
- **Components:** Kanban/List, MapLibre, DriverCard, OfferButton, ConfirmDialog, Toast
- **Key actions:** Assign, re-offer, unassign, mark exception, open driver
- **Data (API):** `/v1/admin/leads/today`
- **Validation / errors:** Capacity/vehicle-class checks; box truck blocked without BOL/CVOR/insurance
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.34 `/merchants/[id]`

- **File:** `apps/admin/src/app/(ops)/merchants/[id]/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/admin/merchants/{id}`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.35 `/merchants/duplicates`

- **File:** `apps/admin/src/app/(ops)/merchants/duplicates/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.36 `/merchants`

- **File:** `apps/admin/src/app/(ops)/merchants/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/admin/merchants`, `/v1/admin/merchants/stats`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.37 `/notifications/delivery`

- **File:** `apps/admin/src/app/(ops)/notifications/delivery/page.tsx`
- **Purpose:** Show live position, ETA and timeline
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Full-bleed MapLibre map with side/bottom sheet timeline
- **Components:** MapLibre (self-hosted PMTiles light), Marker, ETA chip, Timeline, ShareLink
- **Key actions:** Share link, call/text driver via masked link, report issue
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Tracking code format; "We can't find that tracking number"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.38 `/notifications`

- **File:** `apps/admin/src/app/(ops)/notifications/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/notifications/inbox`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.39 `/operations`

- **File:** `apps/admin/src/app/(ops)/operations/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** `/v1/admin/operations/dispatch`
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.40 `/orders/[id]`

- **File:** `apps/admin/src/app/(ops)/orders/[id]/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/admin/orders/{id}`, `/v1/admin/orders/{id}/tracking`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.41 `/orders`

- **File:** `apps/admin/src/app/(ops)/orders/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/admin/orders`, `/v1/admin/orders/dashboard`, `/v1/admin/orders/{id}/pod.zip`, `/v1/admin/orders/{id}/pod/{id}`, `/v1/admin/orders{id}`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.42 `/pricing`

- **File:** `apps/admin/src/app/(ops)/pricing/page.tsx`
- **Purpose:** Build or show a price from the live rate card version
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Two-column: form left, sticky price summary right (stacks on phone)
- **Components:** Form, AddressAutocomplete, VehiclePicker, QuoteLines, MarginBadge (admin only), Button
- **Key actions:** Get quote, edit lines, save draft, convert to order
- **Data (API):** `/v1/admin/merchants`
- **Validation / errors:** Address inside Toronto+150 km else "Outside service area"; weight/vehicle rule; dangerous goods refused
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.43 `/settings`

- **File:** `apps/admin/src/app/(ops)/settings/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Super-admin
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** `/v1/admin/settings/center`
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.44 `/support/[id]`

- **File:** `apps/admin/src/app/(ops)/support/[id]/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** `/v1/admin/support/tickets/{id}`
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.45 `/support`

- **File:** `apps/admin/src/app/(ops)/support/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** `/v1/admin/support/tickets`
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.46 `/system-health`

- **File:** `apps/admin/src/app/(ops)/system-health/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Super-admin
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.47 `/system-tests`

- **File:** `apps/admin/src/app/(ops)/system-tests/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Super-admin
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.48 `/system`

- **File:** `apps/admin/src/app/(ops)/system/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Super-admin
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.49 `/today`

- **File:** `apps/admin/src/app/(ops)/today/page.tsx`
- **Purpose:** Plan and run jobs, offers and vehicles
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Split: queue list | map | detail panel; keyboard shortcuts
- **Components:** Kanban/List, MapLibre, DriverCard, OfferButton, ConfirmDialog, Toast
- **Key actions:** Assign, re-offer, unassign, mark exception, open driver
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Capacity/vehicle-class checks; box truck blocked without BOL/CVOR/insurance
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.50 `/activate-staff`

- **File:** `apps/admin/src/app/activate-staff/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Super-admin
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.51 `/admin/system-health`

- **File:** `apps/admin/src/app/admin/system-health/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Super-admin
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.52 `/admin/system-tests`

- **File:** `apps/admin/src/app/admin/system-tests/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Super-admin
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.53 `/`

- **File:** `apps/admin/src/app/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 3.54 `/sign-in/[[...sign-in]]`

- **File:** `apps/admin/src/app/sign-in/[[...sign-in]]/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Admin (ops staff); super-admin where marked
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR
