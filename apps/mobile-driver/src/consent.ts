/**
 * Location consent (PIPEDA meaningful consent; Ontario ESA electronic monitoring policy).
 * The server is the source of truth: `gps-consent` + `monitoring-policy/ack` record the
 * driver's agreement against the policy version (2026-10). This file keeps a local copy so the
 * OS "Always" prompt is only shown after the driver agreed, and remembers when the server
 * hasn't heard yet (agreed while offline) so it is re-sent on the next open.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";

/** Bump when the in-app wording changes. The server policy version is tracked separately. */
export const CONSENT_VERSION = 2;
const KEY = "porterchain_driver_location_consent";

export type LocationConsent = {
  version: number;
  agreedAt: string;
  /** Monitoring policy version agreed to, e.g. "2026-10". */
  policyVersion?: string | null;
  /** False until the server has recorded the consent. */
  serverSynced?: boolean;
} | null;

export async function readLocationConsent(): Promise<LocationConsent> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const parsed = raw ? (JSON.parse(raw) as LocationConsent) : null;
    return parsed && parsed.version === CONSENT_VERSION ? parsed : null;
  } catch {
    return null;
  }
}

export async function saveLocationConsent(
  now = new Date(),
  extra: { policyVersion?: string | null; serverSynced?: boolean } = {}
): Promise<LocationConsent> {
  const value = {
    version: CONSENT_VERSION,
    agreedAt: now.toISOString(),
    policyVersion: extra.policyVersion ?? null,
    serverSynced: extra.serverSynced ?? false,
  };
  await AsyncStorage.setItem(KEY, JSON.stringify(value));
  return value;
}

export async function withdrawLocationConsent(): Promise<void> {
  await AsyncStorage.removeItem(KEY);
}
