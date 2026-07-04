"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { I18nManager, useColorScheme as useSystemColorScheme } from "react-native";
import { darkColors, lightColors, type ColorScheme, type ThemeColors } from "./colors";
import { motion } from "./motion";
import { shadowForScheme, shadows } from "./shadows";
import { layout, radii, spacing, typography } from "./tokens";
import { createTextStyles } from "./typography-styles";

export type Theme = {
  scheme: ColorScheme;
  colors: ThemeColors;
  spacing: typeof spacing;
  radii: typeof radii;
  typography: typeof typography;
  layout: typeof layout;
  shadows: typeof shadows;
  motion: typeof motion;
  textStyles: ReturnType<typeof createTextStyles>;
  isRTL: boolean;
};

type ThemeContextValue = {
  theme: Theme;
  setScheme: (scheme: ColorScheme | "system") => void;
  toggleScheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({
  children,
  initialScheme = "system",
}: {
  children: ReactNode;
  initialScheme?: ColorScheme | "system";
}) {
  const system = useSystemColorScheme();
  const [preference, setPreference] = useState<ColorScheme | "system">(initialScheme);

  const scheme: ColorScheme =
    preference === "system" ? (system === "dark" ? "dark" : "light") : preference;

  const theme = useMemo<Theme>(() => {
    const colors = scheme === "dark" ? darkColors : lightColors;
    const base = {
      scheme,
      colors,
      spacing,
      radii,
      typography,
      layout,
      shadows,
      motion,
      isRTL: I18nManager.isRTL,
    };
    return { ...base, textStyles: createTextStyles({ ...base, textStyles: {} as Theme["textStyles"] }) };
  }, [scheme]);

  const toggleScheme = useCallback(() => {
    setPreference((prev) => {
      const resolved = prev === "system" ? scheme : prev;
      return resolved === "dark" ? "light" : "dark";
    });
  }, [scheme]);

  const value = useMemo(
    () => ({ theme, setScheme: setPreference, toggleScheme }),
    [theme, toggleScheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}

export { shadowForScheme };
