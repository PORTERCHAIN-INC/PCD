import { type ReactNode } from "react";
import { View, StyleSheet } from "react-native";
import { TabBar } from "./TabBar";
import type { FieldTab } from "../types";

export function FieldShell({
  tab,
  onTab,
  badges,
  children,
}: {
  tab: FieldTab;
  onTab: (tab: FieldTab) => void;
  badges?: Partial<Record<FieldTab, number | null>>;
  children: ReactNode;
}) {
  return (
    <View style={styles.wrap}>
      <View style={styles.body}>{children}</View>
      <TabBar tab={tab} onChange={onTab} badges={badges} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1 },
  body: { flex: 1 },
});
