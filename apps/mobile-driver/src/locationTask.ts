import * as TaskManager from "expo-task-manager";
import { enqueueGpsPing } from "./offline";
import { pingLocation } from "./api";

/** Must match startLocationUpdatesAsync task name in location.ts */
export const DRIVER_LOCATION_TASK = "porterchain-driver-location";

TaskManager.defineTask(DRIVER_LOCATION_TASK, async ({ data, error }) => {
  if (error) return;
  const locations = (
    data as {
      locations?: Array<{
        coords: {
          latitude: number;
          longitude: number;
          accuracy: number | null;
          heading: number | null;
          speed: number | null;
        };
        timestamp: number;
      }>;
    }
  )?.locations;
  const latest = locations?.[locations.length - 1];
  if (!latest) return;

  const lat = latest.coords.latitude;
  const lng = latest.coords.longitude;
  const accuracy_m = latest.coords.accuracy;
  const heading = latest.coords.heading;
  const speed_mps = latest.coords.speed;
  const recorded_at = new Date(latest.timestamp).toISOString();

  try {
    await pingLocation(lat, lng, accuracy_m, {
      heading,
      speed_mps,
      recorded_at,
    });
  } catch {
    await enqueueGpsPing({
      lat,
      lng,
      accuracy_m,
      heading,
      speed_mps,
      recorded_at,
    });
  }
});
