/**
 * Optional device unlock (Face ID / fingerprint) before restoring a Clerk session.
 * Soft-fails open when the module or hardware is unavailable (simulators / web).
 */

export type DeviceUnlockResult =
  { ok: true; skipped: boolean; reason?: string } | { ok: false; reason: string };

export async function unlockWithDeviceAuth(): Promise<DeviceUnlockResult> {
  try {
    // Dynamic import so Expo Go / missing native module does not crash the bundle.
    const LocalAuthentication = await import("expo-local-authentication");
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    if (!hasHardware) {
      return { ok: true, skipped: true, reason: "no_hardware" };
    }
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    if (!enrolled) {
      return { ok: true, skipped: true, reason: "not_enrolled" };
    }
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: "Unlock Porterchain Driver",
      cancelLabel: "Cancel",
      disableDeviceFallback: false,
    });
    if (result.success) {
      return { ok: true, skipped: false };
    }
    return {
      ok: false,
      reason: result.error === "user_cancel" ? "unlock_cancelled" : "unlock_failed",
    };
  } catch {
    return { ok: true, skipped: true, reason: "module_unavailable" };
  }
}
