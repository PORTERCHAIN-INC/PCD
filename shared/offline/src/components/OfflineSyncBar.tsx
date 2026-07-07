"use client";

import { ActivityIndicator, Pressable, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Caption } from "@porterchain/mobile-ui";
import { useOfflineSync } from "../provider/OfflineSyncProvider";

export function OfflineSyncBar() {
  const { theme } = useTheme();
  const { online, syncing, localPending, localFailed, gpsPending, uploadPending, syncNow } =
    useOfflineSync();

  const hasQueue =
    localPending > 0 || localFailed > 0 || uploadPending > 0 || gpsPending > 0;

  // Only surface the bar when offline or there is real queue work to show.
  if (online && !hasQueue) return null;

  const tone = !online
    ? theme.colors.warning
    : localFailed > 0
      ? theme.colors.danger
      : theme.colors.secondary;

  return (
    <Pressable
      onPress={() => void syncNow()}
      style={{
        backgroundColor: tone,
        paddingVertical: theme.spacing.sm,
        paddingHorizontal: theme.spacing.lg,
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        gap: theme.spacing.md,
      }}
    >
      <View style={{ flex: 1, gap: 2 }}>
        <Body style={{ color: theme.colors.onPrimary, fontWeight: "600" }}>
          {!online ? "Offline mode" : syncing ? "Syncing…" : "Sync pending"}
        </Body>
        <Caption style={{ color: theme.colors.onPrimary }}>
          {localPending} queued · {uploadPending} uploads · {gpsPending} GPS
          {localFailed > 0 ? ` · ${localFailed} failed` : ""}
        </Caption>
      </View>
      {syncing ? <ActivityIndicator color={theme.colors.onPrimary} /> : null}
    </Pressable>
  );
}
