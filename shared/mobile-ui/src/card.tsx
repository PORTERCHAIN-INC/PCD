"use client";

import type { ReactNode } from "react";
import { Pressable, View, type PressableProps, type ViewProps } from "react-native";
import { shadowForScheme, useTheme } from "@porterchain/mobile-theme";
import { Title, Caption } from "./typography";

export type CardProps = ViewProps & {
  onPress?: PressableProps["onPress"];
  elevated?: boolean;
  padded?: boolean;
};

export function Card({
  children,
  style,
  onPress,
  elevated = true,
  padded = true,
  ...props
}: CardProps) {
  const { theme } = useTheme();
  const shell = {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: padded ? theme.spacing.lg : 0,
    overflow: "hidden" as const,
    ...(elevated ? shadowForScheme("md", theme.scheme) : {}),
  };

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [shell, { opacity: pressed ? 0.96 : 1 }, style]}
        {...props}
      >
        {children}
      </Pressable>
    );
  }

  return (
    <View style={[shell, style]} {...props}>
      {children}
    </View>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: theme.spacing.md,
        marginBottom: subtitle ? theme.spacing.sm : 0,
      }}
    >
      <View style={{ flex: 1 }}>
        <Title>{title}</Title>
        {subtitle ? <Caption style={{ marginTop: 2 }}>{subtitle}</Caption> : null}
      </View>
      {action}
    </View>
  );
}
