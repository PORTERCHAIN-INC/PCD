/**
 * Instant data: TanStack Query with stale-while-revalidate and an encrypted, persisted cache.
 * Cold start hydrates Today / Job / Me / Settings / Documents from the last known data, then
 * refetches in the background. Skeletons only when there is no cache at all (first launch).
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import { focusManager, onlineManager, QueryClient } from "@tanstack/react-query";
import { AppState, Platform } from "react-native";
import NetInfo from "@react-native-community/netinfo";
import { openString, sealString } from "../secureBlob";
import { currentAppVersion } from "../version";
import { shouldPersist } from "./keys";

const CACHE_KEY = "pcd.driver.rq.v1";
export const CACHE_MAX_AGE = 7 * 24 * 3600 * 1000;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: CACHE_MAX_AGE,
      retry: 1,
      networkMode: "offlineFirst",
      refetchOnReconnect: true,
      refetchOnWindowFocus: true,
    },
    mutations: { networkMode: "offlineFirst" },
  },
});

/** Ciphertext only in AsyncStorage; the key is in the OS keystore and is wiped at sign-out. */
const encryptedStorage = {
  getItem: async (k: string) => {
    const v = await AsyncStorage.getItem(k);
    if (!v) return null;
    try {
      return await openString(v);
    } catch {
      await AsyncStorage.removeItem(k); // key rotated (signed out) → stale cache is unreadable
      return null;
    }
  },
  setItem: async (k: string, v: string) => AsyncStorage.setItem(k, await sealString(v)),
  removeItem: (k: string) => AsyncStorage.removeItem(k),
};

export const persister = createAsyncStoragePersister({
  storage: Platform.OS === "web" ? AsyncStorage : encryptedStorage,
  key: CACHE_KEY,
  throttleTime: 1_000,
});

export const persistOptions = {
  persister,
  maxAge: CACHE_MAX_AGE,
  buster: currentAppVersion(),
  dehydrateOptions: { shouldDehydrateQuery: shouldPersist },
};

let wired = false;
/** App foreground = window focus; NetInfo = online. Called once at startup. */
export function wireQueryLifecycle(): void {
  if (wired) return;
  wired = true;
  AppState.addEventListener("change", (s) => focusManager.setFocused(s === "active"));
  onlineManager.setEventListener((setOnline) =>
    NetInfo.addEventListener((st) =>
      setOnline(Boolean(st.isConnected && st.isInternetReachable !== false))
    )
  );
}

/** Sign-out / "Clear cache": drop memory + disk cache. */
export async function clearQueryCache(): Promise<void> {
  queryClient.clear();
  await persister.removeClient();
}
