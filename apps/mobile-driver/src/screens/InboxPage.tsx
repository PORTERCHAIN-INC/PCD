/** Notifications inbox: newest first, unread dot, mark all read (optimistic). */
import { StyleSheet, Text, View } from "react-native";
import { useInbox, useMarkAllRead } from "../data/queries";
import { Skeleton } from "../ui/motion";
import { Section } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { Button } from "../ui/kit";
import { color, space } from "../ui/theme";
import { UpdatedAgo } from "../ui/UpdatedAgo";

const when = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString("en-CA", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "";

export function InboxPage({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Sheet visible={visible} title="Notifications" onClose={onClose} testID="page-inbox">
      <InboxBody />
    </Sheet>
  );
}

export function InboxBody() {
  const q = useInbox();
  const mark = useMarkAllRead();
  if (!q.data) return <Skeleton width="100%" height={240} />;
  const items = q.data.items ?? [];
  return (
    <View style={st.wrap}>
      <UpdatedAgo at={q.dataUpdatedAt} fetching={q.isFetching} />
      {q.data.unread_count ? (
        <Button
          label={`Mark ${q.data.unread_count} as read`}
          onPress={() => mark.mutate()}
          testID="inbox-mark-all"
        />
      ) : null}
      <Section title="RECENT" testID="inbox-list">
        {items.length ? (
          items.slice(0, 50).map((n) => (
            <View key={n.id} style={st.item}>
              <View style={[st.dot, !n.is_read && st.dotOn]} />
              <View style={st.flex}>
                <Text style={[st.title, n.is_read && st.read]} numberOfLines={1}>
                  {n.title}
                </Text>
                <Text style={st.body} numberOfLines={2}>
                  {n.body}
                </Text>
                <Text style={st.when}>{when(n.created_at)}</Text>
              </View>
            </View>
          ))
        ) : (
          <View style={st.item}>
            <Text style={st.body}>You're all caught up.</Text>
          </View>
        )}
      </Section>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.lg },
  flex: { flex: 1 },
  item: {
    flexDirection: "row",
    gap: space.md,
    padding: space.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.border,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginTop: 7, backgroundColor: "transparent" },
  dotOn: { backgroundColor: color.primary },
  title: { fontSize: 16, fontWeight: "800", color: color.ink },
  read: { color: color.inkMuted, fontWeight: "700" },
  body: { fontSize: 14, lineHeight: 19, color: color.inkMuted, marginTop: 2 },
  when: { fontSize: 12, color: color.inkFaint, marginTop: 4 },
});
