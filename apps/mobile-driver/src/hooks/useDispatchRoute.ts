/**
 * Today's committed route (OR-Tools plan from dispatch) with the smart bits on top:
 * next-best stop, live distance + ETA countdown from on-device GPS, geofence auto-arrive,
 * and offline-first check-ins (queued with a client_id; the server replays them once).
 * No paid APIs: ETA is distance on the road network estimate from the phone's own GPS.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import { dispatchCheckin, fetchDispatchRoute } from "../api";
import type { CheckinEvent, DispatchRoute, DispatchStop } from "../dispatchRoute";
import { haptic } from "../haptics";
import { newClientId, runOnlineOrQueue } from "../offline";
import { distanceM, insideGeofence, type Fix } from "../smart/geo";
import { useLiveFix } from "../smart/useLiveFix";

const POLL_MS = 30_000;
/** City driving average incl. lights; road distance ≈ 1.35 × straight line. */
const CITY_MPS = 8.3;
const DETOUR = 1.35;

export function etaSecondsFrom(fix: Fix | null, stop: DispatchStop | null): number | null {
  if (!fix || !stop || stop.lat == null || stop.lng == null) return null;
  const d = distanceM(fix, { lat: stop.lat, lng: stop.lng }) * DETOUR;
  return Math.round(d / CITY_MPS);
}

/** Optimistic local status so the screen moves on instantly, even offline. */
export function applyLocalCheckin(
  route: DispatchRoute,
  keys: string[],
  event: CheckinEvent
): DispatchRoute {
  const key = keys.join(",");
  const stops = route.stops.map((s) => {
    if (s.keys.join(",") !== key) return s;
    const status: DispatchStop["status"] =
      event === "arrived" ? "arrived" : event === "failed" ? "failed" : "done";
    return { ...s, status };
  });
  const next = stops.findIndex((s) => s.status === "pending" || s.status === "arrived");
  return {
    ...route,
    stops,
    next_index: next < 0 ? null : next,
    done: stops.filter((s) => s.status === "done" || s.status === "failed").length,
  };
}

export function useDispatchRoute(onDuty: boolean) {
  const [route, setRoute] = useState<DispatchRoute | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [queued, setQueued] = useState(false);
  const [autoArrived, setAutoArrived] = useState<string | null>(null);
  const autoDone = useRef(new Set<string>());

  const load = useCallback(async () => {
    try {
      setRoute((await fetchDispatchRoute()).route);
    } catch {
      /* keep what we have (offline) */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void load();
    if (!onDuty) return;
    const t = setInterval(() => {
      if (AppState.currentState === "active") void load();
    }, POLL_MS);
    return () => clearInterval(t);
  }, [load, onDuty]);

  const stop = route && route.next_index != null ? (route.stops[route.next_index] ?? null) : null;
  const stopKey = stop?.keys.join(",") ?? null;
  const { fix, at: fixAt, saver } = useLiveFix(onDuty && Boolean(stopKey));

  const checkin = useCallback(
    async (
      event: CheckinEvent,
      extra: { note?: string; pod_photo?: string; short_reason?: string } = {}
    ) => {
      if (!route || !stop) return;
      const body = {
        keys: stop.keys,
        event,
        client_id: newClientId(),
        ...(fix ? { lat: fix.lat, lng: fix.lng, accuracy_m: fix.accuracy ?? undefined } : {}),
        ...extra,
      };
      const how = await runOnlineOrQueue("dispatch_checkin", body, async () => {
        const out = await dispatchCheckin(body);
        setRoute(out.route);
      });
      if (how === "queued") {
        setQueued(true);
        setRoute((r) => (r ? applyLocalCheckin(r, stop.keys, event) : r));
      } else setQueued(false);
      if (event === "delivered" || event === "picked_up") haptic.success();
    },
    [fix, route, stop]
  );

  // Geofence auto-arrive: inside 100 m, slow, good fix → "Arrived" once per stop.
  useEffect(() => {
    if (!stop || !fix || stop.status !== "pending" || stop.lat == null || stop.lng == null) return;
    const key = stop.keys.join(",");
    if (autoDone.current.has(key)) return;
    if (!insideGeofence(fix, { lat: stop.lat, lng: stop.lng })) return;
    autoDone.current.add(key);
    haptic.warn();
    setAutoArrived(key);
    void checkin("arrived", { note: "auto_arrive_geofence" }).catch(() =>
      autoDone.current.delete(key)
    );
  }, [checkin, fix, stop]);

  const distance =
    stop && fix && stop.lat != null && stop.lng != null
      ? distanceM(fix, { lat: stop.lat, lng: stop.lng })
      : null;
  const etaS = etaSecondsFrom(fix, stop);

  return {
    route,
    loaded,
    stop,
    fix,
    fixAt,
    saver,
    distance,
    /** Absolute ms when we expect to arrive (re-anchored on every GPS fix). */
    etaAt: etaS != null ? fixAt + etaS * 1000 : null,
    queued,
    autoArrived: autoArrived != null && autoArrived === stopKey,
    reload: load,
    checkin,
  };
}

export type RouteState = ReturnType<typeof useDispatchRoute>;
