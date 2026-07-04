"use client";

import type { ReactNode } from "react";
import { ActivityIndicator, StyleSheet, View, type ViewStyle } from "react-native";
import { shadowForScheme, useTheme } from "@porterchain/mobile-theme";
import { Caption } from "./typography";

export type MapFrameProps = {
  children?: ReactNode;
  loading?: boolean;
  height?: number;
  rounded?: boolean;
  overlay?: ReactNode;
  style?: ViewStyle;
};

/** Premium map chrome — wrap `react-native-maps` MapView from `@porterchain/mobile-maps`. */
export function MapFrame({
  children,
  loading,
  height = 240,
  rounded = true,
  overlay,
  style,
}: MapFrameProps) {
  const { theme } = useTheme();

  return (
    <View
      style={[
        {
          height,
          borderRadius: rounded ? theme.radii.lg : 0,
          overflow: "hidden",
          backgroundColor: theme.colors.surfaceMuted,
          borderWidth: 1,
          borderColor: theme.colors.border,
          ...shadowForScheme("md", theme.scheme),
        },
        style,
      ]}
    >
      {children ?? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
          <Caption>Map preview</Caption>
        </View>
      )}
      {loading ? (
        <View
          style={{
            ...StyleSheet.absoluteFillObject,
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: theme.colors.overlay,
          }}
        >
          <ActivityIndicator color={theme.colors.secondary} />
        </View>
      ) : null}
      {overlay ? (
        <View style={{ position: "absolute", top: theme.spacing.md, left: theme.spacing.md, right: theme.spacing.md }}>
          {overlay}
        </View>
      ) : null}
    </View>
  );
}
