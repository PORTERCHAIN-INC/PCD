import type { GpsPing } from "@porterchain/mobile-api";
import { getJson, getMmkvStore, setJson } from "./mmkv";

const GPS_BUFFER_KEY = "offline.gps_buffer";
const MAX_GPS_BUFFER = 500;

export function createGpsBuffer(storeId: string) {
  const store = getMmkvStore(storeId);

  return {
    enqueue(ping: Omit<GpsPing, "recorded_at"> & { recorded_at?: string }) {
      const buffer = getJson<GpsPing[]>(store, GPS_BUFFER_KEY, []);
      buffer.push({ ...ping, recorded_at: ping.recorded_at ?? new Date().toISOString() });
      if (buffer.length > MAX_GPS_BUFFER) buffer.splice(0, buffer.length - MAX_GPS_BUFFER);
      setJson(store, GPS_BUFFER_KEY, buffer);
    },
    list() {
      return getJson<GpsPing[]>(store, GPS_BUFFER_KEY, []);
    },
    remove(count: number) {
      const buffer = getJson<GpsPing[]>(store, GPS_BUFFER_KEY, []);
      setJson(store, GPS_BUFFER_KEY, buffer.slice(count));
    },
    clear() {
      store.delete(GPS_BUFFER_KEY);
    },
    count() {
      return getJson<GpsPing[]>(store, GPS_BUFFER_KEY, []).length;
    },
  };
}
