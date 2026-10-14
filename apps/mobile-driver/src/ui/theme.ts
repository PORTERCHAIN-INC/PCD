/**
 * Driver app design tokens — "Night Ops": deep navy surfaces, one bright accent, nothing else.
 * Built for a van cab at night: no white glare, high contrast (body text ≥ 12:1 on surface,
 * accent ≥ 9:1 against its ink), big type, big targets. Nothing else in the app hard-codes a
 * colour, size, spacing or duration.
 */
import { touchTargetMin } from "@porterchain/mobile-theme";

/** Single accent: signal green. Used only for the one primary action and "live" state. */
const ACCENT = "#2DE3A0";

export const color = {
  bg: "#060B16",
  surface: "#0E1729",
  surface2: "#15213A",
  ink: "#F3F6FB", // 16.8:1 on surface
  inkMuted: "#A7B2C6", // 8.1:1 on surface
  inkFaint: "#6B7891",
  border: "#22304B",
  primary: ACCENT,
  primaryPressed: "#1FC488",
  onPrimary: "#04121C", // 11.6:1 on accent
  accentSoft: "#0D3A2D",
  danger: "#FF5C61",
  onDanger: "#1A0405",
  dangerSoft: "#3A1216",
  warnSoft: "#33280C",
  warnInk: "#FFD36E",
  infoSoft: "#102542",
  infoInk: "#9CC4FF",
  successSoft: "#0D3328",
  successInk: "#7CF2C6",
  disabled: "#1C2840",
  onDisabled: "#7D8AA3",
  skeleton: "#1A2640",
} as const;

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radius = { sm: 8, md: 12, lg: 18, xl: 26, pill: 999 } as const;

/** Minimum tap targets (pt). Primary actions are bigger than the 48pt platform minimum. */
export const target = { min: Math.max(56, touchTargetMin), primary: 72 } as const;

/** Large text: system font scaling is honoured up to this multiplier so layouts never break. */
export const maxFontScale = 1.6;

/** Type scale (1.25 ratio from 16). Heavy weights, tight leading for glanceability. */
export const type = {
  hero: { fontSize: 44, lineHeight: 48, fontWeight: "900" as const, letterSpacing: -1 },
  display: { fontSize: 32, lineHeight: 38, fontWeight: "900" as const, letterSpacing: -0.5 },
  title: { fontSize: 26, lineHeight: 32, fontWeight: "800" as const, letterSpacing: -0.3 },
  heading: { fontSize: 20, lineHeight: 26, fontWeight: "800" as const },
  body: { fontSize: 18, lineHeight: 26, fontWeight: "500" as const },
  bodyStrong: { fontSize: 18, lineHeight: 26, fontWeight: "800" as const },
  label: { fontSize: 13, lineHeight: 18, fontWeight: "800" as const, letterSpacing: 1.4 },
  small: { fontSize: 15, lineHeight: 21, fontWeight: "500" as const },
  button: { fontSize: 20, lineHeight: 24, fontWeight: "900" as const, letterSpacing: 0.2 },
  mono: {
    fontSize: 18,
    lineHeight: 22,
    fontWeight: "800" as const,
    fontVariant: ["tabular-nums"] as ["tabular-nums"],
  },
} as const;

/** Motion (ms). Short and physical; everything respects the OS "reduce motion" setting. */
export const motion = { fast: 120, base: 220, slow: 420, pressScale: 0.97 } as const;
