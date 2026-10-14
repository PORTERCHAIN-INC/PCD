/** One glanceable sync status: Live · Saving N · Offline · N refused. Tap = sync now. */
import { StyleSheet, Text } from "react-native";
import { openRefusedReview } from "../refusedReview";
import { LiveDot, PressScale } from "./motion";
import { color, radius, type } from "./theme";

export function syncState(offline: boolean, pending: number, rejected: number) {
  if (rejected > 0) return { tone: "danger" as const, text: `${rejected} refused` };
  if (offline)
    return { tone: "warn" as const, text: pending ? `Offline · ${pending} saved` : "Offline" };
  if (pending > 0) return { tone: "info" as const, text: `Syncing ${pending}` };
  return { tone: "ok" as const, text: "Synced" };
}

export function SyncPill({
  offline,
  pending,
  rejected,
  onSync,
}: {
  offline: boolean;
  pending: number;
  rejected: number;
  onSync: () => void;
}) {
  const s = syncState(offline, pending, rejected);
  const ink =
    s.tone === "danger"
      ? color.danger
      : s.tone === "warn"
        ? color.warnInk
        : s.tone === "info"
          ? color.infoInk
          : color.inkMuted;
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={`Sync status: ${s.text}. ${rejected > 0 ? "Tap to review." : "Tap to sync now."}`}
      onPress={rejected > 0 ? openRefusedReview : onSync}
      hitSlop={8}
      style={styles.pill}
      testID="sync-pill"
    >
      <LiveDot on={s.tone === "ok"} size={8} />
      <Text style={[styles.text, { color: ink }]}>{s.text}</Text>
    </PressScale>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
    height: 40,
    paddingRight: 14,
    paddingLeft: 6,
    borderRadius: radius.pill,
    backgroundColor: color.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
  },
  text: { ...type.small, fontWeight: "800" },
});
