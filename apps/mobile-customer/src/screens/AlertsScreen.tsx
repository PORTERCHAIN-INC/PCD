import { View } from "react-native";
import { fetchInbox, markAllRead, markRead, type InboxItem } from "../api";
import { friendlyDate } from "../format";
import { screenFromDeepLink } from "../linking";
import { spacing, usePalette } from "../theme";
import { Banner, Card, Divider, EmptyNote, ListRow, SkeletonList, Txt } from "../ui/kit";
import { Screen } from "../ui/Screen";
import { useRemote } from "../ui/useRemote";

let cachedInbox: { items: InboxItem[]; unread_count: number } | null = null;

export function peekUnread(): number {
  return cachedInbox?.unread_count ?? 0;
}

export function AlertsScreen({
  onTrack,
  onUnread,
}: {
  onTrack: (tracking: string) => void;
  onUnread?: (n: number) => void;
}) {
  const c = usePalette();
  const { data, loading, refreshing, error, offline, refresh } = useRemote(async () => {
    const inbox = await fetchInbox();
    cachedInbox = { items: inbox.items, unread_count: inbox.unread_count };
    onUnread?.(inbox.unread_count);
    return cachedInbox;
  }, cachedInbox);
  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;

  return (
    <Screen
      scroll
      testID="alerts"
      title="Alerts"
      subtitle={unread ? `${unread} unread` : "Shipment updates land here."}
      refreshing={refreshing}
      onRefresh={() => void refresh()}
      headerRight={
        unread > 0 ? (
          <Txt
            v="callout"
            tone="accent"
            accessibilityRole="button"
            onPress={() => void markAllRead().then(refresh)}
            style={{ paddingVertical: 12 }}
          >
            Mark all read
          </Txt>
        ) : null
      }
    >
      {error ? (
        <Banner
          tone={offline ? "offline" : "danger"}
          text={error}
          action="Retry"
          onAction={() => void refresh()}
        />
      ) : null}
      {loading && !data ? <SkeletonList rows={3} /> : null}
      {data && items.length === 0 ? (
        <EmptyNote
          icon="notifications-outline"
          title="You're all caught up"
          body="When a shipment moves, the update lands here."
        />
      ) : null}
      {items.length ? (
        <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
          {items.map((item, i) => {
            const isUnread = !item.is_read;
            return (
              <View key={item.id}>
                {i ? <Divider /> : null}
                <ListRow
                  icon={isUnread ? "notifications" : "notifications-outline"}
                  title={item.title}
                  subtitle={[item.body, friendlyDate(item.created_at)].filter(Boolean).join(" · ")}
                  right={
                    isUnread ? (
                      <View
                        accessibilityLabel="Unread"
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: 5,
                          backgroundColor: c.secondary,
                        }}
                      />
                    ) : undefined
                  }
                  onPress={() => {
                    void markRead(item.id).then(refresh);
                    const link = screenFromDeepLink(item.deep_link);
                    if (link?.screen === "track" && link.tracking) onTrack(link.tracking);
                  }}
                />
              </View>
            );
          })}
        </Card>
      ) : null}
    </Screen>
  );
}
