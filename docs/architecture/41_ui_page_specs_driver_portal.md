# 41 · UI page specs — Driver web portal

Generated from code (25 `page.tsx` under `apps/driver-portal/src/app`) and cross-checked against doc 29 inventory. Read-only on code. Design tokens and components: doc 40. Flows: doc 42.

Default role: **Driver (contractor)**.

## Every page on this surface inherits

| Concern        | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| States         | **Loading:** skeleton matching layout (no spinners > 300 ms without skeleton). **Empty:** `EmptyState` with icon, one-line reason, primary action. **Error:** inline `Alert` with plain message + Retry + support ref id. **Offline:** top banner "You're offline — changes will sync"; writes queued (TanStack Query persist) or disabled with tooltip. **Permission-denied:** 403 card "You don't have access to this page. Ask an admin." + link home; nav item hidden when SpiceDB denies.               |
| Accessibility  | WCAG 2.2 AA + AODA: contrast >= 4.5:1 text / 3:1 UI, focus ring 2 px secondary, target >= 24x24 (44 on touch), skip link, landmark roles, labels on every input, errors linked via `aria-describedby`, status via `aria-live`, no colour-only meaning (margin badges carry text + icon), keyboard path for every action, reduced motion honoured, focus not obscured (2.4.11), dragging has a button alternative (2.5.7), no re-entry of known data (3.3.7), accessible auth without cognitive test (3.3.8). |
| Language       | EN/FR from day one: next-intl message keys, no hard-coded strings, `lang` attribute, fr-CA number/currency/date (`12,50 $`), French text +30 % width budget, language switch in header and profile, choice persisted to account.                                                                                                                                                                                                                                                                             |
| Breakpoints    | phone < 640, tablet 640–1023, laptop 1024–1439, desktop 1440–1919, large >= 1920. Tables → stacked cards on phone; side panels → bottom sheets; nav → drawer on phone/tablet, rail on laptop, full sidebar on desktop+.                                                                                                                                                                                                                                                                                      |
| Theme          | Light only for admin/super-admin (Ravi rule). Other web surfaces light default; dark optional later via tokens.                                                                                                                                                                                                                                                                                                                                                                                              |
| Margin colours | Wherever margin shows (admin/super-admin only): green >= 50 %, yellow < 50 %, red <= 35 %. Never blocks a quote. Badge = colour + icon + text ("Margin 42 % · Low").                                                                                                                                                                                                                                                                                                                                         |

## Page specs (25)

### 4.1 `/account`

- **File:** `apps/driver-portal/src/app/account/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Driver (contractor)
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.2 `/communications`

- **File:** `apps/driver-portal/src/app/communications/page.tsx`
- **Purpose:** Sales, content and communications
- **Role:** Driver (contractor)
- **Layout:** List/board + editor or calendar
- **Components:** Kanban, Calendar, RichTextEditor, ChannelBadge, ClickToChat (free WhatsApp)
- **Key actions:** Create, schedule, publish, reply (agent drafts, human sends)
- **Data (API):** `/v1/communications`, `/v1/dashboard`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/me`, `/v1/performance`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`, `/v1/vehicle`
- **Validation / errors:** Title required; slug unique; consent check before marketing send (CASL)
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.3 `/dashboard`

- **File:** `apps/driver-portal/src/app/dashboard/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Driver (contractor)
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** `/v1/dashboard`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/me`, `/v1/performance`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`, `/v1/vehicle`
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.4 `/documents`

- **File:** `apps/driver-portal/src/app/documents/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Driver (contractor)
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.5 `/earnings`

- **File:** `apps/driver-portal/src/app/earnings/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Driver (contractor)
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** `/v1/dashboard`, `/v1/earnings`, `/v1/earnings/statements`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/me`, `/v1/performance`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.6 `/emergency`

- **File:** `apps/driver-portal/src/app/emergency/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Driver (contractor)
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.7 `/impersonate`

