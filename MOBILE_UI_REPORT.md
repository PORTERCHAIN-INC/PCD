# Mobile UI Report

**Audit date:** June 30, 2026  
**Design system:** [MOBILE_DESIGN_SYSTEM.md](./MOBILE_DESIGN_SYSTEM.md)  
**Packages:** `@porterchain/mobile-ui`, `@porterchain/mobile-theme`, `@porterchain/mobile-components`

---

## Executive summary

Both mobile apps use a **unified enterprise design system** with Porterchain Blue theming, shared primitives, and consistent screen patterns (`Screen` + `ScreenHeader`). Feature screens are built and wired — the scaffold-era "no screens" documentation is outdated.

**UI posture:** **Consistent and production-styled** — polish gaps in forms validation, accessibility audit, and customer store branding assets.

---

## 1. Design system stack

| Package | Role |
|---------|------|
| `@porterchain/mobile-theme` | Light/dark tokens, spacing, typography, RTL |
| `@porterchain/mobile-ui` | 40+ components — Button, Card, ListItem, Timeline, maps frame, states |
| `@porterchain/mobile-components` | `AppFlashList`, `OfflineBanner`, `EmptyState` |

### Theme

- **Primary:** Navy `#0a1628` + electric blue `#2563eb`
- **Modes:** System / light / dark via `ThemeProvider`
- **Driver splash:** Green `#124835`
- **Customer splash:** Navy `#0a1628`

---

## 2. Layout patterns

### Standard screen

```tsx
<Screen>
  <ScreenHeader title="..." subtitle="..." right={...} />
  {/* content */}
</Screen>
```

**Consistent across:** All feature screens in both apps via local `ScreenHeader` wrapper.

### Loading / empty / error states

| State | Component | Usage |
|-------|-----------|-------|
| Loading | `SkeletonList`, `SkeletonCard`, `LoadingState` | Lists, maps, checkout |
| Empty | `EmptyState` | Notifications, queues |
| Error | `Body` + danger color | Forms, checkout |
| Success | `SuccessState` | POD complete |

---

## 3. Navigation UI

### Tab bars

| App | Tabs | Icons |
|-----|------|-------|
| Driver | 6 — Home, Jobs, Navigation, Earnings, Shift, More | Bottom tabs |
| Customer | 5 — Home, Bookings, Tracking, Notifications, Profile | Bottom tabs |

### Stacks

- Native stack, `headerShown: false` (custom headers)
- `freezeOnBlur: true` on lazy-loaded stacks (performance)

### Security gates (overlay)

`SecurityShell` wraps main content — biometric/PIN prompts without replacing navigation chrome.

---

## 4. Feature screen inventory

### Driver app

| Area | Screens | UI quality |
|------|---------|------------|
| Auth | SignIn | Basic — needs Clerk UI |
| Home | Dashboard | ✅ Cards, metrics |
| Jobs | Jobs, JobDetail, Queue, POD, Incident | ✅ Timeline, status chips |
| Navigation | Navigation, LiveMap | ✅ EnterpriseMap |
| Shift | Shift | ✅ Online/offline toggle |
| Earnings | Earnings | ✅ Snapshot cards |
| More | Profile, Notifications, Offline, Support, SOS, Settings, Performance | ✅ Full |

### Customer app

| Area | Screens | UI quality |
|------|---------|------------|
| Auth | SignIn | Basic — needs Clerk UI |
| Home | Dashboard | ✅ |
| Bookings | Quote, Booking, Draft, Checkout, Confirmation | ✅ Multi-step flow |
| Tracking | Tracking, LiveMap, History | ✅ Map + FlashList history |
| Notifications | NotificationCenter | ✅ Grouped inbox |
| Profile | Invoices, Receipts, Support, Claims, Settings, Performance | ✅ |

---

## 5. Component usage audit

| Component | Adoption | Gap |
|-----------|----------|-----|
| `ListItem` / `ListSection` | High | Some screens migrated to FlashList rows |
| `StatusChip` | High | Consistent job/order states |
| `Timeline` | Driver JobDetail | — |
| `EnterpriseMap` | Both | Requires Maps API key |
| `Button` variants | High | primary/secondary/ghost/outline/danger |
| `Input` | Medium | Sign-in uses raw state vs react-hook-form |
| `AppBottomSheet` | Low | Available but rarely used |
| `Dialog` / `SheetModal` | Low | Could replace inline error text |
| `BarChart` / `Sparkline` | Low | Earnings could use charts |

---

## 6. Lists & data display

**Before audit:** ScrollView + `.map()` on all lists.  
**After performance work:** FlashList on 7+ high-traffic screens.

| Pattern | Recommendation |
|---------|----------------|
| Long lists | `EnterpriseFlashList` + `estimatedItemSize` |
| Short static menus | `ListSection` in ScrollView OK (Profile links) |
| Grouped notifications | Flattened rows with section headers in FlashList |

---

## 7. Forms & validation

| Screen | Validation | Gap |
|--------|------------|-----|
| SignIn | None | Zod schemas exist in `forms/schemas.ts` — unused |
| Quote/Booking | Partial | Server errors shown; client Zod not wired |
| POD | Manual | OTP length not validated client-side |
| Support | Basic | Subject required implicitly |

**Recommendation:** Wire `react-hook-form` + Zod on sign-in and booking forms without changing API contracts.

---

## 8. Accessibility & RTL

| Concern | Status |
|---------|--------|
| Dark mode | ✅ System automatic |
| RTL | ⚠️ `theme.isRTL` available; screens mostly LTR |
| Touch targets | ✅ Button min heights in design system |
| `accessibilityRole` | ⚠️ Partial — OfflineBanner has it |
| Screen reader labels | ⚠️ Not audited per-screen |

---

## 9. Branding & assets

| Asset | Driver | Customer |
|-------|--------|----------|
| App icon | ✅ `assets/icon.png` | ❌ Missing |
| Splash | ✅ | ❌ Background color only |
| Adaptive icon (Android) | ✅ | ❌ |
| Notification icon | ✅ | Default |

**Customer store submission blocked** until assets added.

---

## 10. Offline & sync UI

| Component | App | Location |
|-----------|-----|----------|
| `OfflineSyncBar` | Both | `AppShell` top bar |
| `OfflineSyncPanel` | Both | Offline sync screen |
| `OfflineSyncScreen` | Both | More / Profile |

Sync status: pending count, last sync, manual sync button.

---

## 11. UI gaps & recommendations

### P0 (store / trust)

1. Customer app icons and splash images
2. Clerk-branded sign-in screens
3. Remove dev mode copy from SignIn in production builds

### P1 (UX polish)

4. Wire Zod + react-hook-form on auth and quote flows
5. Payment retry screen for failed checkouts
6. Rebook action on order history → Quote with `rebookOrderId`
7. Support ticket list FlashList migration

### P2 (enhancement)

8. Bottom sheets for job actions (accept/reject)
9. Earnings charts (`BarChart` / `Sparkline`)
10. Haptic feedback on POD complete
11. Full accessibility audit (VoiceOver / TalkBack)

---

## 12. Related documents

- [MOBILE_DESIGN_SYSTEM.md](./MOBILE_DESIGN_SYSTEM.md)
- [MOBILE_PERFORMANCE_REPORT.md](./MOBILE_PERFORMANCE_REPORT.md)
- [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md)
