import { useMemo } from "react";
import { useColorScheme } from "react-native";
import { paletteFor, type Palette } from "./palette";

export { light, dark, contrastRatio, type Palette } from "./palette";
export { spacing, radius, touchTargetMin } from "@porterchain/mobile-theme";

/**
 * Type scale. System font (SF Pro / Roboto) so Dynamic Type and Android font
 * scaling apply; sizes follow the iOS HIG text styles.
 */
export const type = {
  largeTitle: { fontSize: 32, lineHeight: 38, fontWeight: "700" as const, letterSpacing: -0.4 },
  title: { fontSize: 22, lineHeight: 28, fontWeight: "700" as const },
  headline: { fontSize: 17, lineHeight: 22, fontWeight: "600" as const },
  body: { fontSize: 16, lineHeight: 22, fontWeight: "400" as const },
  callout: { fontSize: 15, lineHeight: 20, fontWeight: "500" as const },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: "500" as const },
  overline: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "700" as const,
    letterSpacing: 0.8,
    textTransform: "uppercase" as const,
  },
};

/** Caps Dynamic Type so the largest accessibility sizes don't break layouts. */
export const maxFontScale = 1.6;

export function usePalette(): Palette {
  return paletteFor(useColorScheme());
}

/** `const { colors, styles } = useThemed(makeStyles)` — styles rebuilt only when the scheme flips. */
export function useThemed<T>(make: (colors: Palette) => T): { colors: Palette; styles: T } {
  const colors = usePalette();
  const styles = useMemo(() => make(colors), [colors, make]);
  return { colors, styles };
}
