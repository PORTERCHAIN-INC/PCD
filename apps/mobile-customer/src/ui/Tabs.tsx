import { Pressable, Text, StyleSheet, View } from "react-native";
import { colors, typography } from "@porterchain/mobile-theme";

export type TabId = "home" | "book" | "activity" | "account" | "alerts";

const TABS: { id: TabId; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "book", label: "Book" },
  { id: "activity", label: "Activity" },
  { id: "alerts", label: "Alerts" },
  { id: "account", label: "Account" },
];

export function Tabs({ current, onChange }: { current: TabId; onChange: (tab: TabId) => void }) {
  return (
    <View style={styles.bar}>
      {TABS.map((tab) => {
        const active = tab.id === current;
        return (
          <Pressable
            key={tab.id}
            accessibilityRole="button"
            onPress={() => onChange(tab.id)}
            style={styles.item}
          >
            <Text style={active ? styles.active : styles.label}>{tab.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: `${colors.primary}14`,
    backgroundColor: colors.white,
    paddingBottom: 8,
    paddingTop: 8,
  },
  item: { flex: 1, alignItems: "center", minHeight: 44, justifyContent: "center" },
  label: { ...typography.caption, color: colors.muted },
  active: { ...typography.caption, color: colors.secondary, fontWeight: "700" },
});
