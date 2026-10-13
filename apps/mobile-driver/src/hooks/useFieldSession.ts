/**
 * Field session state: the handshake snapshot, duty + GPS, and the offline outbox counters.
 * Sync happens automatically on reconnect and on app foreground; "Sync now" is a backup.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import NetInfo from "@react-native-community/netinfo";
import { endShift, startShift } from "../api";
import { idleHandshake, runHandshake } from "../handshake";
import {
  requestLocationAccess,
  startBackgroundLocation,
  startLocationLoop,
  stopBackgroundLocation,
} from "../location";
import {
  flushOfflineQueues,
  pendingOfflineCount,
  queuedStopIds,
  readRejected,
  runOnlineOrQueue,
} from "../offline";
import { mergeOfflineHandshake } from "../fieldState";
import { getSessionSnapshot, subscribeSession } from "../session";
import type { Handshake } from "../types";
import { qk } from "../data/keys";
import { queryClient } from "../data/queryClient";

/** Last known snapshot from the encrypted cache: Today/Job/Me paint instantly on cold start. */
function cachedHandshake(): Handshake | null {
  const h = queryClient.getQueryData<Handshake>(qk.handshake);
  return h && h.api === "up" ? { ...h, error: null } : null;
}

const OFFLINE_POLL_MS = 30_000;
const ON_DUTY_POLL_MS = 30_000;

export function useFieldSession() {
  const [handshake, setHandshake] = useState<Handshake>(() => cachedHandshake() ?? idleHandshake());
  /** False until this launch has its own server copy (GPS/duty side effects wait for it). */
  const [fresh, setFresh] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(
    () => queryClient.getQueryState(qk.handshake)?.dataUpdatedAt ?? 0
  );
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(0);
  const [rejected, setRejected] = useState(0);
  const [syncingStopIds, setSyncingStopIds] = useState<string[]>([]);
  const [signedIn, setSignedIn] = useState(() => getSessionSnapshot().signedIn);
  const signedInRef = useRef(signedIn);
  signedInRef.current = signedIn;
  const locationRef = useRef(handshake.location);
  locationRef.current = handshake.location;

  useEffect(() => subscribeSession(() => setSignedIn(getSessionSnapshot().signedIn)), []);

  const refreshCounts = useCallback(async (serverFailed = 0) => {
    setPending(await pendingOfflineCount());
    setSyncingStopIds(await queuedStopIds());
    setRejected((await readRejected()).length + serverFailed);
  }, []);

  const apply = useCallback((next: Handshake) => {
    setHandshake((prev) => {
      const merged = mergeOfflineHandshake(prev, next, signedInRef.current);
      if (merged.api === "up") {
        queryClient.setQueryData(qk.handshake, merged);
        setUpdatedAt(Date.now());
        setFresh(true);
      }
      return merged;
    });
  }, []);

  /** Pull the server snapshot, push the outbox, and pull again if anything was sent. */
  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      apply(await runHandshake(locationRef.current));
      try {
        const flushed = await flushOfflineQueues();
        if (flushed.queued > 0 || flushed.gps_flushed > 0) {
          apply(await runHandshake(locationRef.current));
        }
        await refreshCounts(flushed.server_failed);
      } catch {
        await refreshCounts();
      }
    } finally {
      setBusy(false);
    }
  }, [apply, refreshCounts]);

  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  // Reliable sync: on reconnect and whenever the app comes back to the foreground.
  useEffect(() => {
    if (!signedIn) return;
    let wasConnected: boolean | null = null;
    const unsubNet = NetInfo.addEventListener((state) => {
      const connected = Boolean(state.isConnected && state.isInternetReachable !== false);
      if (connected && wasConnected === false) void refreshRef.current();
      wasConnected = connected;
    });
    const appSub = AppState.addEventListener("change", (next) => {
      if (next === "active") void refreshRef.current();
    });
    const timer = setInterval(() => void refreshCounts(), OFFLINE_POLL_MS);
    return () => {
      unsubNet();
      appSub.remove();
      clearInterval(timer);
    };
  }, [signedIn, refreshCounts]);

  // On duty with the app open: pull every 30 s so new jobs show up even where push can't
  // reach (iPhones until Firebase Messaging is in the build, Do Not Disturb, flaky FCM).
  useEffect(() => {
    if (!signedIn || !handshake.online) return;
    const timer = setInterval(() => {
      if (AppState.currentState === "active") void refreshRef.current();
    }, ON_DUTY_POLL_MS);
    return () => clearInterval(timer);
  }, [signedIn, handshake.online]);

  // GPS follows duty: on duty → pings + background updates; off duty → nothing.
  useEffect(() => {
    if (!fresh) return; // cached "on duty" isn't proof: wait for this launch's server copy
    if (!handshake.online) {
      void stopBackgroundLocation();
      return;
    }
    const setLocation = (location: Handshake["location"]) =>
      setHandshake((prev) => ({ ...prev, location }));
    void startBackgroundLocation().then(setLocation);
    return startLocationLoop(() => true, setLocation);
  }, [handshake.online, fresh]);

  const goOnDuty = useCallback(
    async (pretrip: Record<string, boolean>) => {
      const access = await requestLocationAccess();
      setHandshake((prev) => ({ ...prev, location: access }));
      await runOnlineOrQueue("shift_start", { route_id: handshake.routeId, pretrip }, () =>
        startShift(handshake.routeId, pretrip)
      );
      setHandshake((prev) => ({ ...prev, online: true }));
    },
    [handshake.routeId]
  );

  const goOffDuty = useCallback(async () => {
    await stopBackgroundLocation();
    await endShift();
    setHandshake((prev) => ({ ...prev, online: false }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setHandshake((prev) => ({ ...prev, error }));
  }, []);

  return {
    handshake,
    setHandshake,
    /** This launch has a server copy (false = painting from the cache). */
    fresh,
    updatedAt,
    busy,
    setBusy,
    pending,
    rejected,
    syncingStopIds,
    refresh,
    refreshCounts,
    goOnDuty,
    goOffDuty,
    setError,
  };
}

export type FieldSession = ReturnType<typeof useFieldSession>;
