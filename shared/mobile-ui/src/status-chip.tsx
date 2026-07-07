"use client";

import { View } from "react-native";
import { statusTone, type StatusTone, useTheme } from "@porterchain/mobile-theme";
import { Text } from "./typography";

export function StatusChip({ label, tone = "neutral" }: { label: string; tone?: StatusTone }) {
  const { theme } = useTheme();
  const colors = statusTone(theme.colors, tone);

  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        alignSelf: "flex-start",
        paddingHorizontal: theme.spacing.md,
        paddingVertical: theme.spacing.xs,
        borderRadius: theme.radii.full,
        backgroundColor: colors.bg,
        borderWidth: colors.border === "transparent" ? 0 : 1,
        borderColor: colors.border,
      }}
    >
      <View
        style={{
          width: 6,
          height: 6,
          borderRadius: 3,
          backgroundColor: colors.text,
          marginRight: theme.spacing.xs,
        }}
      />
      <Text variant="caption" style={{ color: colors.text, fontWeight: "600" }}>
        {label}
      </Text>
    </View>
  );
}
