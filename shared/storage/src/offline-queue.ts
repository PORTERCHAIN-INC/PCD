import type { OfflineAction, OfflineQueueAdapter } from "@porterchain/mobile-api";
import { getJson, getMmkvStore, setJson, storageKeys } from "./mmkv";

export function createOfflineQueue(storeId = "porterchain-offline"): OfflineQueueAdapter {
  const store = getMmkvStore(storeId);

  return {
    enqueue(action) {
      const queue = getJson<OfflineAction[]>(store, storageKeys.offlineQueue, []);
      const row: OfflineAction = {
        ...action,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        client_id: action.client_id ?? `${Date.now()}`,
        created_at: new Date().toISOString(),
        status: "queued",
        retry_count: 0,
      };
      queue.push(row);
      setJson(store, storageKeys.offlineQueue, queue);
      return row;
    },
    list() {
      return getJson<OfflineAction[]>(store, storageKeys.offlineQueue, []);
    },
    update(id, patch) {
      const queue = getJson<OfflineAction[]>(store, storageKeys.offlineQueue, []);
      let updated: OfflineAction | null = null;
      const next = queue.map((row) => {
        if (row.id !== id) return row;
        updated = { ...row, ...patch };
        return updated;
      });
      setJson(store, storageKeys.offlineQueue, next);
      return updated;
    },
    remove(id) {
      const queue = getJson<OfflineAction[]>(store, storageKeys.offlineQueue, []);
      setJson(
        store,
        storageKeys.offlineQueue,
        queue.filter((row) => row.id !== id)
      );
    },
    clear() {
      store.delete(storageKeys.offlineQueue);
    },
  };
}
