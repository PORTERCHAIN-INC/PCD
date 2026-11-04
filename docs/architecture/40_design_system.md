# 40 · Design system (PLANNED) — one system for 5 web portals, website, 2 Expo apps, Shopify

Sources read: `apps/admin/src/app/globals.css`, `packages/ui/src/*`, `packages/mobile-theme/src/tokens.ts`, `packages/maps`, admin `package.json` (Next 16.4.1, React 19.2, Tailwind 4.3, TanStack Query/Table, framer-motion, lucide-react, maplibre-gl 6). Page specs: 41_*. Flows: 42. IA: 16.

## 1. Tokens (single source: `packages/ui/tokens.json` → CSS vars, Tailwind `@theme`, RN `mobile-theme`)

| Token                     | Value                             | Use                                                            |
| ------------------------- | --------------------------------- | -------------------------------------------------------------- |
| `primary`                 | `#0a1628`                         | text, headers, dark buttons                                    |
| `secondary` (brand blue)  | `#1f56d8`                         | links, primary buttons, focus ring (a11y-fixed from `#2563eb`) |
| `gray-bg`                 | `#f0f4f8`                         | page background                                                |
| `surface`                 | `#ffffff`                         | cards                                                          |
| `border`                  | `#e2e8f0`                         | dividers                                                       |
| `muted`                   | `#5b6779`                         | secondary text (4.5:1 on gray-bg)                              |
| `success` / margin-green  | `#15803d` (text) / `#dcfce7` (bg) | margin >= 50 %, delivered                                      |
| `warning` / margin-yellow | `#a16207` / `#fef9c3`             | margin < 50 %, expiring docs                                   |
| `danger` / margin-red     | `#b91c1c` / `#fee2e2`             | margin <= 35 %, errors, expired                                |
| `info`                    | `#0369a1` / `#e0f2fe`             | info banners                                                   |
| `driver-green`            | `#124835`                         | driver app accent                                              |

**Gap fixed by plan:** `mobile-theme` still uses `#2563eb` / `#64748b`; align to `#1f56d8` / `#5b6779` (week 2).

Theme: **light only for admin + super-admin** (`color-scheme: light`, Ravi rule). Website/portals light; apps may follow OS dark using the same token names (`*-dark` set defined, off by default on web).

## 2. Margin band component `MarginBadge`

`>= 50` green "Healthy", `< 50` yellow "Low", `<= 35` red "At risk". Text + icon (CheckCircle / AlertTriangle / AlertOctagon) + colour, `aria-label="Margin 42 percent, low"`. Shown on quote builder, admin pricing, order detail, Today. Row tint in tables. Warn-only, never blocks. Thresholds read from super-admin Settings (50/35).

## 3. Typography

Calibri → Carlito (free metric twin, self-hosted) → Segoe UI → system. Scale (rem): 0.75 caption, 0.875 small, 1 body, 1.125 lg, 1.25 h4, 1.5 h3, 1.875 h2, 2.25 h1, 3 display (website). Line-height 1.5 body / 1.2 headings. Tabular numerals for money/tables. RN: 14/16/22 + Dynamic Type.

## 4. Spacing, radius, elevation, grid

4-pt scale: 4, 8, 12, 16, 24, 32, 48, 64. Radius 8 (inputs), 12 (cards), 16 (sheets), full (pills). Shadows: sm cards, md popovers, lg dialogs. Grid: 4 col phone, 8 tablet, 12 laptop+. Breakpoints: phone <640, tablet 640–1023, laptop 1024–1439, desktop 1440–1919, large >=1920 (admin full-bleed `.admin-page-rail`, content cards max 1600).

## 5. Components (web = shadcn/ui on Radix + Tailwind v4; RN = equivalents; Shopify = Polaris web components)

| Component                                                                                            | Web (shadcn/ui)                                                | React Native                     | Polaris                    |
| ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------- | -------------------------- |
| Button, IconButton                                                                                   | `Button`                                                       | `Pressable` + tokens             | `s-button`                 |
| Input, Textarea, Select, Combobox                                                                    | `Input`, `Select`, `Command`                                   | `TextInput`, bottom-sheet picker | `s-text-field`, `s-select` |
| Date/time                                                                                            | `date-fields`, `datetime-picker-separate` (existing)           | native DateTimePicker            | `s-date-picker`            |
| Address autocomplete                                                                                 | Combobox → self-hosted Pelias/Photon                           | same API                         | `s-text-field`             |
| Dialog, Drawer, Sheet                                                                                | `Dialog`, `Sheet`                                              | `@gorhom/bottom-sheet`           | `s-modal`                  |
| Toast / Alert / Banner                                                                               | `Sonner`, `Alert`                                              | toast lib                        | `s-banner`, toast          |
| Tabs, rail                                                                                           | `Tabs`, `.ops-tab-rail`                                        | top tabs                         | `s-tabs`                   |
| DataTable                                                                                            | TanStack Table + shadcn                                        | FlashList cards                  | `s-table`                  |
| EmptyState, Loading                                                                                  | `packages/ui/empty-state`, `loading`                           | same names                       | `s-empty-state`            |
| Nav                                                                                                  | `app-nav`, `nav-dropdown`, `account-menu`, `notification-bell` | tab bar + stack                  | App Bridge nav             |
| QuoteLines                                                                                           | `packages/ui/quote-lines`                                      | port                             | custom                     |
| Chart                                                                                                | `report-chart` (Recharts)                                      | Victory Native                   | Polaris Viz                |
| ApprovalCard, MarginBadge, StatusBadge, MoneyCell, Timeline, PdfPreview, SignaturePad, CameraCapture | new in `packages/ui`                                           | RN equivalents                   | `s-card`                   |

