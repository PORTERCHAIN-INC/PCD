/**
 * Location consent (PIPEDA meaningful consent / GDPR Art. 6-7 + 13). The OS "Always" prompt is
 * only shown after the driver has read the explainer and agreed. Bump CONSENT_VERSION when the
 * wording or retention changes so every driver sees it again.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";

export const CONSENT_VERSION = 1;
const KEY = "porterchain_driver_location_consent";

export type LocationConsent = { version: number; agreedAt: string } | null;

export async function readLocationConsent(): Promise<LocationConsent> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const parsed = raw ? (JSON.parse(raw) as LocationConsent) : null;
    return parsed && parsed.version === CONSENT_VERSION ? parsed : null;
  } catch {
    return null;
  }
}

export async function saveLocationConsent(now = new Date()): Promise<LocationConsent> {
  const value = { version: CONSENT_VERSION, agreedAt: now.toISOString() };
  await AsyncStorage.setItem(KEY, JSON.stringify(value));
  return value;
}

export async function withdrawLocationConsent(): Promise<void> {
  await AsyncStorage.removeItem(KEY);
}
