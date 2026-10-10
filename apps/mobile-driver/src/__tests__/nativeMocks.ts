import { vi } from "vitest";

/** In-memory AsyncStorage, encrypted-blob store and SecureStore shared by the tests. */
export const storage = new Map<string, string>();
export const blobs = new Map<string, unknown>();
const secure = new Map<string, string>();

export const asyncStorageMock = {
  getItem: vi.fn(async (k: string) => storage.get(k) ?? null),
  setItem: vi.fn(async (k: string, v: string) => {
    storage.set(k, v);
  }),
  removeItem: vi.fn(async (k: string) => {
    storage.delete(k);
  }),
  multiRemove: vi.fn(async (keys: string[]) => {
    keys.forEach((k) => storage.delete(k));
  }),
};

let n = 0;
export const secureBlobMock = {
  writeSecureBlob: vi.fn(async (value: unknown) => {
    const id = `blob-${++n}`;
    blobs.set(id, value);
    return id;
  }),
  readSecureBlob: vi.fn(async (id: string) => {
    if (!blobs.has(id)) throw new Error("pod_blob_missing");
    return blobs.get(id);
  }),
  deleteSecureBlob: vi.fn((id: string) => {
    blobs.delete(id);
  }),
  wipeSecureBlobs: vi.fn(async () => {
    blobs.clear();
    secure.clear();
  }),
};

export function resetNative() {
  storage.clear();
  blobs.clear();
  secure.clear();
  vi.clearAllMocks();
}
