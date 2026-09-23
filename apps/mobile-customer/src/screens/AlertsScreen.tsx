import { useCallback, useEffect, useState } from "react";
import { Pressable, ScrollView, Text, StyleSheet } from "react-native";
import { colors, typography } from "@porterchain/mobile-theme";
import { fetchInbox, markAllRead, markRead, type InboxItem } from "../api";
import { humanCustomerError } from "../errors";
import { screenFromDeepLink } from "../linking";
import { EmptyState } from "../ui/Motion";
import { Screen } from "../ui/Screen";

export function AlertsScreen({ onTrack }: { onTrack: (tracking: string) => void }) {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    void fetchInbox()
      .then((inbox) => {
        setItems(inbox.items);
        setUnread(inbox.unread_count);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Screen>
      <Text style={styles.title}>Alerts</Text>
      <Text style={styles.meta}>
        {unread} unread. Push to this phone is off. Shipment updates appear in this list.
      </Text>
      {unread > 0 ? (
        <Pressable
          onPress={() => {
            void markAllRead().then(load);
          }}
        >
          <Text style={styles.link}>Mark all read</Text>
        </Pressable>
      ) : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView contentContainerStyle={styles.list}>
        {items.length === 0 ? (
          <EmptyState
            animation="inbox"
            title="No alerts yet"
            body="When a shipment moves, the update lands here."
          />
        ) : null}
        {items.map((item) => (
          <Pressable
            key={item.id}
            style={styles.row}
            onPress={() => {
              void markRead(item.id).then(load);
              const link = screenFromDeepLink(item.deep_link);
              if (link?.screen === "track" && link.tracking) onTrack(link.tracking);
            }}
          >
            <Text style={styles.strong}>{item.title}</Text>
            <Text style={styles.meta}>{item.body}</Text>
          </Pressable>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 30, color: colors.primary },
  meta: { ...typography.caption, color: colors.muted },
  link: { ...typography.caption, color: colors.secondary, fontWeight: "700" },
  error: { ...typography.caption, color: colors.danger },
  list: { gap: 8, paddingBottom: 24 },
  row: { backgroundColor: colors.white, borderRadius: 12, padding: 12, gap: 4 },
  strong: { ...typography.body, color: colors.primary, fontWeight: "700" },
});
