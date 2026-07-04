"use client";

import { View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Caption } from "./typography";
import { StatusChip } from "./status-chip";
import type { StatusTone } from "@porterchain/mobile-theme";

export type TimelineItem = {
  id: string;
  title: string;
  subtitle?: string;
  timestamp?: string;
  tone?: StatusTone;
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  const { theme } = useTheme();

  return (
    <View style={{ paddingHorizontal: theme.spacing.lg }}>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <View key={item.id} style={{ flexDirection: "row", gap: theme.spacing.md }}>
            <View style={{ alignItems: "center", width: 20 }}>
              <View
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 5,
                  backgroundColor: theme.colors.secondary,
                  marginTop: 4,
                }}
              />
              {!isLast ? (
                <View
                  style={{
                    flex: 1,
                    width: 2,
                    backgroundColor: theme.colors.border,
                    marginVertical: theme.spacing.xs,
                  }}
                />
              ) : null}
            </View>
            <View style={{ flex: 1, paddingBottom: isLast ? 0 : theme.spacing.lg }}>
              <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: theme.spacing.sm }}>
                <Body style={{ fontWeight: "600", flex: 1 }}>{item.title}</Body>
                {item.tone ? <StatusChip label={item.tone} tone={item.tone} /> : null}
              </View>
              {item.subtitle ? <Caption style={{ marginTop: 2 }}>{item.subtitle}</Caption> : null}
              {item.timestamp ? <Caption style={{ marginTop: theme.spacing.xs }}>{item.timestamp}</Caption> : null}
            </View>
          </View>
        );
      })}
    </View>
  );
}
