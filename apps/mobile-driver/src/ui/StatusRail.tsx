import { View, Text, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import type { Handshake } from "../types";

function Dot({ ok, warn }: { ok: boolean; warn?: boolean }) {
  return <View style={[styles.dot, ok ? styles.ok : warn ? styles.warn : styles.bad]} />;
}

export function StatusRail({ handshake }: { handshake: Handshake }) {
  const pushOk = handshake.push.registered;
  const pushWarn = handshake.push.kind === "apns" || handshake.push.kind === "expo";
  const platformOk = handshake.platformStatus === "ok" || handshake.platformStatus === "unknown";
  const platformWarn = handshake.platformStatus === "degraded";

  return (
    <View style={styles.wrap} testID="handshake-rail">
      <View style={styles.rail}>
        <View style={styles.chip}>
          <Dot ok={handshake.api === "up"} />
          <Text style={styles.chipText}>API</Text>
        </View>
        <View style={styles.chip}>
          <Dot ok={handshake.auth === "up"} />
          <Text style={styles.chipText}>Auth</Text>
        </View>
        <View style={styles.chip}>
          <Dot ok={pushOk} warn={pushWarn && !pushOk} />
          <Text style={styles.chipText}>Push</Text>
        </View>
        <View style={styles.chip}>
          <Dot ok={platformOk && !platformWarn} warn={platformWarn} />
          <Text style={styles.chipText}>Platform</Text>
        </View>
      </View>
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
  wrap: { gap: spacing.sm },
  rail: {
    flexDirection: "row",
    gap: spacing.sm,
    flexWrap: "wrap",
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chipText: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: "600",
  },
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
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  ok: { backgroundColor: colors.success },
  warn: { backgroundColor: "#d97706" },
  bad: { backgroundColor: colors.danger },
});
