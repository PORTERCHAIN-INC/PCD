/** Battery level + low-power mode (expo-battery, free). Null on web / unsupported. */
import { useEffect, useState } from "react";

export function useBattery(): { level: number | null; lowPower: boolean } {
  const [s, set] = useState<{ level: number | null; lowPower: boolean }>({
    level: null,
    lowPower: false,
  });
  useEffect(() => {
    let subs: { remove: () => void }[] = [];
    let cancelled = false;
    void (async () => {
      try {
        const B = await import("expo-battery");
        const [level, lowPower] = await Promise.all([
          B.getBatteryLevelAsync(),
          B.isLowPowerModeEnabledAsync(),
        ]);
        if (cancelled) return;
        set({ level, lowPower });
        subs = [
          B.addBatteryLevelListener(({ batteryLevel }) =>
            set((x) => ({ ...x, level: batteryLevel }))
          ),
          B.addLowPowerModeListener(({ lowPowerMode }) =>
            set((x) => ({ ...x, lowPower: lowPowerMode }))
          ),
        ];
      } catch {
        /* unsupported */
      }
    })();
    return () => {
      cancelled = true;
      subs.forEach((x) => x.remove());
    };
  }, []);
  return s;
}
