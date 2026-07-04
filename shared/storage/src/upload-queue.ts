import type { OfflineUploadItem } from "@porterchain/mobile-api";
import { getJson, getMmkvStore, setJson } from "./mmkv";

const UPLOAD_QUEUE_KEY = "offline.upload_queue";

function createId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export function createUploadQueue(storeId: string) {
  const store = getMmkvStore(storeId);

  const read = () => getJson<OfflineUploadItem[]>(store, UPLOAD_QUEUE_KEY, []);
  const write = (items: OfflineUploadItem[]) => setJson(store, UPLOAD_QUEUE_KEY, items);

  return {
    enqueue(item: Omit<OfflineUploadItem, "id" | "created_at" | "status" | "retry_count">) {
      const queue = read();
      const row: OfflineUploadItem = {
        ...item,
        id: createId(),
        created_at: new Date().toISOString(),
        status: "pending",
        retry_count: 0,
      };
      queue.push(row);
      write(queue);
      return row;
    },
    list() {
      return read();
    },
    update(id: string, patch: Partial<OfflineUploadItem>) {
      const queue = read();
      let updated: OfflineUploadItem | null = null;
      const next = queue.map((row) => {
        if (row.id !== id) return row;
        updated = { ...row, ...patch };
        return updated;
      });
      write(next);
      return updated;
    },
    remove(id: string) {
      write(read().filter((row) => row.id !== id));
    },
    pendingCount() {
      return read().filter((row) => row.status === "pending" || row.status === "failed").length;
    },
  };
}
