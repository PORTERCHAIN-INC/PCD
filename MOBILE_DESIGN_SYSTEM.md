# Porterchain Mobile Design System

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Packages:** `@porterchain/mobile-theme`, `@porterchain/mobile-ui`, `@porterchain/mobile-components`

Enterprise React Native UI shared by **Driver** and **Customer** mobile apps. The system uses Porterchain navy/blue tokens, dark-mode parity, logistics-oriented status components, and app-level providers wired through each Expo app.

---

## Package Map

| Package                          | Path                 | Role                                                           |
| -------------------------------- | -------------------- | -------------------------------------------------------------- |
| `@porterchain/mobile-theme`      | `shared/theme/`      | Colors, spacing, typography, motion, RTL-aware `ThemeProvider` |
| `@porterchain/mobile-ui`         | `shared/mobile-ui/`  | Core primitives and composed UI components                     |
| `@porterchain/mobile-components` | `shared/components/` | App-level list/offline/empty-state patterns                    |

---

## Provider Setup

Both mobile apps include the UI providers inside the full app provider stack:

```tsx
import { ThemeProvider } from "@porterchain/mobile-theme";
import { MobileUiProvider, ToastProvider } from "@porterchain/mobile-ui";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider initialScheme="system">
      <MobileUiProvider>
        <ToastProvider>{children}</ToastProvider>
      </MobileUiProvider>
    </ThemeProvider>
  );
}
```

In production apps this sits inside `SafeAreaProvider`, `QueryClientProvider`, `PerformanceLayer`, `MapsProvider`, `SecurityLayer`, API provider, offline sync, and notification layers.

---

## Tokens

| Token Group | Examples                                                                                         |
| ----------- | ------------------------------------------------------------------------------------------------ |
| Brand       | Navy `#0a1628`, blue `#2563eb`; driver splash green `#124835`                                    |
| Typography  | `Display`, `Headline`, `Title`, `Body`, `Label`, `Caption`, `Text`                               |
| Spacing     | 4pt grid: `xs`, `sm`, `md`, `lg`, `xl`, `2xl`, `3xl`, `4xl`                                      |
| Status      | `neutral`, `info`, `success`, `warning`, `danger`, `active`, `pending`, `completed`, `cancelled` |
| Motion      | `FadeIn`, `FadeInDown`, `FadeInUp`, `FadeOut`, `AnimatedView`, `PressableScale`                  |

---

## Component Inventory

| Category     | Exports                                                                                   |
| ------------ | ----------------------------------------------------------------------------------------- |
| Layout       | `Screen`, `Divider`, `Spacer`                                                             |
| Typography   | `Text`, `Display`, `Headline`, `Title`, `Body`, `Label`, `Caption`                        |
| Actions      | `Button` (`primary`, `secondary`, `ghost`, `outline`, `danger`)                           |
| Surfaces     | `Card`, `CardHeader`                                                                      |
| Forms        | `Input`, `SearchInput`                                                                    |
| Data display | `ListItem`, `ListSection`, `DataTable`, `Badge`, `StatusChip`                             |
| Feedback     | `ToastProvider`, `useToast`, `Dialog`, `MobileUiProvider`, `AppBottomSheet`, `SheetModal` |
| Loading      | `Skeleton`, `SkeletonCard`, `SkeletonList`                                                |
| Charts       | `BarChart`, `Sparkline`, `MetricCard`                                                     |
| Logistics    | `Timeline`, `MapFrame`                                                                    |
| States       | `LoadingState`, `EmptyState`, `ErrorState`, `SuccessState`                                |
| Motion       | `AnimatedView`, `PressableScale`, `FadeIn*`, `FadeOut`                                    |

---

## Usage Examples

```tsx
import { Body, Button, Card, CardHeader, StatusChip } from "@porterchain/mobile-ui";

<Card elevated onPress={openJob}>
  <CardHeader
    title="Stop 3"
    subtitle="123 Main St"
    action={<StatusChip label="In transit" tone="active" />}
  />
  <Body muted>ETA 4 min</Body>
  <Button label="Capture POD" variant="primary" fullWidth />
</Card>;
```

```tsx
import { EmptyState, SkeletonList, Timeline } from "@porterchain/mobile-ui";

<SkeletonList count={5} />
<EmptyState title="No jobs" action={{ label: "Go online", onPress }} />
<Timeline items={[{ id: "1", title: "Picked up", timestamp: "9:02 AM", tone: "completed" }]} />
```

---

## App Usage

| App                    | Design System Usage                                                                                |
| ---------------------- | -------------------------------------------------------------------------------------------------- |
| `apps/mobile-driver`   | Dashboard cards, jobs lists, POD states, navigation map frame, shift controls, SOS/support screens |
| `apps/mobile-customer` | Quote/booking flows, tracking map, notification inbox, invoices/receipts, support/claims screens   |

The apps also use `@porterchain/mobile-performance` (`EnterpriseFlashList`, lazy screens, optimized image) and `@porterchain/mobile-offline` (`OfflineSyncBar`, `OfflineSyncPanel`) alongside the core UI package.

---

## Principles

1. **Operational clarity** — status chips, timelines, maps, and action buttons make logistics state obvious.
2. **Server truth** — UI validates inputs, but Porterchain API owns business decisions.
3. **Mobile accessibility** — 44pt touch targets, screen-reader roles, and dark-mode token parity are required.
4. **Shared by default** — new primitives belong in shared packages unless they are app-specific.
5. **No direct Fleetbase** — mobile UI calls Porterchain API only.

---

## Related Documents

| Document                                                           | Purpose                         |
| ------------------------------------------------------------------ | ------------------------------- |
| [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md)   | Mobile architecture and UI map  |
| [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md) | Readiness and performance notes |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
