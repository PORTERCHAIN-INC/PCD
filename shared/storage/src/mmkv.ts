import { MMKV } from "react-native-mmkv";

const stores = new Map<string, MMKV>();

export function getMmkvStore(id = "porterchain-default"): MMKV {
  let store = stores.get(id);
  if (!store) {
    store = new MMKV({ id });
    stores.set(id, store);
  }
  return store;
}

export const storageKeys = {
  themePreference: "theme.preference",
  locale: "locale",
  offlineQueue: "offline.queue",
  lastSyncAt: "offline.last_sync_at",
} as const;

export function getJson<T>(store: MMKV, key: string, fallback: T): T {
  const raw = store.getString(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function setJson(store: MMKV, key: string, value: unknown) {
  store.set(key, JSON.stringify(value));
}
