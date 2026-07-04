"use client";

import { FlashList, type FlashListProps } from "@shopify/flash-list";
import { View, type ViewStyle } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Text } from "@porterchain/mobile-ui";

const DEFAULT_ESTIMATED_ITEM_SIZE = 72;
const DEFAULT_DRAW_DISTANCE = 250;

export function ListContainer({
  style,
  ...props
}: {
  style?: ViewStyle;
  children?: React.ReactNode;
}) {
  const { theme } = useTheme();
  return <View style={[{ flex: 1, backgroundColor: theme.colors.background }, style]} {...props} />;
}

export function AppFlashList<T>(props: FlashListProps<T>) {
  return (
    <FlashList
      estimatedItemSize={DEFAULT_ESTIMATED_ITEM_SIZE}
      drawDistance={DEFAULT_DRAW_DISTANCE}
      removeClippedSubviews
      {...props}
    />
  );
}

export function EmptyState({ title, message }: { title: string; message?: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ padding: theme.spacing.xl, alignItems: "center" }}>
      <Text style={{ fontWeight: "700", fontSize: theme.typography.size.lg }}>{title}</Text>
      {message ? (
        <Text
          style={{
            marginTop: theme.spacing.sm,
            color: theme.colors.textMuted,
            textAlign: "center",
          }}
        >
          {message}
        </Text>
      ) : null}
    </View>
  );
}

export function OfflineBanner() {
  const { theme } = useTheme();
  return (
    <View
      style={{
        backgroundColor: theme.colors.warning,
        paddingVertical: theme.spacing.sm,
        paddingHorizontal: theme.spacing.lg,
      }}
      accessibilityRole="text"
      accessibilityLabel="You are offline. Changes will sync when connected."
    >
      <Text style={{ color: theme.colors.surface, textAlign: "center", fontWeight: "600" }}>
        Offline — changes will sync when connected
      </Text>
    </View>
  );
}
