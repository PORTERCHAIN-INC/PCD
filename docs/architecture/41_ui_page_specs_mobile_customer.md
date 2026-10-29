# 41 · UI page specs — Expo customer app (iOS + Android)

Read-only from code. Tokens/components: doc 40 (React Native column). Flows: doc 42. Plan context: docs 25.

## Every screen inherits

| Concern  | Rule                                                                                                                                                                                                                                                                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| States   | Loading skeleton; Empty state with action; Error card + Retry; **Offline-first**: banner + local queue (MMKV/SQLite) auto-sync; Permission-denied: OS permission explainer screen before system prompt (location, camera, notifications, Bluetooth) with "Open Settings" fallback; 403 from API → "Your account can't do this" + support. |
| A11y     | WCAG 2.2 AA / AODA mapped to mobile: VoiceOver/TalkBack labels on every touchable, 44 pt targets, Dynamic Type up to 200 %, contrast 4.5:1, reduce-motion, haptic + text (never colour only).                                                                                                                                             |
| Language | EN/FR via i18n keys, device locale default, switch in Settings, fr-CA formats.                                                                                                                                                                                                                                                            |
| Devices  | iPhone SE → Pro Max, Android 360–480 dp; tablets (iPad, Android 10") get two-pane layout; landscape supported on tablet; foldables use window size classes.                                                                                                                                                                               |
| Theme    | Light default following tokens; dark follows OS (driver night driving) using the same token names.                                                                                                                                                                                                                                        |

### 7.1 Onboarding

- **File:** `apps/mobile-customer/src/screens/OnboardingScreen.tsx`
- **Purpose:** First-run intro + permissions
- **Layout:** 3 swipe cards
- **Components:** Pager, Button
- **Key actions:** Skip, continue, allow notifications
- **Data (API):** —
- **Validation / errors:** —
- **Screen-specific states:** —

### 7.2 Sign in

- **File:** `apps/mobile-customer/src/screens/SignInScreen.tsx`
- **Purpose:** Customer login (Keycloak customer realm, passkey) — fix: currently points to admin login
- **Layout:** Form
- **Components:** TextInput, PasskeyButton, AppleSignIn
- **Key actions:** Sign in, guest continue
- **Data (API):** Keycloak OIDC, `/v1/customer/me`
- **Validation / errors:** Generic auth error
- **Screen-specific states:** Offline banner

### 7.3 Home

- **File:** `apps/mobile-customer/src/screens/HomeScreen.tsx`
- **Purpose:** Quick book + active deliveries
- **Layout:** Hero CTA, active list
- **Components:** DeliveryCard, Button
- **Key actions:** Book, open tracking
- **Data (API):** `/v1/customer/orders`
- **Validation / errors:** —
- **Screen-specific states:** Empty: "Send your first delivery"

### 7.4 Book

- **File:** `apps/mobile-customer/src/screens/BookScreen.tsx`
- **Purpose:** Quote and book (Stripe for retail, real payment only)
- **Layout:** Stepper: addresses → vehicle → time → pay
- **Components:** AddressAutocomplete, VehiclePicker, QuoteLines, StripePaymentSheet
- **Key actions:** Get quote, pay, book
- **Data (API):** `/v1/quotes`, `/v1/customer/orders`, Stripe PaymentIntent
- **Validation / errors:** Service area, time window, card errors from Stripe; remove test checkout path
- **Screen-specific states:** Quote expired → refresh

### 7.5 Track

- **File:** `apps/mobile-customer/src/screens/TrackScreen.tsx`
- **Purpose:** Live map + timeline; Live Activity / Android live notification
- **Layout:** Map + bottom sheet
- **Components:** MapLibre RN, Timeline, ETA chip
- **Key actions:** Share, contact, report issue
- **Data (API):** `/v1/tracking/{code}`, live feed
- **Validation / errors:** Bad code message
- **Screen-specific states:** Offline shows last known

### 7.6 Activity

- **File:** `apps/mobile-customer/src/screens/ActivityScreen.tsx`
- **Purpose:** Past orders, invoices, receipts
- **Layout:** List
- **Components:** OrderRow, PdfViewer
- **Key actions:** Open, rebook, download receipt, open claim
- **Data (API):** `/v1/customer/orders`, `/v1/customer/invoices`
- **Validation / errors:** —
- **Screen-specific states:** Empty state

### 7.7 Alerts

- **File:** `apps/mobile-customer/src/screens/AlertsScreen.tsx`
- **Purpose:** Notification centre
- **Layout:** List
- **Components:** AlertRow
- **Key actions:** Open, mark read
- **Data (API):** `/v1/notifications/inbox`
- **Validation / errors:** —
- **Screen-specific states:** Empty: "You're all caught up"

### 7.8 Account

- **File:** `apps/mobile-customer/src/screens/AccountScreen.tsx`
- **Purpose:** Profile, addresses, language, delete account
- **Layout:** Grouped list
- **Components:** ListItem, Switch
- **Key actions:** Edit, sign out, delete account (Apple rule)
- **Data (API):** `/v1/customer/me`
- **Validation / errors:** —
- **Screen-specific states:** —

### 7.9 `Settings → Help & Legal`

- **File:** `mobile customer app` (planned, doc 68)
- **Purpose:** Help articles (bundled JSON + web view), policies with version, Delete account (Apple 5.1.1(v)), notification consents
- **Role:** Customer
- **Layout:** PorterChain header, breadcrumb, left section nav (desktop) / section select (phone), article, "Last updated · version" line, related policies, Contact CTA
- **Components:** HelpList, PolicyView, DeleteAccount
- **Key actions:** Delete account, change consents
- **Data (API):** content `GET /v1/trust/help?persona=&locale=` / `GET /v1/trust/policies/:slug?version=` (doc 68 §6)
- **Validation / errors:** Network error → cached copy with date
- **States:** loading; offline cached; re-consent required
- **Responsive:** Phone single column with sticky search; tablet 2 col; laptop+ 3 col (nav, article, on-this-page)
- **A11y / i18n / theme:** WCAG 2.2 AA, one `<h1>`, skip link, plain language; EN/FR from `content/trust/` (FR "translation pending" banner until D-68-2); legal text marked DRAFT until lawyer sign-off
