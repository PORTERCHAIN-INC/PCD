"use client";

import { View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Caption, Label } from "./typography";

export type BarChartPoint = { label: string; value: number };

export function BarChart({
  data,
  height = 160,
  barColor,
}: {
  data: BarChartPoint[];
  height?: number;
  barColor?: string;
}) {
  const { theme } = useTheme();
  const max = Math.max(...data.map((d) => d.value), 1);
  const fill = barColor ?? theme.colors.secondary;

  return (
    <View style={{ gap: theme.spacing.md }}>
      <View
        style={{
          height,
          flexDirection: "row",
          alignItems: "flex-end",
          gap: theme.spacing.sm,
          paddingTop: theme.spacing.md,
        }}
      >
        {data.map((point) => {
          const barHeight = Math.max((point.value / max) * (height - 24), 4);
          return (
            <View
              key={point.label}
              style={{ flex: 1, alignItems: "center", gap: theme.spacing.xs }}
            >
              <View
                style={{
                  width: "100%",
                  maxWidth: 48,
                  height: barHeight,
                  borderRadius: theme.radii.sm,
                  backgroundColor: fill,
                  opacity: point.value === 0 ? 0.25 : 1,
                }}
              />
              <Caption numberOfLines={1}>{point.label}</Caption>
            </View>
          );
        })}
      </View>
    </View>
  );
}

export function Sparkline({
  values,
  height = 48,
  color,
}: {
  values: number[];
  height?: number;
  color?: string;
}) {
  const { theme } = useTheme();
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const stroke = color ?? theme.colors.secondary;

  return (
    <View style={{ height, flexDirection: "row", alignItems: "flex-end", gap: 2 }}>
      {values.map((v, i) => (
        <View
          key={i}
          style={{
            flex: 1,
            height: Math.max(((v - min) / range) * height, 2),
            backgroundColor: stroke,
            borderRadius: 2,
            opacity: 0.85,
          }}
        />
      ))}
    </View>
  );
}

export function MetricCard({
  label,
  value,
  delta,
  trend,
}: {
  label: string;
  value: string;
  delta?: string;
  trend?: number[];
}) {
  const { theme } = useTheme();
  const deltaUp = delta?.startsWith("+");

  return (
    <View
      style={{
        padding: theme.spacing.lg,
        borderRadius: theme.radii.lg,
        backgroundColor: theme.colors.surface,
        borderWidth: 1,
        borderColor: theme.colors.border,
        gap: theme.spacing.sm,
      }}
    >
      <Label>{label}</Label>
      <View
        style={{ flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between" }}
      >
        <Label
          style={{
            fontSize: theme.typography.size["2xl"],
            color: theme.colors.text,
            fontWeight: "700",
          }}
        >
          {value}
        </Label>
        {delta ? (
          <Caption
            style={{
              color: deltaUp ? theme.colors.success : theme.colors.danger,
              fontWeight: "600",
            }}
          >
            {delta}
          </Caption>
        ) : null}
      </View>
      {trend ? <Sparkline values={trend} height={32} /> : null}
    </View>
  );
}
