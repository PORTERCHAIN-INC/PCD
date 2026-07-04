"use client";

import type { ReactNode } from "react";
import { Pressable, View, type ViewStyle } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Caption, Label } from "./typography";
import { Divider } from "./layout";

export type ListItemProps = {
  title: string;
  subtitle?: string;
  meta?: string;
  leading?: ReactNode;
  trailing?: ReactNode;
  onPress?: () => void;
  showDivider?: boolean;
  inset?: boolean;
};

export function ListItem({
  title,
  subtitle,
  meta,
  leading,
  trailing,
  onPress,
  showDivider = true,
  inset = true,
}: ListItemProps) {
  const { theme } = useTheme();
  const content = (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: theme.spacing.md,
        paddingVertical: theme.spacing.md,
        paddingHorizontal: inset ? theme.spacing.lg : 0,
        minHeight: theme.layout.minTouchTarget,
      }}
    >
      {leading}
      <View style={{ flex: 1, gap: 2 }}>
        <Body style={{ fontWeight: "500" }}>{title}</Body>
        {subtitle ? <Caption>{subtitle}</Caption> : null}
      </View>
      {meta ? <Caption>{meta}</Caption> : null}
      {trailing}
    </View>
  );

  return (
    <View>
      {onPress ? (
        <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
          {content}
        </Pressable>
      ) : (
        content
      )}
      {showDivider ? <Divider inset={inset ? theme.spacing.lg + (leading ? 48 : 0) : 0} /> : null}
    </View>
  );
}

export function ListSection({
  title,
  children,
  style,
}: {
  title?: string;
  children: ReactNode;
  style?: ViewStyle;
}) {
  const { theme } = useTheme();
  return (
    <View style={[{ marginBottom: theme.spacing.lg }, style]}>
      {title ? (
        <Label style={{ paddingHorizontal: theme.spacing.lg, marginBottom: theme.spacing.xs }}>
          {title.toUpperCase()}
        </Label>
      ) : null}
      <View
        style={{
          backgroundColor: theme.colors.surface,
          borderRadius: theme.radii.lg,
          borderWidth: 1,
          borderColor: theme.colors.border,
          overflow: "hidden",
        }}
      >
        {children}
      </View>
    </View>
  );
}
