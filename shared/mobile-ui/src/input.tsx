"use client";

import { forwardRef, useState } from "react";
import { TextInput, View, type TextInputProps, type ViewStyle } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Caption, Label } from "./typography";

export type InputProps = TextInputProps & {
  label?: string;
  hint?: string;
  error?: string;
  containerStyle?: ViewStyle;
};

export const Input = forwardRef<TextInput, InputProps>(function Input(
  { label, hint, error, containerStyle, style, onFocus, onBlur, ...props },
  ref
) {
  const { theme } = useTheme();
  const [focused, setFocused] = useState(false);
  const borderColor = error
    ? theme.colors.danger
    : focused
      ? theme.colors.focus
      : theme.colors.border;

  return (
    <View style={[{ gap: theme.spacing.xs }, containerStyle]}>
      {label ? <Label>{label}</Label> : null}
      <TextInput
        ref={ref}
        placeholderTextColor={theme.colors.textMuted}
        onFocus={(e) => {
          setFocused(true);
          onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          onBlur?.(e);
        }}
        style={[
          {
            minHeight: theme.layout.minTouchTarget,
            borderRadius: theme.radii.md,
            borderWidth: 1.5,
            borderColor,
            backgroundColor: theme.colors.surface,
            paddingHorizontal: theme.spacing.lg,
            paddingVertical: theme.spacing.md,
            fontSize: theme.typography.size.md,
            color: theme.colors.text,
          },
          style,
        ]}
        accessibilityLabel={label}
        {...props}
      />
      {error ? (
        <Caption style={{ color: theme.colors.danger }}>{error}</Caption>
      ) : hint ? (
        <Caption>{hint}</Caption>
      ) : null}
    </View>
  );
});
