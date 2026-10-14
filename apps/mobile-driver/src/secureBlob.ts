/**
 * Encrypted on-device storage for proof-of-delivery data (photos, signatures, OTP) while it
 * waits to sync. AES-256-GCM via expo-crypto; the key lives in the OS keystore (expo-secure-store);
 * ciphertext lives as files under documentDirectory/pod-outbox. Nothing sensitive goes in AsyncStorage.
 */
import {
  AESEncryptionKey,
  AESSealedData,
  aesDecryptAsync,
  aesEncryptAsync,
  randomUUID,
} from "expo-crypto";
import { Directory, File, Paths } from "expo-file-system";
import * as SecureStore from "expo-secure-store";

const KEY_NAME = "porterchain_driver_pod_key";
const DIR_NAME = "pod-outbox";

let cachedKey: AESEncryptionKey | null = null;

function outboxDir(): Directory {
  return new Directory(Paths.document, DIR_NAME);
}

async function getKey(): Promise<AESEncryptionKey> {
  if (cachedKey) return cachedKey;
  const stored = await SecureStore.getItemAsync(KEY_NAME);
  if (stored) {
    cachedKey = await AESEncryptionKey.import(stored, "base64");
    return cachedKey;
  }
  const fresh = await AESEncryptionKey.generate();
  await SecureStore.setItemAsync(KEY_NAME, await fresh.encoded("base64"), {
    keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
  });
  cachedKey = fresh;
  return fresh;
}

/** Encrypt a JSON-able value to a new file. Returns the blob id. Throws on any failure (never silent). */
export async function writeSecureBlob(value: unknown): Promise<string> {
  const key = await getKey();
  const plain = new TextEncoder().encode(JSON.stringify(value));
  const sealed = await aesEncryptAsync(plain, key);
  const dir = outboxDir();
  dir.create({ idempotent: true, intermediates: true });
  const id = randomUUID();
  const file = new File(dir, `${id}.bin`);
  file.write(await sealed.combined("base64"));
  return id;
}

export async function readSecureBlob<T = unknown>(id: string): Promise<T> {
  const key = await getKey();
  const file = new File(outboxDir(), `${id}.bin`);
  if (!file.exists) throw new Error("pod_blob_missing");
  const sealed = AESSealedData.fromCombined(await file.text());
  const bytes = await aesDecryptAsync(sealed, key, { output: "bytes" });
  return JSON.parse(new TextDecoder().decode(bytes)) as T;
}

export function deleteSecureBlob(id: string): void {
  try {
    const file = new File(outboxDir(), `${id}.bin`);
    if (file.exists) file.delete();
  } catch {
    /* already gone */
  }
}

/** Sign-out: delete every encrypted file and the key, so nothing left behind is readable. */
export async function wipeSecureBlobs(): Promise<void> {
  const dir = outboxDir();
  if (dir.exists) dir.delete();
  cachedKey = null;
  await SecureStore.deleteItemAsync(KEY_NAME);
}

/** Encrypt a string with the same device key (used by the encrypted query-cache persister). */
export async function sealString(plain: string): Promise<string> {
  const sealed = await aesEncryptAsync(new TextEncoder().encode(plain), await getKey());
  return sealed.combined("base64");
}

export async function openString(combined: string): Promise<string> {
  const bytes = await aesDecryptAsync(AESSealedData.fromCombined(combined), await getKey(), {
    output: "bytes",
  });
  return new TextDecoder().decode(bytes);
}
