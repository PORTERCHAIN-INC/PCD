import type { MobileSession } from "../types";
import {
  clearSecuritySession,
  deleteSecureValue,
  getSecureValue,
  securityKeys,
  setSecureValue,
} from "../storage/secure-session";

export async function loadPersistedSession(): Promise<
  Partial<MobileSession> & { biometricEnabled: boolean; pinEnabled: boolean }
> {
  const [accessToken, refreshToken, driverId, customerId, biometric, pin, expiresAt] =
    await Promise.all([
      getSecureValue(securityKeys.accessToken),
      getSecureValue(securityKeys.refreshToken),
      getSecureValue(securityKeys.driverId),
      getSecureValue(securityKeys.customerId),
      getSecureValue(securityKeys.biometricEnabled),
      getSecureValue(securityKeys.pinEnabled),
      getSecureValue(securityKeys.sessionExpiresAt),
    ]);

  return {
    accessToken: accessToken ?? undefined,
    refreshToken: refreshToken ?? undefined,
    userId: driverId ?? customerId ?? "",
    biometricEnabled: biometric === "1",
    pinEnabled: pin === "1",
    expiresAt: expiresAt,
  };
}

export async function persistSession(session: MobileSession, appKind: "customer" | "driver") {
  const writes = [setSecureValue(securityKeys.accessToken, session.accessToken)];
  if (session.refreshToken)
    writes.push(setSecureValue(securityKeys.refreshToken, session.refreshToken));
  if (appKind === "driver") writes.push(setSecureValue(securityKeys.driverId, session.userId));
  if (appKind === "customer") writes.push(setSecureValue(securityKeys.customerId, session.userId));
  if (session.expiresAt)
    writes.push(setSecureValue(securityKeys.sessionExpiresAt, session.expiresAt));
  await Promise.all(writes);
  await touchLastActive();
}

export async function clearPersistedSession() {
  await clearSecuritySession();
}

export async function touchLastActive() {
  await setSecureValue(securityKeys.lastActiveAt, new Date().toISOString());
}

export async function getLastActiveAt() {
  return getSecureValue(securityKeys.lastActiveAt);
}

export async function isSessionExpired(timeoutMinutes: number) {
  const lastActive = await getLastActiveAt();
  if (!lastActive) return false;
  const elapsed = Date.now() - new Date(lastActive).getTime();
  return elapsed > timeoutMinutes * 60_000;
}

export async function setBiometricEnabled(enabled: boolean) {
  if (enabled) await setSecureValue(securityKeys.biometricEnabled, "1");
  else await deleteSecureValue(securityKeys.biometricEnabled);
}

export async function setPinEnabled(enabled: boolean) {
  if (enabled) await setSecureValue(securityKeys.pinEnabled, "1");
  else await deleteSecureValue(securityKeys.pinEnabled);
}