- **File:** `apps/driver-portal/src/app/impersonate/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Driver (contractor)
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.8 `/insurance`

- **File:** `apps/driver-portal/src/app/insurance/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Driver (contractor)
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.9 `/jobs/[orderId]`

- **File:** `apps/driver-portal/src/app/jobs/[orderId]/page.tsx`
- **Purpose:** List, create or manage delivery orders
- **Role:** Driver (contractor)
- **Layout:** Toolbar (search, filters, date) + DataTable or form wizard; detail drawer
- **Components:** DataTable, FilterBar, StatusBadge, Stepper, Drawer, Timeline, MapLibre mini-map
- **Key actions:** Create, filter, bulk-select, cancel, reschedule, export CSV, open detail
- **Data (API):** `/v1/dashboard`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/jobs/{id}`, `/v1/me`, `/v1/performance`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`, `/v1/vehicle`
- **Validation / errors:** Required pickup/drop, time window in future, phone E.164; server errors inline per field
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.10 `/jobs`

- **File:** `apps/driver-portal/src/app/jobs/page.tsx`
- **Purpose:** Plan and run jobs, offers and vehicles
- **Role:** Driver (contractor)
- **Layout:** Split: queue list | map | detail panel; keyboard shortcuts
- **Components:** Kanban/List, MapLibre, DriverCard, OfferButton, ConfirmDialog, Toast
- **Key actions:** Assign, re-offer, unassign, mark exception, open driver
- **Data (API):** `/v1/dashboard`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/me`, `/v1/performance`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`, `/v1/vehicle`
- **Validation / errors:** Capacity/vehicle-class checks; box truck blocked without BOL/CVOR/insurance
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.11 `/login/[[...sign-in]]`

- **File:** `apps/driver-portal/src/app/login/[[...sign-in]]/page.tsx`
- **Purpose:** Authenticate the user (Keycloak OIDC + passkey, L-free stack)
- **Role:** Driver (contractor)
- **Layout:** Centred card 420 px, logo, form, footer links
- **Components:** Input, Button, PasskeyButton, Alert, OTP field
- **Key actions:** Sign in with passkey; email+password; forgot password; switch language
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Email format; "Email or password is wrong" (no account enumeration); rate-limit "Too many tries, wait 60 s"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.12 `/monitoring-policy`

- **File:** `apps/driver-portal/src/app/monitoring-policy/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Driver (contractor)
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.13 `/navigation`

- **File:** `apps/driver-portal/src/app/navigation/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Driver (contractor)
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.14 `/onboarding`

- **File:** `apps/driver-portal/src/app/onboarding/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Driver (contractor)
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.15 `/`

- **File:** `apps/driver-portal/src/app/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Driver (contractor)
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.16 `/performance`

- **File:** `apps/driver-portal/src/app/performance/page.tsx`
- **Purpose:** Read KPIs and trends
- **Role:** Driver (contractor)
- **Layout:** KPI grid + charts + table, date range
- **Components:** KpiCard, Chart (line/bar), DateRangePicker, DataTable, ExportButton
- **Key actions:** Change range, drill down, export CSV
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Range <= 366 days
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.17 `/profile`

- **File:** `apps/driver-portal/src/app/profile/page.tsx`
- **Purpose:** Manage accounts, people and roles
- **Role:** Driver (contractor)
- **Layout:** DataTable + profile page with tabs
- **Components:** DataTable, Avatar, Tabs, RoleSelect (SpiceDB), InviteDialog
- **Key actions:** Invite, edit, suspend, merge duplicates, impersonate (super-admin only, audited)
- **Data (API):** `/v1/dashboard`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/me`, `/v1/performance`, `/v1/profile`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`, `/v1/vehicle`
- **Validation / errors:** Email unique; role must exist in schema.zed; self-demotion blocked
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.18 `/route`

