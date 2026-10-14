/** SOS: always tries to attach where the driver is (last known fix, then a quick fresh one). */
import { sendEmergency } from "./api";

async function whereAmI(): Promise<{ lat: number; lng: number; accuracy_m: number | null } | null> {
  try {
    const Location = await import("expo-location");
    if ((await Location.getForegroundPermissionsAsync()).status !== "granted") return null;
    const p =
      (await Location.getLastKnownPositionAsync({ maxAge: 120_000 })) ??
      (await Promise.race([
        Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
        new Promise<null>((r) => setTimeout(() => r(null), 4_000)),
      ]));
    return p
      ? { lat: p.coords.latitude, lng: p.coords.longitude, accuracy_m: p.coords.accuracy }
      : null;
  } catch {
    return null;
  }
}

export async function sendSos(): Promise<void> {
  await sendEmergency("Driver SOS from mobile app", await whereAmI());
}
