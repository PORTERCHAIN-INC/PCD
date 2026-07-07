"use client";

import { View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Text } from "./typography";

export type BadgeVariant = "neutral" | "primary" | "success" | "warning" | "danger";

export function Badge({
  label,
  variant = "neutral",
  dot,
}: {
  label: string;
  variant?: BadgeVariant;
  dot?: boolean;
}) {
  const { theme } = useTheme();

  const palette: Record<BadgeVariant, { bg: string; text: string }> = {
    neutral: { bg: theme.colors.surfaceMuted, text: theme.colors.textSecondary },
    primary: { bg: theme.colors.secondaryMuted, text: theme.colors.secondary },
    success: { bg: theme.colors.successSoft, text: theme.colors.success },
    warning: { bg: theme.colors.warningSoft, text: theme.colors.warning },
    danger: { bg: theme.colors.dangerSoft, text: theme.colors.danger },
  };

  const colors = palette[variant];

  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.xs,
        alignSelf: "flex-start",
        paddingHorizontal: theme.spacing.sm,
        paddingVertical: theme.spacing.xs,
        borderRadius: theme.radii.full,
        backgroundColor: colors.bg,
      }}
    >
      {dot ? (
        <View
          style={{
            width: 6,
            height: 6,
            borderRadius: 3,
            backgroundColor: colors.text,
          }}
        />
      ) : null}
      <Text
        variant="caption"
        style={{ color: colors.text, fontWeight: "600", fontSize: theme.typography.size["2xs"] }}
      >
        {label}
      </Text>
    </View>
  );
}
