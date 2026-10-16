import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { haptic } from "../haptics";
import { type, usePalette } from "../theme";
import { Icon, type IconName } from "./kit";

export type TabId = "home" | "book" | "activity" | "account" | "alerts";

const TABS: { id: TabId; label: string; icon: IconName; iconOn: IconName }[] = [
  { id: "home", label: "Home", icon: "home-outline", iconOn: "home" },
  { id: "book", label: "Book", icon: "add-circle-outline", iconOn: "add-circle" },
  { id: "activity", label: "Activity", icon: "receipt-outline", iconOn: "receipt" },
  { id: "alerts", label: "Alerts", icon: "notifications-outline", iconOn: "notifications" },
  { id: "account", label: "Account", icon: "person-circle-outline", iconOn: "person-circle" },
];

export function Tabs({
  current,
  onChange,
  badges,
}: {
  current: TabId;
  onChange: (tab: TabId) => void;
  badges?: Partial<Record<TabId, number>>;
}) {
  const c = usePalette();
  return (
    <SafeAreaView style={{ backgroundColor: c.white }}>
      <View
        accessibilityRole="tablist"
        style={[styles.bar, { backgroundColor: c.white, borderTopColor: c.border }]}
      >
        {TABS.map((tab) => {
          const active = tab.id === current;
          const badge = badges?.[tab.id] ?? 0;
          return (
            <Pressable
              key={tab.id}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              accessibilityLabel={badge ? `${tab.label}, ${badge} unread` : tab.label}
              onPress={() => {
                if (!active) haptic.tap();
                onChange(tab.id);
              }}
              style={styles.item}
            >
              <View>
                <Icon
                  name={active ? tab.iconOn : tab.icon}
                  size={25}
                  color={active ? c.accentText : c.muted}
                />
                {badge > 0 ? (
                  <View
                    style={[
                      styles.badge,
                      {
                        backgroundColor: c.danger === "#fca5a5" ? "#ef4444" : c.danger,
                        borderColor: c.white,
                      },
                    ]}
                  >
                    <Text style={styles.badgeText} maxFontSizeMultiplier={1}>
                      {badge > 9 ? "9+" : badge}
                    </Text>
                  </View>
                ) : null}
              </View>
              <Text
                maxFontSizeMultiplier={1.2}
                style={[
                  type.caption,
                  {
                    fontSize: 11,
                    color: active ? c.accentText : c.muted,
                    fontWeight: active ? "700" : "500",
                  },
                ]}
              >
                {tab.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: 6,
    paddingBottom: 4,
  },
  item: { flex: 1, alignItems: "center", justifyContent: "center", minHeight: 48, gap: 2 },
  badge: {
    position: "absolute",
    top: -4,
    right: -10,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    paddingHorizontal: 4,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
  },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "800" },
});
