import { View, Text, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import type { Handshake } from "../types";
import { DEV_MENU_GUTTER } from "./Screen";

export function StatusRail({ handshake }: { handshake: Handshake }) {
  return (
    <View style={styles.wrap} testID="handshake-rail">
      {handshake.platformDetail ? (
        <Text style={styles.banner} testID="platform-degraded">
          {handshake.platformDetail}
        </Text>
      ) : null}
      {handshake.api !== "up" ? (
        <Text style={styles.offline} testID="offline-banner">
          Offline — API unreachable. Queued actions will sync when back on network.
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm, paddingRight: DEV_MENU_GUTTER },
  banner: {
    ...typography.caption,
    color: "#92400e",
    backgroundColor: "#fef3c7",
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontWeight: "600",
  },
  offline: {
    ...typography.caption,
    color: colors.danger,
    backgroundColor: "#fef2f2",
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontWeight: "600",
  },
});
