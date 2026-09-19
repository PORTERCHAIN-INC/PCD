import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import {
  fetchInbox,
  fetchInboxHistory,
  markAllNotificationsRead,
  markNotificationArchived,
  markNotificationRead,
} from "../api";
import { Card, CardTitle } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import type { InboxNotification, InboxSnapshot } from "../types";

type Props = {
  onBack: () => void;
  onOpenJob: (orderId: string) => void;
};

export function InboxScreen({ onBack, onOpenJob }: Props) {
  const [inbox, setInbox] = useState<InboxSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const reload = useCallback(() => {
    const load = showHistory ? fetchInboxHistory() : fetchInbox();
    void load.then(setInbox).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "inbox_failed");
    });
  }, [showHistory]);

  useEffect(() => {
    reload();
  }, [reload]);

  const run = async (id: string, work: () => Promise<unknown>) => {
    setBusy(id);
    setError(null);
    try {
      await work();
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "action_failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Screen testID="mobile-inbox">
      <PrimaryButton tone="ghost" label="Back" onPress={onBack} />
      <Text style={styles.title}>Inbox</Text>
      <Text style={styles.lede}>
        {inbox
          ? showHistory
            ? `${inbox.items?.length ?? 0} archived`
            : `${inbox.unread_count} unread`
          : "Assignments and dispatch messages"}
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={styles.row}>
        <PrimaryButton
          tone="ghost"
          label={showHistory ? "Active" : "History"}
          disabled={Boolean(busy)}
          testID="inbox-history-toggle"
          onPress={() => setShowHistory((v) => !v)}
        />
        {!showHistory ? (
          <PrimaryButton
            tone="ghost"
            label={busy === "all" ? "Marking…" : "Mark all read"}
            disabled={Boolean(busy)}
            onPress={() => void run("all", () => markAllNotificationsRead())}
          />
        ) : null}
        <PrimaryButton tone="ghost" label="Refresh" disabled={Boolean(busy)} onPress={reload} />
      </View>
      <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
        {(inbox?.items ?? []).map((item) => (
          <NotificationCard
            key={item.id}
            item={item}
            busy={busy === item.id}
            onRead={() => void run(item.id, () => markNotificationRead(item.id))}
            onArchive={() => void run(item.id, () => markNotificationArchived(item.id))}
            onOpenJob={onOpenJob}
          />
        ))}
        {inbox && inbox.items.length === 0 ? (
          <Text style={styles.meta}>No messages yet.</Text>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

function NotificationCard({
  item,
  busy,
  onRead,
  onArchive,
  onOpenJob,
}: {
  item: InboxNotification;
  busy: boolean;
  onRead: () => void;
  onArchive: () => void;
  onOpenJob: (orderId: string) => void;
}) {
  return (
    <Card style={item.is_read ? undefined : styles.unread}>
      <CardTitle>{item.title || "Notification"}</CardTitle>
      <Text style={styles.body}>{item.body}</Text>
      <Text style={styles.meta}>
        {(item.group || item.category || "general").replace(/_/g, " ")}
        {item.created_at ? ` · ${new Date(item.created_at).toLocaleString()}` : ""}
        {item.is_read ? "" : " · unread"}
      </Text>
      <View style={styles.row}>
        {!item.is_read ? (
          <PrimaryButton
            tone="ghost"
            label={busy ? "…" : "Mark read"}
            disabled={busy}
            onPress={onRead}
          />
        ) : null}
        <PrimaryButton tone="ghost" label="Archive" disabled={busy} onPress={onArchive} />
        {item.order_id ? (
          <PrimaryButton
            tone="ghost"
            label="Open job"
            disabled={busy}
            onPress={() => onOpenJob(item.order_id as string)}
          />
        ) : null}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
  list: { gap: spacing.md, paddingBottom: spacing.xl },
  body: { ...typography.body, color: colors.primary },
  meta: { ...typography.caption, color: colors.muted },
  row: { gap: spacing.sm, marginTop: spacing.sm },
  unread: { borderColor: colors.secondary, borderWidth: 1 },
});
