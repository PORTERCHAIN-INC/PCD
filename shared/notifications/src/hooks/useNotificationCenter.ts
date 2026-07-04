import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { InboxFilter, NotificationCenterAdapter, NotificationInboxItem } from "../types";
import { filterInboxItems, groupInboxItems } from "../group";

export function useNotificationCenter(
  adapter: NotificationCenterAdapter,
  mode: "driver" | "customer",
  filter: InboxFilter = "all"
) {
  const queryClient = useQueryClient();
  const queryKey = useMemo(() => ["notifications", mode, filter], [mode, filter]);

  const inboxQuery = useQuery({
    queryKey,
    queryFn: () => adapter.fetchInbox(filter),
  });

  const historyQuery = useQuery({
    queryKey: ["notifications", mode, "history"],
    queryFn: () => adapter.fetchHistory(),
    enabled: false,
  });

  const [liveItems, setLiveItems] = useState<NotificationInboxItem[]>([]);

  useEffect(() => {
    setLiveItems(inboxQuery.data?.items ?? []);
  }, [inboxQuery.data?.items]);

  const unreadCount = inboxQuery.data?.unread_count ?? 0;
  const filteredItems = useMemo(
    () => filterInboxItems(liveItems, filter),
    [liveItems, filter]
  );
  const groups = useMemo(
    () => groupInboxItems(filteredItems, inboxQuery.data?.by_group, mode),
    [filteredItems, inboxQuery.data?.by_group, mode]
  );

  const refresh = useCallback(async () => {
    await inboxQuery.refetch();
  }, [inboxQuery]);

  const pushRealtimeItem = useCallback((item: NotificationInboxItem) => {
    setLiveItems((prev) => {
      const without = prev.filter((row) => row.id !== item.id);
      return [item, ...without];
    });
    void queryClient.invalidateQueries({ queryKey: ["notifications", mode] });
  }, [mode, queryClient]);

  const markRead = useCallback(
    async (id: string) => {
      await adapter.markRead(id);
      setLiveItems((prev) => prev.map((row) => (row.id === id ? { ...row, is_read: true } : row)));
      await queryClient.invalidateQueries({ queryKey: ["notifications", mode] });
    },
    [adapter, mode, queryClient]
  );

  const markArchive = useCallback(
    async (id: string) => {
      await adapter.markArchive(id);
      setLiveItems((prev) => prev.filter((row) => row.id !== id));
      await queryClient.invalidateQueries({ queryKey: ["notifications", mode] });
    },
    [adapter, mode, queryClient]
  );

  const markAllRead = useCallback(async () => {
    await adapter.markAllRead();
    setLiveItems((prev) => prev.map((row) => ({ ...row, is_read: true })));
    await queryClient.invalidateQueries({ queryKey: ["notifications", mode] });
  }, [adapter, mode, queryClient]);

  const loadHistory = useCallback(async () => {
    const result = await historyQuery.refetch();
    return result.data?.items ?? [];
  }, [historyQuery]);

  return {
    isLoading: inboxQuery.isLoading,
    isError: inboxQuery.isError,
    unreadCount,
    items: filteredItems,
    groups,
    refresh,
    pushRealtimeItem,
    markRead,
    markArchive,
    markAllRead,
    loadHistory,
    historyItems: historyQuery.data?.items ?? [],
    isHistoryLoading: historyQuery.isLoading,
  };
}
