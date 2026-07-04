import { useTheme } from "@porterchain/mobile-theme";
import { Headline, Body } from "@porterchain/mobile-ui";
import type { ReactNode } from "react";
import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export function ScreenHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View
      style={{
        paddingTop: insets.top + theme.spacing.md,
        paddingHorizontal: theme.spacing.lg,
        paddingBottom: theme.spacing.md,
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderColor: theme.colors.border,
        flexDirection: "row",
        alignItems: "flex-end",
        justifyContent: "space-between",
        gap: theme.spacing.md,
      }}
    >
      <View style={{ flex: 1 }}>
        <Headline>{title}</Headline>
        {subtitle ? (
          <Body muted style={{ marginTop: 2 }}>
            {subtitle}
          </Body>
        ) : null}
      </View>
      {right}
    </View>
  );
}
