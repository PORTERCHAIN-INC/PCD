# 41 · UI page specs — Expo driver app (iOS + Android)

Read-only from code. Tokens/components: doc 40 (React Native column). Flows: doc 42. Plan context: docs 26.

## Every screen inherits

| Concern  | Rule                                                                                                                                                                                                                                                                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| States   | Loading skeleton; Empty state with action; Error card + Retry; **Offline-first**: banner + local queue (MMKV/SQLite) auto-sync; Permission-denied: OS permission explainer screen before system prompt (location, camera, notifications, Bluetooth) with "Open Settings" fallback; 403 from API → "Your account can't do this" + support. |
| A11y     | WCAG 2.2 AA / AODA mapped to mobile: VoiceOver/TalkBack labels on every touchable, 44 pt targets, Dynamic Type up to 200 %, contrast 4.5:1, reduce-motion, haptic + text (never colour only).                                                                                                                                             |
| Language | EN/FR via i18n keys, device locale default, switch in Settings, fr-CA formats.                                                                                                                                                                                                                                                            |
| Devices  | iPhone SE → Pro Max, Android 360–480 dp; tablets (iPad, Android 10") get two-pane layout; landscape supported on tablet; foldables use window size classes.                                                                                                                                                                               |
| Theme    | Light default following tokens; dark follows OS (driver night driving) using the same token names.                                                                                                                                                                                                                                        |

### 6.1 Sign in

- **File:** `apps/mobile-driver/src/screens/SignInScreen.tsx`
- **Purpose:** Driver login (Keycloak OIDC PKCE + passkey)
- **Layout:** Logo, form, passkey button
- **Components:** TextInput, Button, PasskeyButton
- **Key actions:** Sign in, forgot password
- **Data (API):** Keycloak `/realms/porterchain/protocol/openid-connect/*`, `/v1/driver/me`
- **Validation / errors:** "Email or password is wrong"; account suspended message
- **Screen-specific states:** Offline: "Connect to sign in"

### 6.2 Consent

- **File:** `apps/mobile-driver/src/screens/ConsentScreen.tsx`
- **Purpose:** ESA electronic-monitoring notice + location/camera consent
- **Layout:** Scroll text, checkboxes, Accept
- **Components:** ScrollView, Checkbox, Button
- **Key actions:** Accept, read policy
- **Data (API):** `/v1/driver/consents`
- **Validation / errors:** All required boxes checked
- **Screen-specific states:** Denied location → explainer, can't go online

### 6.3 Today

- **File:** `apps/mobile-driver/src/screens/TodayScreen.tsx`
- **Purpose:** Shift home: online toggle, offers, today's stops
- **Layout:** Header status, offer card, stop list, map preview
- **Components:** OnlineSwitch, OfferCard (countdown), StopRow, MapLibre RN
- **Key actions:** Go online/offline, accept/decline offer, open job
- **Data (API):** `/v1/driver/jobs`, `/v1/driver/offers`, GPS → Redis live feed
- **Validation / errors:** Can't accept with expired docs (box truck: BOL/CVOR/insurance)
- **Screen-specific states:** Empty: "No jobs yet — stay online"; offline queues accept

### 6.4 Job

- **File:** `apps/mobile-driver/src/screens/JobScreen.tsx`
- **Purpose:** Run one job: navigate, arrive, POD
- **Layout:** Map top, step sheet bottom (pickup→drop)
- **Components:** MapLibre, StepSheet, CameraCapture, SignaturePad, BarcodeScan, TempLog (cooler, BLE)
- **Key actions:** Navigate (Valhalla truck route), arrive, scan, photo, signature, fail with reason
- **Data (API):** `/v1/driver/jobs/{id}`, `/v1/driver/jobs/{id}/pod`, `/v1/driver/jobs/{id}/events`
- **Validation / errors:** POD requires photo + name or signature; photo hash + GPS + time (tamper-evident)
- **Screen-specific states:** Offline POD stored encrypted, uploaded later with original timestamp

### 6.5 Inbox

- **File:** `apps/mobile-driver/src/screens/InboxPage.tsx`
- **Purpose:** Messages and alerts from dispatch
- **Layout:** List + thread
- **Components:** MessageList, Composer
- **Key actions:** Read, reply, call dispatch
- **Data (API):** `/v1/notifications/inbox`
- **Validation / errors:** Message <= 1000 chars
- **Screen-specific states:** Empty: "No messages"

### 6.6 Availability

- **File:** `apps/mobile-driver/src/screens/AvailabilityPage.tsx`
- **Purpose:** Set weekly availability and shifts
- **Layout:** Week grid
- **Components:** WeekGrid, TimeRangePicker
- **Key actions:** Add/remove slot
- **Data (API):** `/v1/driver/availability`
- **Validation / errors:** No overlaps (DB exclusion constraint)
- **Screen-specific states:** Conflict error inline

### 6.7 Pay

- **File:** `apps/mobile-driver/src/screens/PayPage.tsx`
- **Purpose:** DPWRA pay statements and earnings
- **Layout:** Period summary + list
- **Components:** KpiCard, StatementRow, PdfViewer
- **Key actions:** View statement, download PDF
- **Data (API):** `/v1/driver/earnings`, `/v1/driver/statements`
- **Validation / errors:** —
- **Screen-specific states:** Empty: "No pay periods yet"

### 6.8 Documents

- **File:** `apps/mobile-driver/src/screens/DocumentsPage.tsx`
- **Purpose:** Licence, insurance, CVOR, vehicle docs with expiry
- **Layout:** List with expiry badges
- **Components:** DocRow, CameraCapture, ExpiryBadge
- **Key actions:** Upload, replace
- **Data (API):** `/v1/driver/documents`
- **Validation / errors:** jpg/png/pdf <= 10 MB; expiry date in future
- **Screen-specific states:** Expiring < 30 days: yellow; expired: red + blocks offers

### 6.9 Me

- **File:** `apps/mobile-driver/src/screens/MeScreen.tsx`
- **Purpose:** Driver hub: profile, pay, docs, help, settings
- **Layout:** Menu list
- **Components:** ListItem, Avatar
- **Key actions:** Navigate
- **Data (API):** `/v1/driver/me`
- **Validation / errors:** —
- **Screen-specific states:** —

### 6.10 Profile

- **File:** `apps/mobile-driver/src/screens/ProfilePage.tsx`
- **Purpose:** Edit personal and vehicle info
- **Layout:** Form
- **Components:** TextInput, VehiclePicker
- **Key actions:** Save
- **Data (API):** `/v1/driver/me`
- **Validation / errors:** Phone E.164, plate format
- **Screen-specific states:** —

### 6.11 Settings

- **File:** `apps/mobile-driver/src/screens/SettingsPage.tsx`
- **Purpose:** Language, notifications, theme, sign out, delete account
- **Layout:** Grouped list
- **Components:** Switch, Select
- **Key actions:** Toggle, sign out, request deletion
- **Data (API):** `/v1/driver/settings`
- **Validation / errors:** —
- **Screen-specific states:** —

### 6.12 Help

- **File:** `apps/mobile-driver/src/screens/HelpPage.tsx`
- **Purpose:** FAQ, emergency, contact dispatch
- **Layout:** List + emergency button
- **Components:** Accordion, EmergencyButton
- **Key actions:** Call 911 / dispatch, open ticket
- **Data (API):** `/v1/support/tickets`
- **Validation / errors:** —
- **Screen-specific states:** Emergency works offline (tel:)
