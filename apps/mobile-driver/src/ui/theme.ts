/**
 * The one design-token file for the driver app. Built for use in a van: high contrast
 * (all text pairs meet WCAG AA; body text is AAA on surface), large type, big targets.
 * Nothing else in the app hard-codes a colour, size or spacing. Brand base (ink, background,
 * 44pt minimum) comes from @porterchain/mobile-theme so web and mobile stay in parity.
 */
import { colors as brand, touchTargetMin } from "@porterchain/mobile-theme";

export const color = {
  bg: brand.grayBg,
  surface: brand.white,
  ink: brand.primary, // #0a1628, 18:1 on surface
  inkMuted: "#3D4A5C", // 9.1:1 on surface
  border: "#AEB8C5",
  primary: "#0B6B3A", // white on primary 6.9:1
  primaryPressed: "#08532D",
  onPrimary: "#FFFFFF",
  danger: "#B42318", // white on danger 6.1:1
  dangerSoft: "#FDE8E7",
  warnSoft: "#FFF4CC",
  warnInk: "#5C3B00", // 9.6:1 on warnSoft
  infoSoft: "#E3ECFF",
  infoInk: "#0F2E7A",
  successSoft: "#DDF4E6",
  successInk: "#0B4A28",
  disabled: "#C9D1DB",
  onDisabled: "#3D4A5C",
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radius = { md: 10, lg: 14, pill: 999 } as const;

/** Minimum tap targets (pt). Primary actions are bigger than the 48pt platform minimum. */
export const target = { min: Math.max(56, touchTargetMin), primary: 68 } as const;

export const type = {
  display: { fontSize: 30, lineHeight: 36, fontWeight: "800" as const },
  title: { fontSize: 24, lineHeight: 30, fontWeight: "800" as const },
  heading: { fontSize: 20, lineHeight: 26, fontWeight: "700" as const },
  body: { fontSize: 18, lineHeight: 26, fontWeight: "400" as const },
  bodyStrong: { fontSize: 18, lineHeight: 26, fontWeight: "700" as const },
  label: { fontSize: 15, lineHeight: 20, fontWeight: "700" as const, letterSpacing: 0.6 },
  small: { fontSize: 15, lineHeight: 21, fontWeight: "400" as const },
  button: { fontSize: 20, lineHeight: 24, fontWeight: "800" as const },
} as const;
