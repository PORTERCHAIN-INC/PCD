"use client";

import { forwardRef, type ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  View,
  type PressableProps,
  type ViewStyle,
} from "react-native";
import { a11yProps } from "@porterchain/mobile-hooks";
import { shadowForScheme, useTheme } from "@porterchain/mobile-theme";
import { Text } from "./typography";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";
export type ButtonSize = "sm" | "md" | "lg";

export type ButtonProps = Omit<PressableProps, "children"> & {
  label?: string;
  children?: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
};

function sizeStyles(size: ButtonSize, minTouch: number) {
  const map = {
    sm: { py: 8, px: 14, fontSize: 13, minHeight: 36 },
    md: { py: 12, px: 18, fontSize: 15, minHeight: minTouch },
    lg: { py: 16, px: 22, fontSize: 17, minHeight: 52 },
  };
  return map[size];
}

export const Button = forwardRef<View, ButtonProps>(function Button(
  {
    label,
    children,
    variant = "primary",
    size = "md",
    loading,
    fullWidth,
    leftIcon,
    rightIcon,
    disabled,
    style,
    ...props
  },
  ref
) {
  const { theme } = useTheme();
  const dims = sizeStyles(size, theme.layout.minTouchTarget);

  const palette: Record<ButtonVariant, { bg: string; text: string; border: string }> = {
    primary: { bg: theme.colors.secondary, text: theme.colors.onSecondary, border: "transparent" },
    secondary: {
      bg: theme.colors.surfaceElevated,
      text: theme.colors.text,
      border: theme.colors.border,
    },
    ghost: { bg: "transparent", text: theme.colors.secondary, border: "transparent" },
    danger: { bg: theme.colors.danger, text: theme.colors.onSecondary, border: "transparent" },
    outline: { bg: "transparent", text: theme.colors.secondary, border: theme.colors.secondary },
  };

  const colors = palette[variant];
  const content = children ?? label;

  return (
    <Pressable
      ref={ref}
      disabled={disabled || loading}
      style={({ pressed }) => [
        {
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "center",
          gap: theme.spacing.sm,
          minHeight: dims.minHeight,
          paddingVertical: dims.py,
          paddingHorizontal: dims.px,
          borderRadius: theme.radii.md,
          backgroundColor: colors.bg,
          borderWidth: variant === "outline" || variant === "secondary" ? 1 : 0,
          borderColor: colors.border,
          opacity: disabled ? 0.45 : pressed ? 0.92 : 1,
          alignSelf: fullWidth ? "stretch" : "auto",
          ...shadowForScheme(variant === "primary" ? "sm" : "none", theme.scheme),
        } as ViewStyle,
        typeof style === "function" ? style({ pressed }) : style,
      ]}
      {...(label ? a11yProps(label) : {})}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={colors.text} size="small" />
      ) : (
        <>
          {leftIcon}
          {typeof content === "string" ? (
            <Text style={{ color: colors.text, fontSize: dims.fontSize, fontWeight: "600" }}>
              {content}
            </Text>
          ) : (
            content
          )}
          {rightIcon}
        </>
      )}
    </Pressable>
  );
});
