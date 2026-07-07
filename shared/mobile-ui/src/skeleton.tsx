"use client";

import { useEffect } from "react";
import { View, type ViewStyle } from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  interpolate,
} from "react-native-reanimated";
import { useTheme } from "@porterchain/mobile-theme";

export function Skeleton({
  width,
  height = 16,
  borderRadius,
  style,
}: {
  width?: number | `${number}%`;
  height?: number;
  borderRadius?: number;
  style?: ViewStyle;
}) {
  const { theme } = useTheme();
  const shimmer = useSharedValue(0);

  useEffect(() => {
    shimmer.value = withRepeat(withTiming(1, { duration: 1200 }), -1, false);
  }, [shimmer]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: interpolate(shimmer.value, [0, 0.5, 1], [0.55, 1, 0.55]),
  }));

  return (
    <Animated.View
      style={[
        {
          width: width ?? "100%",
          height,
          borderRadius: borderRadius ?? theme.radii.sm,
          backgroundColor: theme.colors.skeleton,
        },
        animatedStyle,
        style,
      ]}
    />
  );
}

export function SkeletonCard() {
  const { theme } = useTheme();
  return (
    <View
      style={{
        padding: theme.spacing.lg,
        borderRadius: theme.radii.lg,
        backgroundColor: theme.colors.surface,
        borderWidth: 1,
        borderColor: theme.colors.border,
        gap: theme.spacing.md,
      }}
    >
      <Skeleton height={20} width="60%" />
      <Skeleton height={14} width="90%" />
      <Skeleton height={14} width="75%" />
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginTop: theme.spacing.sm }}>
        <Skeleton height={36} width={100} borderRadius={theme.radii.md} />
        <Skeleton height={36} width={100} borderRadius={theme.radii.md} />
      </View>
    </View>
  );
}

export function SkeletonList({ count = 4 }: { count?: number }) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.md }}>
      {Array.from({ length: count }).map((_, i) => (
        <View key={i} style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.md }}>
          <Skeleton width={44} height={44} borderRadius={theme.radii.md} />
          <View style={{ flex: 1, gap: theme.spacing.xs }}>
            <Skeleton height={16} width="70%" />
            <Skeleton height={12} width="45%" />
          </View>
        </View>
      ))}
    </View>
  );
}
