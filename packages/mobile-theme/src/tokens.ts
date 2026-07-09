/** Porterchain brand tokens — parity with web portals (`globals.css`, `@porterchain/ui`). */

export const colors = {
  primary: "#0a1628",
  secondary: "#2563eb",
  grayBg: "#f0f4f8",
  muted: "#64748b",
  white: "#ffffff",
  danger: "#dc2626",
  success: "#16a34a",
  /** Driver splash / field accent */
  driverGreen: "#124835",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  "2xl": 32,
} as const;

export const radius = {
  md: 8,
  lg: 12,
  xl: 16,
} as const;

/** WCAG touch target minimum (pt) */
export const touchTargetMin = 44;

export const typography = {
  title: { fontSize: 22, fontWeight: "600" as const },
  body: { fontSize: 16, fontWeight: "400" as const },
  caption: { fontSize: 14, fontWeight: "400" as const },
  button: { fontSize: 16, fontWeight: "600" as const },
};
