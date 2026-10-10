"use client";

import { useEffect, useEffectEvent, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi, type GpsStatus } from "@/lib/api";
import { enqueueGpsPing } from "@/lib/offline-client";
import type { DriverNavigationSession } from "@/lib/navigation";

const POLL_MS = 10_000;
const LOCATION_POST_MS = 25_000;

export function useDriverNavigation(orderId?: string | null) {
  const qc = useQueryClient();
  const [deviceLocation, setDeviceLocation] = useState<{ lat: number; lng: number } | null>(null);
  const lastPost = useRef(0);

  const query = useQuery({
    queryKey: ["driver-navigation", orderId ?? null],
    queryFn: () => driverApi.navigationSession(orderId ?? undefined),
    refetchInterval: () =>
      typeof document !== "undefined" && document.visibilityState === "hidden" ? false : POLL_MS,
  });

  const refreshNav = () => {
    void qc.invalidateQueries({ queryKey: ["driver-navigation", orderId ?? null] });
  };
  const onSequence = useEffectEvent(() => {
    refreshNav();
  });

  useEffect(() => {
    window.addEventListener("pc:sequence-applied", onSequence);
    return () => window.removeEventListener("pc:sequence-applied", onSequence);
  }, []);

  // Live GPS can be switched off by PorterChain (global or per driver): then we never
  // read or send the device position, and tell the driver plainly.
  const [gps, setGps] = useState<GpsStatus | null>(null);
  useEffect(() => {
    driverApi
      .gpsStatus()
      .then(setGps)
      .catch(() => setGps({ enabled: true, message: "" }));
  }, []);

  useEffect(() => {
    if (!navigator.geolocation || !gps?.enabled) return;
    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setDeviceLocation(loc);
        const now = Date.now();
        if (now - lastPost.current > LOCATION_POST_MS) {
          lastPost.current = now;
          const ping = {
            lat: loc.lat,
            lng: loc.lng,
            accuracy_m: pos.coords.accuracy,
            heading: pos.coords.heading ?? undefined,
            speed_mps: pos.coords.speed ?? undefined,
            recorded_at: new Date(pos.timestamp).toISOString(),
          };
          if (!navigator.onLine) {
            enqueueGpsPing(ping);
            return;
          }
          driverApi.postLocation(ping).catch(() => enqueueGpsPing(ping));
        }
      },
      () => undefined,
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
    );
    return () => navigator.geolocation.clearWatch(watchId);
  }, [gps?.enabled]);

  return {
    session: query.data ?? null,
    error: query.error instanceof Error ? query.error.message : "",
    loading: query.isLoading && !query.data,
    deviceLocation,
    gps,
    acceptGps: () => driverApi.gpsConsent(true).then(setGps),
    refresh: refreshNav,
  };
}
