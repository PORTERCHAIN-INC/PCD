# Mobile UI Report

**Last verified:** 2026-07-04  
**Design system:** [MOBILE_DESIGN_SYSTEM.md](./MOBILE_DESIGN_SYSTEM.md)  
**Packages:** `@porterchain/mobile-ui`, `@porterchain/mobile-theme`, `@porterchain/mobile-components`, `@porterchain/mobile-performance`

---

## Executive Summary

Both mobile apps use the shared Porterchain mobile design system and have full feature screen stacks. The old scaffold-era state is obsolete.

| App | UI Coverage | Verdict |
| --- | ----------- | ------- |
| Driver | High | Jobs, POD, navigation, shift, earnings, support, SOS, offline, notifications |
| Customer | High | Quote/booking, checkout, tracking, notifications, invoices, receipts, support, claims |

**UI posture:** production-styled and consistent enough for beta. Remaining gaps are customer store branding assets, per-screen accessibility audit, payment retry polish, and a few form-validation refinements.

---

## Design System Stack

| Package | Role |
| ------- | ---- |
| `@porterchain/mobile-theme` | Light/dark tokens, spacing, typography, RTL state |
| `@porterchain/mobile-ui` | Core primitives: buttons, cards, forms, states, charts, timelines, sheets |
| `@porterchain/mobile-components` | `AppFlashList`, `OfflineBanner`, app-level empty states |
| `@porterchain/mobile-performance` | `EnterpriseFlashList`, lazy screens, optimized images, performance dashboard |
| `@porterchain/mobile-offline` | `OfflineSyncBar`, sync panel/screen support |

---

## Navigation UI

| App | Tabs | Pattern |
| --- | ---- | ------- |
| Driver | Home, Jobs, Navigation, Earnings, Shift, More | Native bottom tabs + nested stacks |
| Customer | Home, Bookings, Tracking, Notifications, Profile | Native bottom tabs + nested stacks |

Shared patterns:

- `headerShown: false`; screen headers are rendered in app screens.
- Heavy screens use `createLazyScreen`.
- `freezeOnBlur` is enabled on stack navigators.
- `SecurityShell` wraps signed-in content for PIN/biometric/integrity gates.

---

## Driver Screen Inventory

| Area | Screens | UI Quality |
| ---- | ------- | ---------- |
| Auth | SignIn with `ClerkSignInPanel` or local-only dev panel | ✅ production auth panel; dev fallback gated by local env |
| Home | Dashboard | ✅ cards, metrics, quick actions |
| Jobs | Jobs, JobDetail, AssignmentQueue, POD, Incident | ✅ timeline, status chips, lazy POD/incident screens |
| Navigation | Navigation | ✅ `EnterpriseMap`, server route data |
| Shift | Shift | ✅ online/offline and shift controls |
| Earnings | Earnings | ✅ summary cards |
| More | Profile, Notifications, OfflineSync, Support, SOS, Settings, Performance | ✅ broad coverage |

---

## Customer Screen Inventory

| Area | Screens | UI Quality |
| ---- | ------- | ---------- |
| Auth | SignIn with `ClerkSignInPanel` or local-only dev panel | ✅ production auth panel |
| Home | Dashboard | ✅ cards and recent activity |
| Bookings | Bookings, Quote, Booking, Draft, StripeCheckout, Confirmation | ✅ multi-step retail flow |
| Tracking | Tracking, LiveMap, History | ✅ map and history views |
| Notifications | NotificationCenter | ✅ inbox patterns |
| Profile | Profile, Invoices, Receipts, Support, Claims, OfflineSync, Settings, Performance | ✅ broad coverage |

---

## Component Adoption

| Component / Pattern | Adoption | Notes |
| ------------------- | -------- | ----- |
| `Screen` / app shell | High | Both apps use shared screen/layout patterns |
| `Button` variants | High | Primary/secondary/ghost/outline/danger available |
| `Card`, `CardHeader` | High | Dashboard/job/profile surfaces |
| `StatusChip`, `Badge` | High | Driver state and notification states |
| `Timeline` | Medium | Driver job/POD timeline patterns |
| `EnterpriseMap` / `MapFrame` | Medium | Driver navigation and customer tracking |
| `EnterpriseFlashList` | Medium/High | High-traffic lists |
| `Input` | Medium | Sign-in panels still use local form fields |
| `Dialog` / `SheetModal` | Low | Available for action confirmations |
| Charts | Low | Available for earnings/analytics polish |

---

## Forms And Validation

| Flow | Status | Gap |
| ---- | ------ | --- |
| Clerk sign-in | ✅ | Panel uses email/password and Google; can be visually aligned further with design tokens |
| Local dev sign-in | ✅ local-only | Hidden unless `EXPO_PUBLIC_APP_ENV=local` |
| Driver POD | ✅ | Add stricter client-side OTP/file validation |
| Customer quote/booking | ⚠ partial | Server errors shown; more Zod/react-hook-form coverage recommended |
| Support/claims | ⚠ basic | Improve required-field and attachment validation |
| Payment retry | ⚠ partial | Finish UX for failed/canceled checkout |

---

## Lists And Data Display

| Pattern | Status |
| ------- | ------ |
| High-volume lists | Use `EnterpriseFlashList` where traffic is expected |
| Short static menus | `ListSection` / `ScrollView` is acceptable |
| Notifications/history | Flattened list patterns supported |
| Offline sync state | `OfflineSyncBar`, `OfflineSyncPanel`, and app offline screens |

Recommendation: keep migrating any growing support/claims/history lists to `EnterpriseFlashList` with tuned `estimatedItemSize`.

---

## Accessibility, RTL, And Dark Mode

| Concern | Status | Next Step |
| ------- | ------ | --------- |
| Dark mode | ✅ | Continue token-only colors |
| RTL | ⚠ available | Audit screens for `start`/`end` assumptions |
| Touch targets | ✅ | Maintain 44pt minimum for primary actions |
| Screen-reader labels | ⚠ partial | VoiceOver/TalkBack pass before store release |
| Error messaging | ⚠ partial | Use consistent `ErrorState`/inline form errors |

---

## Branding And Store Assets

| Asset | Driver | Customer |
| ----- | ------ | -------- |
| App icon | ✅ configured | ⚠ missing explicit icon |
| Splash | ✅ configured | ⚠ background-only |
| Android adaptive icon | ✅ configured | ⚠ missing |
| Notification icon | ✅ configured | ⚠ default/minimal |

Customer store submission remains blocked until icon/splash/adaptive assets are added.

---

## UI Gap Priorities

| Priority | Item |
| -------- | ---- |
| P0 | Customer icon, splash, adaptive icon, notification icon |
| P0 | Hide/disable dev sign-in panel in production builds and EAS profiles |
| P1 | Payment retry screen for failed/canceled customer checkout |
| P1 | Wire stricter Zod/react-hook-form validation on quote, support, POD |
| P1 | Full VoiceOver/TalkBack accessibility audit |
| P2 | Bottom sheets for driver job actions |
| P2 | Earnings charts and richer analytics cards |
| P2 | Haptic feedback for POD complete / SOS confirmation |

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [MOBILE_DESIGN_SYSTEM.md](./MOBILE_DESIGN_SYSTEM.md) | Component inventory and principles |
| [MOBILE_PERFORMANCE_REPORT.md](./MOBILE_PERFORMANCE_REPORT.md) | List/lazy/performance package details |
| [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md) | Release blockers |
| [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md) | App architecture |
