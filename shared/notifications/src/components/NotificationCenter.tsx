"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Pressable, View } from "react-native";
import { EnterpriseFlashList, LIST_ITEM_SIZES } from "@porterchain/mobile-performance";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Badge,
  Body,
  Button,
  Caption,
  Card,
  EmptyState,
  ListItem,
  Screen,
  SkeletonList,
  StatusChip,
} from "@porterchain/mobile-ui";
import { deepLinkFromItem, parseDeepLink } from "../deep-link";
import { useNotificationCenter } from "../hooks/useNotificationCenter";
import { useNotificationContext } from "../provider/NotificationProvider";
import type { InboxFilter, NotificationInboxItem } from "../types";

type CenterTab = "inbox" | "history" | "settings";

type NotificationRow =
  | { kind: "section"; id: string; title: string }
  | { kind: "item"; id: string; item: NotificationInboxItem };

export type NotificationCenterProps = {
  title?: string;
  subtitle?: string;
  showSettings?: boolean;
  settingsSlot?: ReactNode;
};

function FilterChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      style={{
        paddingHorizontal: theme.spacing.md,
        paddingVertical: theme.spacing.xs,
        borderRadius: theme.radii.full,
        backgroundColor: active ? theme.colors.primary : theme.colors.surfaceMuted,
      }}
    >
      <Caption style={{ color: active ? theme.colors.onPrimary : theme.colors.text }}>
        {label}
      </Caption>
    </Pressable>
  );
}

function NotificationRowCard({
  item,
  onOpen,
  onArchive,
}: {
  item: NotificationInboxItem;
  onOpen: () => void;
  onArchive: () => void;
}) {
  const { theme } = useTheme();
  const isCritical = item.priority === "critical";

  return (
    <Card style={{ marginBottom: theme.spacing.sm, opacity: item.is_read ? 0.85 : 1 }}>
      <ListItem
        title={item.title}
        subtitle={item.body}
        meta={item.created_at?.slice(0, 16) ?? undefined}
        leading={
          <View
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: item.is_read ? "transparent" : theme.colors.primary,
            }}
          />
        }
        trailing={
          <View style={{ flexDirection: "row", gap: theme.spacing.xs, alignItems: "center" }}>
            {isCritical ? <StatusChip tone="danger" label="Critical" /> : null}
            {item.priority === "high" ? <Badge variant="warning" label="High" /> : null}
          </View>
        }
        onPress={onOpen}
        showDivider={false}
        inset={false}
      />
      <View
        style={{
          flexDirection: "row",
          gap: theme.spacing.sm,
          paddingHorizontal: theme.spacing.lg,
          paddingBottom: theme.spacing.md,
        }}
      >
        <Button size="sm" variant="ghost" label="Archive" onPress={onArchive} />
      </View>
    </Card>
  );
}

export function NotificationCenter({
  title = "Notifications",
  subtitle,
  showSettings = true,
  settingsSlot,
}: NotificationCenterProps) {
  const { theme } = useTheme();
  const { adapter, mode, appScheme, onDeepLink, registerRealtimeConsumer, realtimeConnected } =
    useNotificationContext();
  const [tab, setTab] = useState<CenterTab>("inbox");
  const [filter, setFilter] = useState<InboxFilter>("all");

  const center = useNotificationCenter(adapter, mode, filter);

  useEffect(() => {
    return registerRealtimeConsumer(center.pushRealtimeItem);
  }, [center.pushRealtimeItem, registerRealtimeConsumer]);

  useEffect(() => {
    if (tab === "history") void center.loadHistory();
  }, [center, tab]);

  const resolvedSubtitle =
    subtitle ?? `${center.unreadCount} unread${realtimeConnected ? " · live" : ""}`;

  const openItem = async (item: NotificationInboxItem) => {
    if (!item.is_read) await center.markRead(item.id);
    const link = deepLinkFromItem(item, appScheme);
    if (link) {
      onDeepLink(link, item);
      return;
    }
    const parsed = parseDeepLink(item.deep_link ?? "", appScheme);
    if (parsed.screen) onDeepLink(parsed.raw, item);
  };

  const rows = useMemo((): NotificationRow[] => {
    if (tab === "history") {
      return center.historyItems.map((item) => ({ kind: "item", id: item.id, item }));
    }
    const next: NotificationRow[] = [];
    for (const group of center.groups) {
      next.push({ kind: "section", id: group.key, title: group.label });
      for (const item of group.items) {
        next.push({ kind: "item", id: item.id, item });
      }
    }
    return next;
  }, [center.groups, center.historyItems, tab]);

  const header = (
    <View style={{ padding: theme.spacing.lg, gap: theme.spacing.sm }}>
      <Body style={{ fontSize: 28, fontWeight: "700" }}>{title}</Body>
      <Caption>{resolvedSubtitle}</Caption>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, flexWrap: "wrap" }}>
        <FilterChip label="Inbox" active={tab === "inbox"} onPress={() => setTab("inbox")} />
        <FilterChip label="History" active={tab === "history"} onPress={() => setTab("history")} />
        {showSettings ? (
          <FilterChip
            label="Settings"
            active={tab === "settings"}
            onPress={() => setTab("settings")}
          />
        ) : null}
      </View>
      {tab === "inbox" ? (
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, flexWrap: "wrap" }}>
          <FilterChip label="All" active={filter === "all"} onPress={() => setFilter("all")} />
          <FilterChip
            label="Unread"
            active={filter === "unread"}
            onPress={() => setFilter("unread")}
          />
          <FilterChip label="Read" active={filter === "read"} onPress={() => setFilter("read")} />
        </View>
      ) : null}
      {tab === "inbox" && center.unreadCount > 0 ? (
        <Button
          size="sm"
          variant="secondary"
          label="Mark all read"
          onPress={() => void center.markAllRead()}
        />
      ) : null}
    </View>
  );

  if (tab === "settings" && settingsSlot) {
    return (
      <Screen>
        {header}
        <View style={{ padding: theme.spacing.lg, paddingTop: 0 }}>{settingsSlot}</View>
      </Screen>
    );
  }

  const loading = tab === "history" ? center.isHistoryLoading : center.isLoading;
  const empty = tab === "history" ? center.historyItems.length === 0 : center.items.length === 0;

  return (
    <Screen>
      {header}
      {loading ? (
        <View style={{ padding: theme.spacing.lg, paddingTop: 0 }}>
          <SkeletonList />
        </View>
      ) : empty ? (
        <View style={{ padding: theme.spacing.lg, paddingTop: 0 }}>
          <EmptyState
            title={tab === "history" ? "No archived notifications" : "Inbox clear"}
            message={tab === "history" ? "Archived items appear here." : "You're all caught up."}
          />
        </View>
      ) : (
        <EnterpriseFlashList
          data={rows}
          estimatedItemSize={LIST_ITEM_SIZES.notification}
          keyExtractor={(row) => row.id}
          contentContainerStyle={{ padding: theme.spacing.lg, paddingTop: 0 }}
          renderItem={({ item: row }) => {
            if (row.kind === "section") {
              return (
                <Body
                  style={{
                    fontWeight: "700",
                    marginTop: theme.spacing.md,
                    marginBottom: theme.spacing.sm,
                  }}
                >
                  {row.title}
                </Body>
              );
            }
            return (
              <NotificationRowCard
                item={row.item}
                onOpen={() => void openItem(row.item)}
                onArchive={() => void center.markArchive(row.item.id)}
              />
            );
          }}
        />
      )}
    </Screen>
  );
}
