import * as Location from "expo-location";
import type { DriverApi } from "@porterchain/mobile-api";

let watchSub: Location.LocationSubscription | null = null;

export async function requestLocationPermission() {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === "granted";
}

type GpsHandlers = {
  onOfflinePing?: (ping: {
    lat: number;
    lng: number;
    accuracy_m?: number;
    heading?: number;
    speed_mps?: number;
  }) => void;
  onError?: (error: Error) => void;
};

export async function startGpsTracking(api: DriverApi, handlers?: GpsHandlers) {
  const granted = await requestLocationPermission();
  if (!granted) return;

  watchSub?.remove();
  watchSub = await Location.watchPositionAsync(
    {
      accuracy: Location.Accuracy.High,
      distanceInterval: 25,
      timeInterval: 15000,
    },
    (pos) => {
      const ping = {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        accuracy_m: pos.coords.accuracy ?? undefined,
        heading: pos.coords.heading ?? undefined,
        speed_mps: pos.coords.speed ?? undefined,
      };

      void api.postLocation(ping).catch(() => {
        handlers?.onOfflinePing?.(ping);
        handlers?.onError?.(new Error("location_queued_offline"));
      });
    }
  );
}

export function stopGpsTracking() {
  watchSub?.remove();
  watchSub = null;
}

export async function getCurrentCoords() {
  const granted = await requestLocationPermission();
  if (!granted) return null;
  const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
  return { lat: pos.coords.latitude, lng: pos.coords.longitude };
}
