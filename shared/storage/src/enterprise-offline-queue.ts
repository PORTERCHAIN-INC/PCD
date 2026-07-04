import type { OfflineAction, OfflineQueueAdapter } from "@porterchain/mobile-api";
import { entityKeyForAction } from "@porterchain/mobile-api";
import { getJson, getMmkvStore, setJson, storageKeys } from "./mmkv";

function createClientId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export function createEnterpriseOfflineQueue(storeId = "porterchain-offline"): OfflineQueueAdapter {
  const store = getMmkvStore(storeId);

  const read = () => getJson<OfflineAction[]>(store, storageKeys.offlineQueue, []);
  const write = (queue: OfflineAction[]) => setJson(store, storageKeys.offlineQueue, queue);

  return {
    enqueue(action) {
      const queue = read();
      const entityKey = action.entity_key ?? entityKeyForAction(action.action_type, action.payload);
      if (entityKey) {
        const existing = queue.find(
          (row) =>
            row.entity_key === entityKey &&
            row.status !== "synced" &&
            row.action_type === action.action_type
        );
        if (existing) {
          const updated: OfflineAction = {
            ...existing,
            payload: action.payload,
            client_id: action.client_id ?? existing.client_id,
            status: "queued",
            last_error: null,
          };
          write(queue.map((row) => (row.id === existing.id ? updated : row)));
          return updated;
        }
      }

      const row: OfflineAction = {
        ...action,
        id: createClientId(),
        client_id: action.client_id ?? createClientId(),
        created_at: new Date().toISOString(),
        status: "queued",
        retry_count: 0,
        entity_key: entityKey,
      };
      queue.push(row);
      write(queue);
      return row;
    },
    list() {
      return read();
    },
    update(id, patch) {
      const queue = read();
      let updated: OfflineAction | null = null;
      const next = queue.map((row) => {
        if (row.id !== id) return row;
        updated = { ...row, ...patch };
        return updated;
      });
      write(next);
      return updated;
    },
    remove(id) {
      write(read().filter((row) => row.id !== id));
    },
    clear() {
      store.delete(storageKeys.offlineQueue);
    },
  };
}

export function getLastSyncAt(storeId: string): string | null {
  const store = getMmkvStore(storeId);
  return store.getString(storageKeys.lastSyncAt) ?? null;
}

export function setLastSyncAt(storeId: string, iso: string) {
  const store = getMmkvStore(storeId);
  store.set(storageKeys.lastSyncAt, iso);
}
