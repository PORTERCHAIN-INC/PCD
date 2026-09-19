import { Pressable, Text, View, StyleSheet } from "react-native";
import { colors, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import type { FieldTab } from "../types";

const TABS: { id: FieldTab; label: string }[] = [
  { id: "work", label: "Work" },
  { id: "jobs", label: "Jobs" },
  { id: "money", label: "Money" },
  { id: "docs", label: "Docs" },
  { id: "more", label: "More" },
];

type Props = {
  tab: FieldTab;
  onChange: (tab: FieldTab) => void;
};

export function TabBar({ tab, onChange }: Props) {
  return (
    <View style={styles.bar} testID="driver-tabs">
      {TABS.map((item) => {
        const active = item.id === tab;
        return (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            testID={`tab-${item.id}`}
            onPress={() => onChange(item.id)}
            style={styles.tab}
          >
            <Text style={[styles.label, active && styles.active]}>{item.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: `${colors.primary}14`,
    paddingBottom: spacing.sm,
  },
  tab: {
    flex: 1,
    minHeight: Math.max(touchTargetMin, 52),
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.sm,
  },
  label: {
    ...typography.caption,
    color: colors.muted,
    fontWeight: "600",
  },
  active: {
    color: colors.driverGreen,
  },
});
