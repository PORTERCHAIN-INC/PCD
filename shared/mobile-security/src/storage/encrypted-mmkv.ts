import { MMKV } from "react-native-mmkv";
import { getSecureValue, securityKeys, setSecureValue } from "./secure-session";

const encryptedStores = new Map<string, MMKV>();

async function getOrCreateEncryptionKey(storeId: string) {
  const keyName = `${securityKeys.mmkvEncryptionKey}.${storeId}`;
  let key = await getSecureValue(keyName);
  if (!key) {
    key = `${Date.now()}-${Math.random().toString(36).repeat(3)}`.slice(0, 32);
    await setSecureValue(keyName, key);
  }
  return key;
}

export async function getEncryptedMmkvStore(storeId: string): Promise<MMKV> {
  const existing = encryptedStores.get(storeId);
  if (existing) return existing;

  const encryptionKey = await getOrCreateEncryptionKey(storeId);
  const store = new MMKV({ id: storeId, encryptionKey });
  encryptedStores.set(storeId, store);
  return store;
}

export function getJsonEncrypted<T>(store: MMKV, key: string, fallback: T): T {
  const raw = store.getString(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function setJsonEncrypted(store: MMKV, key: string, value: unknown) {
  store.set(key, JSON.stringify(value));
}
