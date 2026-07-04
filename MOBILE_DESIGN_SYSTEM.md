# Porterchain Mobile Design System

Enterprise-grade React Native UI for **Driver** and **Customer** apps. Porterchain Blue theme — navy `#0a1628` + electric blue `#2563eb` — with patterns inspired by Uber Driver, Stripe, Linear, Apple HIG, and Material Design 3.

## Packages

| Package | Role |
|---------|------|
| `@porterchain/mobile-theme` | Colors, spacing, typography, shadows, motion, status tones |
| `@porterchain/mobile-ui` | Components (this design system) |

## Setup

```tsx
import { ThemeProvider } from "@porterchain/mobile-theme";
import { MobileUiProvider, ToastProvider } from "@porterchain/mobile-ui";

export function AppProviders({ children }) {
  return (
    <ThemeProvider initialScheme="system">
      <MobileUiProvider>
        <ToastProvider>{children}</ToastProvider>
      </MobileUiProvider>
    </ThemeProvider>
  );
}
```

## Typography

| Token | Size | Use |
|-------|------|-----|
| `display` | 36 | Hero numbers, splash |
| `headline` | 24 | Screen titles |
| `title` | 17 | Card headers |
| `body` | 15 | Default copy |
| `label` | 13 | Form labels, table headers |
| `caption` | 11 | Meta, timestamps |
| `overline` | 10 | Section labels (uppercase) |

```tsx
import { Headline, Body, Caption } from "@porterchain/mobile-ui";

<Headline>Today's route</Headline>
<Body muted>12 stops remaining</Body>
```

## Spacing

4pt grid via `theme.spacing`: `xs` 4 · `sm` 8 · `md` 12 · `lg` 16 · `xl` 20 · `2xl` 24 · `3xl` 32 · `4xl` 40

```tsx
import { Spacer } from "@porterchain/mobile-ui";
<Spacer size="2xl" />
```

## Components

### Buttons
Variants: `primary` · `secondary` · `ghost` · `outline` · `danger`  
Sizes: `sm` · `md` · `lg` (44pt min touch on `md`)

```tsx
<Button label="Accept job" variant="primary" loading={pending} fullWidth />
```

### Cards
```tsx
<Card elevated onPress={open}>
  <CardHeader title="Stop 3" subtitle="123 Main St" action={<Badge label="ETA 4m" />} />
</Card>
```

### Inputs & Search
```tsx
<Input label="Phone" hint="Include country code" error={errors.phone} />
<SearchInput placeholder="Search orders…" />
```

### Lists & Tables
```tsx
<ListSection title="Active jobs">
  <ListItem title="PC-1042" subtitle="Downtown" meta="2.1 km" onPress={open} />
</ListSection>

<DataTable columns={cols} data={rows} keyExtractor={(r) => r.id} />
```

### Badges & Status Chips
```tsx
<Badge label="Live" variant="success" dot />
<StatusChip label="In transit" tone="active" />
```

Tones: `neutral` · `info` · `success` · `warning` · `danger` · `active` · `pending` · `completed` · `cancelled`

### Toast
```tsx
const { show } = useToast();
show("Route updated", "success");
```

### Dialogs & Bottom Sheets
```tsx
<Dialog visible={open} title="Cancel stop?" destructive onConfirm={cancel} onCancel={close} />

const sheetRef = useRef<BottomSheetModal>(null);
<SheetModal ref={sheetRef} title="Proof of delivery" snapPoints={["50%", "90%"]}>
  ...
</SheetModal>
```

### Skeletons
```tsx
<SkeletonList count={5} />
<SkeletonCard />
```

### Charts
```tsx
<BarChart data={[{ label: "Mon", value: 12 }, ...]} />
<MetricCard label="Earnings" value="$284" delta="+12%" trend={[4,6,5,8,12]} />
```

### Timeline & Maps
```tsx
<Timeline items={[{ id: "1", title: "Picked up", timestamp: "9:02 AM", tone: "completed" }]} />

<MapFrame loading={!ready} overlay={<SearchInput />}>
  <MapView ... />
</MapFrame>
```

### State Views
```tsx
<LoadingState message="Syncing route…" />
<EmptyState title="No jobs" action={{ label: "Go online", onPress }} />
<ErrorState action={{ label: "Retry", onPress: refetch }} />
<SuccessState title="Delivered" message="POD captured" />
```

### Motion
```tsx
import { FadeInDown, PressableScale } from "@porterchain/mobile-ui";

<Animated.View entering={FadeInDown.duration(280)}>
  <PressableScale onPress={tap}><Card>...</Card></PressableScale>
</Animated.View>
```

## Theming

```tsx
const { theme, toggleScheme } = useTheme();
// theme.colors.secondary — Porterchain Blue
// theme.shadows.md — elevation
// theme.motion.duration.normal — 280ms
```

## Principles

1. **Premium density** — generous whitespace, crisp borders, subtle shadows
2. **Operational clarity** — status chips, timeline, and map chrome for logistics
3. **Accessibility** — 44pt touch targets, `a11yProps` on primary actions
4. **Dark mode** — full token parity via `ThemeProvider`
5. **No direct Fleetbase** — UI calls Porterchain API only (`masterrule.md`)
