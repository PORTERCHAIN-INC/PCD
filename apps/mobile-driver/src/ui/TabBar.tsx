import { Platform, Pressable, Text, View, StyleSheet } from "react-native";
import { colors, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import type { FieldTab } from "../types";

/** Ordered by a driver's day. Active = navy label + one accent bar; badges = needs action. */
export const TABS: { id: FieldTab; label: string }[] = [
  { id: "work", label: "Work" },
  { id: "jobs", label: "Jobs" },
  { id: "money", label: "Money" },
  { id: "docs", label: "Docs" },
  { id: "more", label: "More" },
];

type Props = {
  tab: FieldTab;
  onChange: (tab: FieldTab) => void;
  badges?: Partial<Record<FieldTab, number | null>>;
};

export function TabBar({ tab, onChange, badges }: Props) {
  return (
    <View style={styles.bar} testID="driver-tabs" accessibilityRole="tablist">
      {TABS.map((item) => {
        const active = item.id === tab;
        const n = badges?.[item.id] ?? 0;
        return (
          <Pressable
            key={item.id}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={n > 0 ? `${item.label}, ${n} need action` : item.label}
            testID={`tab-${item.id}`}
            onPress={() => onChange(item.id)}
            style={styles.tab}
          >
            {active ? <View style={styles.accent} /> : null}
            <Text style={[styles.label, active && styles.active]}>{item.label}</Text>
            {n > 0 ? (
              <View style={styles.badge} testID={`tab-${item.id}-badge`}>
                <Text style={styles.badgeText}>{n > 99 ? "99+" : n}</Text>
              </View>
            ) : null}
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
    paddingBottom: Platform.OS === "android" ? 20 : 28,
  },
  tab: {
    flex: 1,
    minHeight: Math.max(touchTargetMin, 52),
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.sm,
  },
  accent: {
    position: "absolute",
    top: 0,
    width: 28,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.driverGreen,
  },
  label: {
    ...typography.caption,
    color: colors.muted,
    fontWeight: "600",
  },
  active: {
    color: colors.primary,
    fontWeight: "800",
  },
  badge: {
    position: "absolute",
    top: 6,
    right: "22%",
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    paddingHorizontal: 4,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.driverGreen,
  },
  badgeText: { color: colors.white, fontSize: 11, fontWeight: "700" },
});
