import { Platform } from "react-native";
import { fetchGpsStatus, pingLocation, setAvailability } from "./api";
import { locationPingMs } from "./config";
import { humanError } from "./errorCopy";
import { enqueueGpsPing } from "./offline";
import { readLocationConsent } from "./consent";
import { DRIVER_LOCATION_TASK } from "./locationTask";
import type { LocationState } from "./types";

/** Soft-offline if no successful ping for this long while on duty. */
const STALE_LOCATION_MS = 5 * 60_000;

let lastSuccessfulPingAt = 0;
/** Set when PorterChain has switched live GPS off for this driver. */
let gpsOffMessage: string | null = null;

export function gpsDisabledMessage(): string | null {
  return gpsOffMessage;
}

/** Ask the server whether live GPS is on; stops background updates when it is off. */
const policyListeners = new Set<() => void>();
/** Called when live GPS turns back on (e.g. the driver just agreed on the consent screen). */
export function onGpsPolicyEnabled(fn: () => void): () => void {
  policyListeners.add(fn);
  return () => policyListeners.delete(fn);
}

export async function refreshGpsPolicy(): Promise<boolean> {
  const wasOff = gpsOffMessage != null;
  try {
    const s = await fetchGpsStatus();
    gpsOffMessage = s.enabled ? null : s.message;
  } catch {
    /* keep the last known policy */
  }
  if (wasOff && gpsOffMessage == null) policyListeners.forEach((fn) => fn());
  if (gpsOffMessage) await stopBackgroundLocation();
  return gpsOffMessage == null;
}

function gpsOffState(): LocationState {
  return { kind: "idle", detail: gpsOffMessage ?? "Live location sharing is off" };
}
let softOfflineArmed = false;

export function idleLocation(): LocationState {
  return { kind: "idle", detail: "Location idle — on-duty pings go to PorterChain dispatch" };
}

function humanLocationDetail(err: unknown): string {
  const raw = err instanceof Error ? err.message : "location_unavailable";
  return humanError(raw);
}

function markLocationPingSuccess(at = Date.now()): void {
  lastSuccessfulPingAt = at;
  softOfflineArmed = false;
}

function isLocationStale(now = Date.now()): boolean {
  if (!lastSuccessfulPingAt) return false;
  return now - lastSuccessfulPingAt > STALE_LOCATION_MS;
}

async function loadLocation() {
  return import("expo-location");
}

/** Foreground ("While using") permission only. Never shows the "Always" prompt. */
export async function requestLocationAccess(): Promise<LocationState> {
  try {
    const Location = await loadLocation();
    const existing = await Location.getForegroundPermissionsAsync();
    let status = existing.status;
    if (status !== "granted" && existing.canAskAgain !== false) {
      status = (await Location.requestForegroundPermissionsAsync()).status;
    }
    if (status !== "granted") {
      return { kind: "denied", detail: "Location off — dispatch will not see this van" };
    }
    return { kind: "granted", detail: "Location on while the app is open" };
  } catch (err) {
    return { kind: "error", detail: humanLocationDetail(err) };
  }
}

/** Checks (never prompts) — safe to call on every ping. */
async function hasForegroundPermission(): Promise<boolean> {
  try {
    const Location = await loadLocation();
    return (await Location.getForegroundPermissionsAsync()).status === "granted";
  } catch {
    return false;
  }
}

/**
 * The "Always" prompt. Only called after the driver agreed on the consent screen
 * (see consent.ts); without consent, on-duty GPS stays foreground-only.
 */
async function requestBackgroundAccess(): Promise<boolean> {
  const consent = await readLocationConsent();
  if (!consent) return false;
  const Location = await loadLocation();
  const bg = await Location.getBackgroundPermissionsAsync();
  if (bg.status === "granted") return true;
  if (bg.canAskAgain === false) return false;
  return (await Location.requestBackgroundPermissionsAsync()).status === "granted";
}

/** Fresh fix, else a recent cached one. Null = permission is fine but there is no fix yet. */
export async function readPosition(Location: Awaited<ReturnType<typeof loadLocation>>): Promise<{
  coords: {
    latitude: number;
    longitude: number;
    accuracy: number | null;
    heading: number | null;
    speed: number | null;
  };
} | null> {
  try {
    return await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
  } catch {
    try {
      return await Location.getLastKnownPositionAsync({ maxAge: 5 * 60_000 });
    } catch {
      return null;
    }
  }
}

/** Permission is granted but no fix: say exactly what is missing instead of "Location is off". */
export async function noFixState(
  Location: Awaited<ReturnType<typeof loadLocation>>
): Promise<LocationState> {
  let servicesOn = true;
  try {
    servicesOn = await Location.hasServicesEnabledAsync();
  } catch {
    /* assume on */
  }
  if (!servicesOn) {
    return {
      kind: "denied",
      detail:
        "Location Services are off for this phone. Settings → Privacy & Security → Location Services.",
    };
  }
  return {
    kind: "searching",
    detail: "Finding GPS signal… dispatch will see you once the phone gets a fix.",
  };
}

export async function sendLocationPing(): Promise<LocationState> {
  if (gpsOffMessage) return gpsOffState();
  if (!(await hasForegroundPermission())) {
    return { kind: "denied", detail: "Location off — dispatch will not see this van" };
  }
  try {
    const Location = await loadLocation();
    const pos = await readPosition(Location);
    if (!pos) return await noFixState(Location);
    try {
      const res = (await pingLocation(
        pos.coords.latitude,
        pos.coords.longitude,
        pos.coords.accuracy,
        {
          heading: pos.coords.heading,
          speed_mps: pos.coords.speed,
        }
      )) as { gps_enabled?: boolean; message?: string } | null;
      if (res && res.gps_enabled === false) {
        gpsOffMessage = res.message ?? "Live location sharing is off";
        await stopBackgroundLocation();
        return gpsOffState();
      }
      markLocationPingSuccess();
      return { kind: "granted", detail: "Location ping sent to PorterChain dispatch" };
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

/** Signal soft-offline once when GPS goes stale while on duty. */
export async function maybeSoftOfflineOnStale(online: boolean): Promise<LocationState | null> {
  if (!online || softOfflineArmed || gpsOffMessage || !isLocationStale()) return null;
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
  if (!(await refreshGpsPolicy())) return gpsOffState();
  const access = await requestLocationAccess();
  if (access.kind !== "granted") return access;
  try {
    if (!(await requestBackgroundAccess())) {
      return {
        kind: "granted",
        detail: "Location shared only while the app is open (background location is off)",
      };
    }
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
      detail: "Background location active — PorterChain keeps the van on the map",
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
