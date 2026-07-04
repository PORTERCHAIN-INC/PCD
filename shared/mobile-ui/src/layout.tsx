"use client";

import { View, type ViewProps } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";

export function Screen({ style, ...props }: ViewProps) {
  const { theme } = useTheme();
  return <View style={[{ flex: 1, backgroundColor: theme.colors.background }, style]} {...props} />;
}

export function Divider({ inset = 0 }: { inset?: number }) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        height: 1,
        backgroundColor: theme.colors.border,
        marginStart: inset,
        marginEnd: inset,
      }}
    />
  );
}

export function Spacer({
  size = "lg",
}: {
  size?: keyof typeof import("@porterchain/mobile-theme").spacing;
}) {
  const { theme } = useTheme();
  return <View style={{ height: theme.spacing[size] }} />;
}