- **File:** `apps/driver-portal/src/app/route/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Driver (contractor)
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.19 `/shift`

- **File:** `apps/driver-portal/src/app/shift/page.tsx`
- **Purpose:** Plan and run jobs, offers and vehicles
- **Role:** Driver (contractor)
- **Layout:** Split: queue list | map | detail panel; keyboard shortcuts
- **Components:** Kanban/List, MapLibre, DriverCard, OfferButton, ConfirmDialog, Toast
- **Key actions:** Assign, re-offer, unassign, mark exception, open driver
- **Data (API):** `/v1/dashboard`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/me`, `/v1/performance`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`, `/v1/vehicle`
- **Validation / errors:** Capacity/vehicle-class checks; box truck blocked without BOL/CVOR/insurance
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.20 `/stops`

- **File:** `apps/driver-portal/src/app/stops/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Driver (contractor)
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.21 `/support`

- **File:** `apps/driver-portal/src/app/support/page.tsx`
- **Purpose:** Raise and resolve problems
- **Role:** Driver (contractor)
- **Layout:** List + conversation/detail thread
- **Components:** DataTable, Thread, FileUpload (photos), StatusBadge, SLA timer
- **Key actions:** Open claim/ticket, reply, attach, escalate, resolve
- **Data (API):** `/v1/dashboard`, `/v1/incidents`, `/v1/jobs`, `/v1/jobs/history`, `/v1/me`, `/v1/performance`, `/v1/ratings`, `/v1/routes/assigned`, `/v1/shift`, `/v1/support`, `/v1/support/hub`, `/v1/vehicle`
- **Validation / errors:** Description min 10 chars; files <= 10 MB jpg/png/pdf
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.22 `/timesheets`

- **File:** `apps/driver-portal/src/app/timesheets/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Driver (contractor)
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.23 `/training`

- **File:** `apps/driver-portal/src/app/training/page.tsx`
- **Purpose:** Configure the platform, integrations or compliance
- **Role:** Driver (contractor)
- **Layout:** Settings layout: left section nav + form cards
- **Components:** Form, Switch, SecretField (masked, copy), StatusDot, AuditTrail
- **Key actions:** Save, rotate key, test connection, export data
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Field-level; destructive changes need confirm
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.24 `/vehicle`

- **File:** `apps/driver-portal/src/app/vehicle/page.tsx`
- **Purpose:** Public/info content page
- **Role:** Driver (contractor)
- **Layout:** Hero + content sections + CTA footer
- **Components:** Header, Section, Card, CTA Button, Footer, LanguageSwitch
- **Key actions:** Read, start quote, contact
- **Data (API):** none direct (server component / static content or child components; confirm in build)
- **Validation / errors:** None (static); 404 page for bad slugs
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR

### 4.25 `/wallet`

- **File:** `apps/driver-portal/src/app/wallet/page.tsx`
- **Purpose:** Money: invoices, credit notes, payments, statements, payouts
- **Role:** Driver (contractor)
- **Layout:** Summary KPI row + DataTable + detail with PDF preview
- **Components:** KpiCard, DataTable, MoneyCell (CAD, fr/en format), PdfPreview, StatusBadge, ConfirmDialog
- **Key actions:** Download PDF, send, record Interac payment, issue credit note (approval card if over cap)
- **Data (API):** `/v1/availability`, `/v1/availability/schedule`, `/v1/bonuses`, `/v1/communications`, `/v1/communications/notifications/mark-all-read`, `/v1/communications/notifications/{id}/read`, `/v1/communications/offline/retry`, `/v1/dashboard`, `/v1/dispatch/orders/{id}/checklist`, `/v1/dispatch/route`, `/v1/dispatch/stops/checkin`, `/v1/documents`
- **Validation / errors:** Amount > 0, <= invoice balance; HST number format; "Credit note exceeds remaining balance"
- **States:** inherit + page-specific empty text "No items yet" → primary action
- **Responsive:** Phone: single column, sticky primary action bottom; Tablet: 2 col; Laptop+: full layout; Large: max content 1600 px (admin full-bleed)
- **A11y / i18n / theme:** inherit; page `<h1>` matches nav label in EN/FR
