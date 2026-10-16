/**
 * Customer app colour system. Built on the shared PorterChain brand tokens
 * (`@porterchain/mobile-theme`: navy #0a1628, blue #2563eb, mist #f0f4f8) and
 * extended with a dark palette. Every text/background pair used by the app is
 * checked for WCAG AA in `palette.test.ts`.
 *
 * Pure TS (no react-native import) so it can be unit tested.
 */
import { colors as brand } from "@porterchain/mobile-theme";

export type Palette = {
  /** Strong text / brand navy in light mode. */
  primary: string;
  /** Brand blue, used as a fill (buttons, selected chips). */
  secondary: string;
  /** Text and icons drawn on `secondary`. */
  onAccent: string;
  /** Brand blue as text or link on the page or a surface. */
  accentText: string;
  /** Page background. */
  grayBg: string;
  /** Card / input / sheet surface. */
  white: string;
  /** Raised surface inside a card (skeletons, segmented control track). */
  sunken: string;
  /** Secondary text. AA (>= 4.5:1) on both `grayBg` and `white`. */
  muted: string;
  border: string;
  danger: string;
  dangerBg: string;
  success: string;
  successBg: string;
  warning: string;
  warningBg: string;
  infoBg: string;
  /** Hero card (active shipment). */
  hero: string;
  onHero: string;
  onHeroMuted: string;
  scheme: "light" | "dark";
};

export const light: Palette = {
  primary: brand.primary,
  secondary: brand.secondary,
  onAccent: "#ffffff",
  accentText: "#1d4ed8",
  grayBg: brand.grayBg,
  white: brand.white,
  sunken: "#e2e8f0",
  muted: "#475569",
  border: "#cbd5e1",
  danger: "#b91c1c",
  dangerBg: "#fef2f2",
  success: "#15803d",
  successBg: "#f0fdf4",
  warning: "#a16207",
  warningBg: "#fefce8",
  infoBg: "#eff6ff",
  hero: brand.primary,
  onHero: "#ffffff",
  onHeroMuted: "#cbd5e1",
  scheme: "light",
};

export const dark: Palette = {
  primary: "#e2e8f0",
  secondary: brand.secondary,
  onAccent: "#ffffff",
  accentText: "#93c5fd",
  grayBg: "#070d18",
  white: "#111a2b",
  sunken: "#1e293b",
  muted: "#a3b1c6",
  border: "#2b3a52",
  danger: "#fca5a5",
  dangerBg: "#3b1114",
  success: "#86efac",
  successBg: "#0c2a18",
  warning: "#fcd34d",
  warningBg: "#2e2306",
  infoBg: "#0f1f3d",
  hero: "#1e3a8a",
  onHero: "#ffffff",
  onHeroMuted: "#dbeafe",
  scheme: "dark",
};

export function paletteFor(scheme: string | null | undefined): Palette {
  return scheme === "dark" ? dark : light;
}

/** WCAG 2.x relative luminance contrast ratio between two #rrggbb colours. */
export function contrastRatio(a: string, b: string): number {
  const lum = (hex: string) => {
    const n = hex.replace("#", "");
    const [r, g, bl] = [0, 2, 4].map((i) => {
      const c = parseInt(n.slice(i, i + 2), 16) / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r! + 0.7152 * g! + 0.0722 * bl!;
  };
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi! + 0.05) / (lo! + 0.05);
}
