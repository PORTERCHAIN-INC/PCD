"use client";

import { ScrollView, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Caption,
  Card,
  EmptyState,
  ListItem,
  ListSection,
  Screen,
  StatusChip,
} from "@porterchain/mobile-ui";
import { useOfflineSync } from "../provider/OfflineSyncProvider";

function labelForAction(actionType: string) {
  return actionType.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function OfflineSyncPanel() {
  const { theme } = useTheme();
  const {
    online,
    syncing,
    lastSyncAt,
    localPending,
    localFailed,
    uploadPending,
    gpsPending,
    serverStatus,
    queue,
    syncNow,
    retryFailed,
  } = useOfflineSync();

  return (
    <Screen>
      <View style={{ padding: theme.spacing.lg, gap: theme.spacing.sm }}>
        <Body style={{ fontSize: 24, fontWeight: "700" }}>Offline sync</Body>
        <Caption>
          {online ? "Connected" : "Offline"} · {localPending} local ·{" "}
          {serverStatus?.pending_count ?? 0} server pending
        </Caption>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, flexWrap: "wrap" }}>
          <StatusChip
            label={`${uploadPending} uploads`}
            tone={uploadPending > 0 ? "warning" : "neutral"}
          />
          <StatusChip label={`${gpsPending} GPS`} tone={gpsPending > 0 ? "info" : "neutral"} />
          <StatusChip
            label={`${localFailed} failed`}
            tone={localFailed > 0 ? "danger" : "neutral"}
          />
        </View>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
          <Button label="Sync now" loading={syncing} onPress={() => void syncNow()} />
          {localFailed > 0 ? (
            <Button label="Retry failed" variant="secondary" onPress={() => void retryFailed()} />
          ) : null}
        </View>
        {lastSyncAt ? (
          <Caption>Last sync {lastSyncAt.slice(0, 19).replace("T", " ")}</Caption>
        ) : null}
      </View>

      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, paddingTop: 0 }}>
        <ListSection title="Local queue">
          {queue.length === 0 ? (
            <EmptyState title="Queue empty" message="Actions captured offline will appear here." />
          ) : (
            queue.map((row) => (
              <Card key={row.id} style={{ marginBottom: theme.spacing.sm }}>
                <ListItem
                  title={labelForAction(row.action_type)}
                  subtitle={row.last_error ?? row.status}
                  meta={row.created_at.slice(0, 16)}
                  trailing={
                    <StatusChip
                      label={row.status}
                      tone={row.status === "failed" ? "danger" : "pending"}
                    />
                  }
                  showDivider={false}
                />
              </Card>
            ))
          )}
        </ListSection>

        {serverStatus ? (
          <ListSection title="Server queue">
            {serverStatus.pending.map((row) => (
              <ListItem
                key={row.id}
                title={labelForAction(row.action_type)}
                subtitle={row.error ?? "pending on server"}
                meta={row.created_at?.slice(0, 16) ?? undefined}
              />
            ))}
            {serverStatus.failed.map((row) => (
              <ListItem
                key={row.id}
                title={labelForAction(row.action_type)}
                subtitle={row.error ?? "failed on server"}
                meta={row.created_at?.slice(0, 16) ?? undefined}
              />
            ))}
          </ListSection>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
