import type { TextStyle } from "react-native";
import type { Theme } from "./ThemeProvider";

export function createTextStyles(theme: Theme): Record<string, TextStyle> {
  const { typography: t, colors } = theme;
  const base = { color: colors.text, fontFamily: t.fontFamily.regular };

  return {
    display: {
      ...base,
      fontSize: t.size["4xl"],
      lineHeight: t.size["4xl"] * t.lineHeight.tight,
      fontWeight: t.weight.bold,
      letterSpacing: t.letterSpacing.tight,
    },
    headline: {
      ...base,
      fontSize: t.size["2xl"],
      lineHeight: t.size["2xl"] * t.lineHeight.snug,
      fontWeight: t.weight.bold,
      letterSpacing: t.letterSpacing.tight,
    },
    title: {
      ...base,
      fontSize: t.size.lg,
      lineHeight: t.size.lg * t.lineHeight.snug,
      fontWeight: t.weight.semibold,
    },
    body: {
      ...base,
      fontSize: t.size.md,
      lineHeight: t.size.md * t.lineHeight.normal,
      fontWeight: t.weight.regular,
    },
    bodyMedium: {
      ...base,
      fontSize: t.size.md,
      lineHeight: t.size.md * t.lineHeight.normal,
      fontWeight: t.weight.medium,
    },
    label: {
      ...base,
      fontSize: t.size.sm,
      lineHeight: t.size.sm * t.lineHeight.normal,
      fontWeight: t.weight.medium,
      color: colors.textSecondary,
    },
    caption: {
      ...base,
      fontSize: t.size.xs,
      lineHeight: t.size.xs * t.lineHeight.normal,
      fontWeight: t.weight.regular,
      color: colors.textMuted,
    },
    overline: {
      ...base,
      fontSize: t.size["2xs"],
      lineHeight: t.size["2xs"] * t.lineHeight.normal,
      fontWeight: t.weight.semibold,
      letterSpacing: t.letterSpacing.caps,
      textTransform: "uppercase",
      color: colors.textMuted,
    },
    mono: {
      ...base,
      fontSize: t.size.sm,
      fontVariant: ["tabular-nums"],
      fontWeight: t.weight.medium,
    },
  };
}
