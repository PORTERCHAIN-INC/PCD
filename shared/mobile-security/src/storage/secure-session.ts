import * as SecureStore from "expo-secure-store";

const prefix = "porterchain.secure.";

export const securityKeys = {
  accessToken: `${prefix}access_token`,
  refreshToken: `${prefix}refresh_token`,
  driverId: `${prefix}driver_id`,
  customerId: `${prefix}customer_id`,
  pinHash: `${prefix}pin_hash`,
  biometricEnabled: `${prefix}biometric_enabled`,
  pinEnabled: `${prefix}pin_enabled`,
  mmkvEncryptionKey: `${prefix}mmkv_key`,
  sessionExpiresAt: `${prefix}session_expires_at`,
  lastActiveAt: `${prefix}last_active_at`,
} as const;

export async function getSecureValue(key: string): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(key, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  } catch {
    return null;
  }
}

export async function setSecureValue(key: string, value: string): Promise<void> {
  await SecureStore.setItemAsync(key, value, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function deleteSecureValue(key: string): Promise<void> {
  await SecureStore.deleteItemAsync(key);
}

export async function clearSecuritySession(): Promise<void> {
  await Promise.all(Object.values(securityKeys).map((key) => deleteSecureValue(key)));
}
