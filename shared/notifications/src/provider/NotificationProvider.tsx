import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AppState } from "react-native";
import * as Notifications from "expo-notifications";
import { setWebsocketMetrics, useForegroundAwareInterval } from "@porterchain/mobile-performance";
import { setBadgeCount } from "../badge";
import { setupNotificationCategories } from "../categories";
import { deepLinkFromPushData } from "../deep-link";
import { onForegroundMessage, getInitialNotification, onNotificationOpenedApp } from "../fcm";
import { setupNotificationChannels } from "../sound";
import type { DeepLinkHandler, NotificationCenterAdapter, NotificationInboxItem } from "../types";
import { NotificationRealtimeClient } from "../websocket";

export type NotificationProviderProps = {
  children: ReactNode;
  adapter: NotificationCenterAdapter;
  apiBaseUrl: string;
  getAccessToken: () => string | null;
  appScheme: string;
  mode: "driver" | "customer";
  onDeepLink: DeepLinkHandler;
  enabled?: boolean;
  orgId?: string;
};

type NotificationContextValue = {
  adapter: NotificationCenterAdapter;
  mode: "driver" | "customer";
  appScheme: string;
  onDeepLink: DeepLinkHandler;
  registerRealtimeConsumer: (consumer: (item: NotificationInboxItem) => void) => () => void;
  realtimeConnected: boolean;
};

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({
  children,
  adapter,
  apiBaseUrl,
  getAccessToken,
  appScheme,
  mode,
  onDeepLink,
  enabled = true,
  orgId,
}: NotificationProviderProps) {
  const consumersRef = useRef(new Set<(item: NotificationInboxItem) => void>());
  const clientRef = useRef<NotificationRealtimeClient | null>(null);
  const [realtimeConnected, setRealtimeConnected] = useState(false);

  const pushRealtimeItem = useCallback((item: NotificationInboxItem) => {
    consumersRef.current.forEach((consumer) => consumer(item));
  }, []);

  const registerRealtimeConsumer = useCallback(
    (consumer: (item: NotificationInboxItem) => void) => {
      consumersRef.current.add(consumer);
      return () => {
        consumersRef.current.delete(consumer);
      };
    },
    []
  );

  const syncBadge = useCallback(async () => {
    try {
      const inbox = await adapter.fetchInbox("all");
      await setBadgeCount(inbox.unread_count);
    } catch {
      // Ignore badge sync errors.
    }
  }, [adapter]);

  useEffect(() => {
    if (!enabled) return;
    void setupNotificationChannels();
    void setupNotificationCategories(mode);
  }, [enabled, mode]);

  useEffect(() => {
    if (!enabled) return;
    void syncBadge();
  }, [enabled, syncBadge]);

  useEffect(() => {
    if (!enabled) return;

    const client = new NotificationRealtimeClient({
      apiBaseUrl,
      getAccessToken,
      orgId,
      reconnectBaseMs: 4000,
      reconnectMaxMs: 60000,
      onStatusChange: (connected) => {
        setRealtimeConnected(connected);
        setWebsocketMetrics(connected, client.isPaused());
      },
      onEvent: (event) => {
        if (event.type === "notification") {
          pushRealtimeItem(event.payload);
          void syncBadge();
        }
        if (event.type === "unread_count") {
          void setBadgeCount(event.count);
        }
      },
    });

    clientRef.current = client;
    client.connect();

    const sub = AppState.addEventListener("change", (state) => {
      const paused = state !== "active";
      client.setPaused(paused);
      setWebsocketMetrics(realtimeConnected, paused);
    });

    return () => {
      sub.remove();
      client.disconnect();
      clientRef.current = null;
      setWebsocketMetrics(false, false);
    };
  }, [apiBaseUrl, enabled, getAccessToken, orgId, pushRealtimeItem, syncBadge]);

  useForegroundAwareInterval(() => clientRef.current?.ping(), enabled ? 30000 : null);

  useEffect(() => {
    if (!enabled) return;

    void getInitialNotification().then((message) => {
      const data = message?.data as Record<string, unknown> | undefined;
      const link = deepLinkFromPushData(data, appScheme);
      if (link) onDeepLink(link);
    });

    const unsubOpened = onNotificationOpenedApp((message) => {
      const data = message.data as Record<string, unknown> | undefined;
      const link = deepLinkFromPushData(data, appScheme);
      if (link) onDeepLink(link);
    });

    return () => unsubOpened();
  }, [appScheme, enabled, onDeepLink]);

  useEffect(() => {
    if (!enabled) return;

    const unsubFcm = onForegroundMessage((message) => {
      const data = (message as { data?: Record<string, unknown> }).data;
      const notification = (message as { notification?: { title?: string; body?: string } })
        .notification;
      const item: NotificationInboxItem = {
        id: String(data?.notification_id ?? data?.id ?? Date.now()),
        title: notification?.title ?? "Porterchain",
        body: notification?.body ?? "",
        is_read: false,
        created_at: new Date().toISOString(),
        deep_link: deepLinkFromPushData(data, appScheme) ?? undefined,
        priority: typeof data?.priority === "string" ? data.priority : undefined,
        category: typeof data?.category === "string" ? data.category : undefined,
      };
      pushRealtimeItem(item);
      void syncBadge();
    });

    const responseSub = Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as
        Record<string, unknown> | undefined;
      const actionId = response.actionIdentifier;
      const notificationId = data?.notification_id ?? data?.id;

      if (actionId === "archive" && typeof notificationId === "string") {
        void adapter.markArchive(notificationId);
        void syncBadge();
        return;
      }

      const link = deepLinkFromPushData(data, appScheme);
      if (link) onDeepLink(link);
    });

    return () => {
      if (typeof unsubFcm === "function") unsubFcm();
      responseSub.remove();
    };
  }, [adapter, appScheme, enabled, onDeepLink, pushRealtimeItem, syncBadge]);

  const value = useMemo(
    () => ({
      adapter,
      mode,
      appScheme,
      onDeepLink,
      registerRealtimeConsumer,
      realtimeConnected,
    }),
    [adapter, appScheme, mode, onDeepLink, registerRealtimeConsumer, realtimeConnected]
  );

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotificationContext() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotificationContext must be used within NotificationProvider");
  return ctx;
}
