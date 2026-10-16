/**
 * Light haptic feedback. expo-haptics is loaded lazily so an older dev client
 * without the native module keeps working (it simply skips the buzz).
 */
type HapticsModule = typeof import("expo-haptics");

let mod: HapticsModule | null | undefined;

function load(): HapticsModule | null {
  if (mod !== undefined) return mod;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    mod = require("expo-haptics") as HapticsModule;
  } catch {
    mod = null;
  }
  return mod;
}

export const haptic = {
  tap() {
    void load()
      ?.selectionAsync()
      .catch(() => undefined);
  },
  success() {
    const h = load();
    void h?.notificationAsync(h.NotificationFeedbackType.Success).catch(() => undefined);
  },
  error() {
    const h = load();
    void h?.notificationAsync(h.NotificationFeedbackType.Error).catch(() => undefined);
  },
};
