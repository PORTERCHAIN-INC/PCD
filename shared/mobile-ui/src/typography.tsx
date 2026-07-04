"use client";

import { Text as RNText, type TextProps } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";

type Variant = "display" | "headline" | "title" | "body" | "bodyMedium" | "label" | "caption" | "overline" | "mono";

export type TypographyProps = TextProps & {
  variant?: Variant;
  muted?: boolean;
  inverse?: boolean;
};

export function Text({ variant = "body", muted, inverse, style, ...props }: TypographyProps) {
  const { theme } = useTheme();
  const base = theme.textStyles[variant];
  return (
    <RNText
      style={[
        base,
        muted && { color: theme.colors.textMuted },
        inverse && { color: theme.colors.textInverse },
        style,
      ]}
      {...props}
    />
  );
}

export const Display = (props: Omit<TypographyProps, "variant">) => <Text variant="display" {...props} />;
export const Headline = (props: Omit<TypographyProps, "variant">) => <Text variant="headline" {...props} />;
export const Title = (props: Omit<TypographyProps, "variant">) => <Text variant="title" {...props} />;
export const Body = (props: Omit<TypographyProps, "variant">) => <Text variant="body" {...props} />;
export const Label = (props: Omit<TypographyProps, "variant">) => <Text variant="label" {...props} />;
export const Caption = (props: Omit<TypographyProps, "variant">) => <Text variant="caption" {...props} />;
