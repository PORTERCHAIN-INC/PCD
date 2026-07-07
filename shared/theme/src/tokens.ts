/** 4pt base grid — Apple HIG + Material 3 spacing rhythm */
export const spacing = {
  "0": 0,
  px: 1,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  "2xl": 24,
  "3xl": 32,
  "4xl": 40,
  "5xl": 48,
  "6xl": 64,
} as const;

export const radii = {
  xs: 6,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  "2xl": 24,
  full: 9999,
} as const;

export const typography = {
  fontFamily: {
    regular: "System",
    medium: "System",
    semibold: "System",
    bold: "System",
  },
  weight: {
    regular: "400" as const,
    medium: "500" as const,
    semibold: "600" as const,
    bold: "700" as const,
  },
  size: {
    "2xs": 10,
    xs: 11,
    sm: 13,
    md: 15,
    lg: 17,
    xl: 20,
    "2xl": 24,
    "3xl": 30,
    "4xl": 36,
  },
  lineHeight: {
    tight: 1.15,
    snug: 1.3,
    normal: 1.45,
    relaxed: 1.6,
  },
  letterSpacing: {
    tight: -0.4,
    normal: 0,
    wide: 0.4,
    caps: 1.2,
  },
} as const;

export const layout = {
  minTouchTarget: 44,
  maxContentWidth: 680,
  headerHeight: 56,
  tabBarHeight: 64,
  bottomSheetHandleWidth: 36,
} as const;
