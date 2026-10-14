/**
 * Foreground GPS watch (only while `active`; nothing stored on the phone).
 * Battery saver: in low-power mode or under 20 % it drops to balanced accuracy and wider spacing.
 */
import { useEffect, useState } from "react";
import type { Fix } from "./geo";
import { gpsMode } from "./route";
import { useBattery } from "./useBattery";
import { useSettings } from "../settings";

export function useLiveFix(active: boolean): { fix: Fix | null; at: number; saver: boolean } {
  const battery = useBattery();
  const { battery_saver_pct } = useSettings();
  const saver = gpsMode(battery.level, battery.lowPower, battery_saver_pct) === "saver";
  const [state, setState] = useState<{ fix: Fix | null; at: number }>({ fix: null, at: 0 });
  useEffect(() => {
    if (!active) return;
    let sub: { remove: () => void } | null = null;
    let cancelled = false;
    void (async () => {
      try {
        const Location = await import("expo-location");
        if ((await Location.getForegroundPermissionsAsync()).status !== "granted") return;
        const s = await Location.watchPositionAsync(
          saver
            ? { accuracy: Location.Accuracy.Balanced, distanceInterval: 40, timeInterval: 15_000 }
            : { accuracy: Location.Accuracy.High, distanceInterval: 15, timeInterval: 5_000 },
          (p) => {
            if (cancelled) return;
            setState({
              fix: {
                lat: p.coords.latitude,
                lng: p.coords.longitude,
                accuracy: p.coords.accuracy,
                speed: p.coords.speed,
              },
              at: Date.now(),
            });
          }
        );
        if (cancelled) s.remove();
        else sub = s;
      } catch {
        /* web / no GPS */
      }
    })();
    return () => {
      cancelled = true;
      sub?.remove();
    };
  }, [active, saver]);
  return { ...state, saver };
}
