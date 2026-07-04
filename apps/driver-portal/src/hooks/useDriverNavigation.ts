"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import { enqueueGpsPing } from "@/lib/offline-client";
import type { DriverNavigationSession } from "@/lib/navigation";

const POLL_MS = 10_000;
const LOCATION_POST_MS = 25_000;

export function useDriverNavigation(orderId?: string | null) {
  const [session, setSession] = useState<DriverNavigationSession | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deviceLocation, setDeviceLocation] = useState<{ lat: number; lng: number } | null>(null);
  const lastPost = useRef(0);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const data = await driverApi.navigationSession(orderId ?? undefined);
      if (mounted.current) {
        setSession(data);
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "navigation_failed");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(interval);
    };
  }, [refresh]);

  useEffect(() => {
    if (!navigator.geolocation) return;
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
  }, []);

  return { session, error, loading, deviceLocation, refresh };
}
