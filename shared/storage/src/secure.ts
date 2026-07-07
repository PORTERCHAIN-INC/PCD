import * as SecureStore from "expo-secure-store";

const prefix = "porterchain.secure.";

export const secureKeys = {
  accessToken: `${prefix}access_token`,
  refreshToken: `${prefix}refresh_token`,
  driverId: `${prefix}driver_id`,
  customerId: `${prefix}customer_id`,
} as const;

export async function getSecureItem(key: string): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(key);
  } catch {
    return null;
  }
}

export async function setSecureItem(key: string, value: string): Promise<void> {
  await SecureStore.setItemAsync(key, value);
}

export async function deleteSecureItem(key: string): Promise<void> {
  await SecureStore.deleteItemAsync(key);
}

export async function clearSecureSession(): Promise<void> {
  await Promise.all(Object.values(secureKeys).map((key) => deleteSecureItem(key)));
}