Rules: every component ships EN/FR strings via props, keyboard + screen-reader tested (axe + Playwright in CI), Storybook-free docs page in admin `/system-tests`.

## 6. Icons

lucide-react (web) / lucide-react-native (apps); 16/20/24 px, stroke 1.75; decorative `aria-hidden`; meaningful have labels. Polaris icons in Shopify.

## 7. Motion

framer-motion + View Transitions (`view-transition.tsx`, `customer-motion` package). Durations 120 (hover), 200 (enter), 300 (sheet). Ease-out. `prefers-reduced-motion` → opacity only. No auto-playing motion > 5 s.

## 8. Maps

MapLibre GL JS 6 (web) / MapLibre React Native; **self-hosted PMTiles** (Protomaps OSM build, Ontario extract) on droplet/Oracle with Ubuntu origin; light style (`porterchain-light`: gray-bg land, white roads, `#1f56d8` route, `#0a1628` labels). Markers: driver (vehicle icon + heading), pickup (P), drop (D), exception (red). Clustering > 50 markers. Route lines from OSRM (cars) / Valhalla 3.9 (truck). Live GPS from Redis via WebSocket. A11y: list view alternative of every map, keyboard pan/zoom, attribution visible. No Google/Mapbox.

## 9. Charts

Recharts (web), Victory Native (RN). Palette: blue `#1f56d8`, navy `#0a1628`, teal `#0f766e`, amber `#a16207`, gray `#94a3b8`; margin charts use the band colours with threshold lines at 50 and 35. Every chart has a data-table toggle and summary sentence.

## 10. Tables pattern

Sticky header, column visibility, sort, server pagination (50), saved filters, bulk-select bar, row click → drawer, `.ops-table-scroll`, phone → cards. Money right-aligned tabular. Export CSV. Empty / loading skeleton rows / error row.

## 11. Forms pattern

React Hook Form + Zod (schemas shared with API OpenAPI types); label above field; required marked "(required)"; inline errors on blur + summary at top on submit with links (3.3.1); never clear input on error; autosave drafts for long forms; destructive = confirm dialog naming the thing; money inputs CAD with fr/en formats.

## 12. Admin + super-admin information architecture (from doc 16)

| Group                   | Pages (routes in 41_ui_page_specs_admin)                                                                        |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| Today                   | queue, exceptions, **approvals inbox** (6 human cases)                                                          |
| Dispatch                | plan, live map, fleet, box truck, cooler runs                                                                   |
| Orders + Claims         | orders, order detail, claims                                                                                    |
| Accounts                | merchants, customers, duplicates                                                                                |
| Sales                   | booking drafts, leads (today, pipeline, calendar, attribution, lead agent), WhatsApp inbox (free click-to-chat) |
| Finance                 | cash, invoices, credit notes, payments, driver pay, GST/HST, tax registration, reports                          |
| Support                 | tickets                                                                                                         |
| Content + comms         | blog, blog authors, notifications, notification delivery                                                        |
| **Super-admin:** System | health, services, diagnostics, system tests                                                                     |
| Agents                  | runs, autonomy ladder, kill switch                                                                              |
| Compliance              | retention, privacy requests, breach log, consent, CVOR/insurance expiry                                         |
| Settings                | margin bands 50/35, spend caps, approval caps, tax registration                                                 |
| Staff + roles           | SpiceDB roles, impersonation (audited, humans only)                                                             |
| Insights                | investor/visitor metrics                                                                                        |

Shell: left sidebar (desktop/large), icon rail (laptop), drawer (tablet/phone); top bar = global search (Cmd-K), notification bell, language, account. One nav source generated from `schema.zed`.

## 13. Devices

Phone, tablet, laptop, desktop, large screen, plus: driver tablets in vehicle mount (landscape two-pane), warehouse kiosk (large touch), keyboard-only, screen readers (NVDA, JAWS, VoiceOver, TalkBack), 200 % zoom, PWA install for portals with offline shell.
