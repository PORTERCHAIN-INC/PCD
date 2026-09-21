import { Platform } from "react-native";
import { pingLocation, setAvailability } from "./api";
import { locationPingMs } from "./config";
import { humanFieldCopy } from "./fieldCopy";
import { enqueueGpsPing } from "./offline";
import { DRIVER_LOCATION_TASK } from "./locationTask";
import type { LocationState } from "./types";

/** Soft-offline if no successful ping for this long while on duty. */
export const STALE_LOCATION_MS = 5 * 60_000;

let lastSuccessfulPingAt = 0;
let softOfflineArmed = false;

export function idleLocation(): LocationState {
  return { kind: "idle", detail: "Location idle — on-duty pings go to Fleetbase" };
}

function humanLocationDetail(err: unknown): string {
  const raw = err instanceof Error ? err.message : "location_unavailable";
  return humanFieldCopy(raw) || raw;
}

export function markLocationPingSuccess(at = Date.now()): void {
  lastSuccessfulPingAt = at;
  softOfflineArmed = false;
}

export function isLocationStale(now = Date.now()): boolean {
  if (!lastSuccessfulPingAt) return false;
  return now - lastSuccessfulPingAt > STALE_LOCATION_MS;
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
      detail: humanLocationDetail(err),
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
      markLocationPingSuccess();
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
      detail: humanLocationDetail(err) || "location_ping_failed",
    };
  }
}

/** Signal soft-offline once when GPS goes stale while on duty (Fleetbase remains SoT). */
export async function maybeSoftOfflineOnStale(online: boolean): Promise<LocationState | null> {
  if (!online || softOfflineArmed || !isLocationStale()) return null;
  softOfflineArmed = true;
  try {
    await setAvailability("offline");
    return {
      kind: "error",
      detail: "GPS stale — soft offline signaled to dispatch",
    };
  } catch {
    softOfflineArmed = false;
    return null;
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
    markLocationPingSuccess();
    return {
      kind: "granted",
      detail: "Background location active — Fleetbase keeps the van on the map",
    };
  } catch (err) {
    return {
      kind: "error",
      detail: humanLocationDetail(err) || "background_location_failed",
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
    if (!cancelled && shouldPing()) {
      const soft = await maybeSoftOfflineOnStale(true);
      if (soft && !cancelled) onState(soft);
    }
  };
  void tick();
  const timer = setInterval(() => void tick(), locationPingMs);
  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}
