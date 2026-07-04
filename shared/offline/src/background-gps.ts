import * as Location from "expo-location";
import * as TaskManager from "expo-task-manager";
import type { createGpsBuffer } from "@porterchain/mobile-storage";

export const BACKGROUND_GPS_TASK = "porterchain-background-gps";

type GpsBufferRef = ReturnType<typeof createGpsBuffer>;

let gpsBufferRef: GpsBufferRef | null = null;

export function registerBackgroundGpsTask(getBuffer: () => GpsBufferRef) {
  gpsBufferRef = getBuffer();

  if (TaskManager.isTaskDefined(BACKGROUND_GPS_TASK)) return;

  TaskManager.defineTask(BACKGROUND_GPS_TASK, async ({ data, error }) => {
    if (error || !data) return;
    const buffer = gpsBufferRef ?? getBuffer();
    const locations = (data as { locations?: Location.LocationObject[] }).locations ?? [];
    for (const pos of locations) {
      buffer.enqueue({
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        accuracy_m: pos.coords.accuracy ?? undefined,
        heading: pos.coords.heading ?? undefined,
        speed_mps: pos.coords.speed ?? undefined,
      });
    }
  });
}

export async function startBackgroundGps() {
  const fg = await Location.requestForegroundPermissionsAsync();
  if (fg.status !== "granted") return false;
  const bg = await Location.requestBackgroundPermissionsAsync();
  if (bg.status !== "granted") return false;

  const started = await Location.hasStartedLocationUpdatesAsync(BACKGROUND_GPS_TASK);
  if (started) return true;

  await Location.startLocationUpdatesAsync(BACKGROUND_GPS_TASK, {
    accuracy: Location.Accuracy.High,
    distanceInterval: 80,
    timeInterval: 20000,
    showsBackgroundLocationIndicator: true,
    foregroundService: {
      notificationTitle: "Porterchain GPS",
      notificationBody: "Tracking route while on shift",
    },
  });
  return true;
}

export async function stopBackgroundGps() {
  const started = await Location.hasStartedLocationUpdatesAsync(BACKGROUND_GPS_TASK);
  if (started) await Location.stopLocationUpdatesAsync(BACKGROUND_GPS_TASK);
}
