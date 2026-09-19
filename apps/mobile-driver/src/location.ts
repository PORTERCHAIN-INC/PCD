import { Platform } from "react-native";
import { pingLocation } from "./api";
import { locationPingMs } from "./config";
import { enqueueGpsPing } from "./offline";
import { DRIVER_LOCATION_TASK } from "./locationTask";
import type { LocationState } from "./types";

export function idleLocation(): LocationState {
  return { kind: "idle", detail: "Location idle — on-duty pings go to Fleetbase" };
}

async function loadLocation() {
  return import("expo-location");
}

export async function requestLocationAccess(): Promise<LocationState> {
  try {
    const Location = await loadLocation();
    const existing = await Location.getForegroundPermissionsAsync();
    let status = existing.status;
    if (status !== "granted") {
      const asked = await Location.requestForegroundPermissionsAsync();
      status = asked.status;
    }
    if (status !== "granted") {
      return { kind: "denied", detail: "Location off — dispatch will not see this van" };
    }

    const bg = await Location.getBackgroundPermissionsAsync();
    if (bg.status !== "granted") {
      await Location.requestBackgroundPermissionsAsync();
    }

    return { kind: "granted", detail: "Location on — foreground + background → Fleetbase" };
  } catch (err) {
    return {
      kind: "error",
      detail: err instanceof Error ? err.message : "location_unavailable",
    };
  }
}

export async function sendLocationPing(): Promise<LocationState> {
  const access = await requestLocationAccess();
  if (access.kind !== "granted") return access;
  try {
    const Location = await loadLocation();
    const pos = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    try {
      await pingLocation(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy, {
        heading: pos.coords.heading,
        speed_mps: pos.coords.speed,
      });
      return { kind: "granted", detail: "Location ping sent to Fleetbase" };
    } catch {
      await enqueueGpsPing({
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        accuracy_m: pos.coords.accuracy,
        heading: pos.coords.heading,
        speed_mps: pos.coords.speed,
      });
      return { kind: "granted", detail: "Offline — GPS buffered for sync" };
    }
  } catch (err) {
    return {
      kind: "error",
      detail: err instanceof Error ? err.message : "location_ping_failed",
    };
  }
}

export async function startBackgroundLocation(): Promise<LocationState> {
  const access = await requestLocationAccess();
  if (access.kind !== "granted") return access;
  try {
    const Location = await loadLocation();
    const started = await Location.hasStartedLocationUpdatesAsync(DRIVER_LOCATION_TASK);
    if (!started) {
      await Location.startLocationUpdatesAsync(DRIVER_LOCATION_TASK, {
        accuracy: Location.Accuracy.Balanced,
        timeInterval: locationPingMs,
        distanceInterval: 40,
        deferredUpdatesInterval: locationPingMs,
        showsBackgroundLocationIndicator: true,
        pausesUpdatesAutomatically: false,
        foregroundService:
          Platform.OS === "android"
            ? {
                notificationTitle: "Porterchain on duty",
                notificationBody: "Sharing van location with dispatch",
                notificationColor: "#124835",
              }
            : undefined,
      });
    }
    return {
      kind: "granted",
      detail: "Background location active — Fleetbase keeps the van on the map",
    };
  } catch (err) {
    return {
      kind: "error",
      detail: err instanceof Error ? err.message : "background_location_failed",
    };
  }
}

export async function stopBackgroundLocation(): Promise<void> {
  try {
    const Location = await loadLocation();
    const started = await Location.hasStartedLocationUpdatesAsync(DRIVER_LOCATION_TASK);
    if (started) {
      await Location.stopLocationUpdatesAsync(DRIVER_LOCATION_TASK);
    }
  } catch {
    /* ignore */
  }
}

export function startLocationLoop(
  shouldPing: () => boolean,
  onState: (next: LocationState) => void
): () => void {
  let cancelled = false;
  const tick = async () => {
    if (cancelled || !shouldPing()) return;
    const next = await sendLocationPing();
    if (!cancelled) onState(next);
  };
  void tick();
  const timer = setInterval(() => void tick(), locationPingMs);
  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}
