import { create } from "zustand";
import { getJson, getMmkvStore, setJson } from "@porterchain/mobile-storage";
import type { ColorScheme } from "@porterchain/mobile-theme";

const store = getMmkvStore("porterchain-customer");

type SettingsStore = {
  themePreference: ColorScheme | "system";
  visitorSessionId: string;
  localNotifications: Array<{
    id: string;
    title: string;
    body: string;
    created_at: string;
    read: boolean;
  }>;
  hydrate: () => void;
  setThemePreference: (pref: ColorScheme | "system") => void;
  ensureVisitorSession: () => string;
  pushLocalNotification: (title: string, body: string) => void;
  markNotificationRead: (id: string) => void;
};

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  themePreference: "system",
  visitorSessionId: "",
  localNotifications: [],
  hydrate: () => {
    set({
      themePreference: getJson(store, "customer.theme", "system" as ColorScheme | "system"),
      visitorSessionId: getJson(store, "customer.visitor_session", ""),
      localNotifications: getJson(store, "customer.notifications", []),
    });
  },
  setThemePreference: (pref) => {
    setJson(store, "customer.theme", pref);
    set({ themePreference: pref });
  },
  ensureVisitorSession: () => {
    let id = get().visitorSessionId;
    if (!id) {
      id = `mob-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      setJson(store, "customer.visitor_session", id);
      set({ visitorSessionId: id });
    }
    return id;
  },
  pushLocalNotification: (title, body) => {
    const row = {
      id: `${Date.now()}`,
      title,
      body,
      created_at: new Date().toISOString(),
      read: false,
    };
    const next = [row, ...get().localNotifications].slice(0, 100);
    setJson(store, "customer.notifications", next);
    set({ localNotifications: next });
  },
  markNotificationRead: (id) => {
    const next = get().localNotifications.map((n) => (n.id === id ? { ...n, read: true } : n));
    setJson(store, "customer.notifications", next);
    set({ localNotifications: next });
  },
}));
