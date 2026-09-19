import { useCallback, useEffect, useState } from "react";
import { endShift, startShift } from "../api";
import { idleHandshake, runHandshake } from "../handshake";
import {
  requestLocationAccess,
  startBackgroundLocation,
  startLocationLoop,
  stopBackgroundLocation,
} from "../location";
import { flushOfflineQueues, pendingOfflineCount, type FlushResult } from "../offline";
import type { Handshake, LocationState } from "../types";

const OFFLINE_POLL_MS = 30_000;

export function useFieldSession() {
  const [handshake, setHandshake] = useState<Handshake>(idleHandshake());
  const [busy, setBusy] = useState(false);
  const [location, setLocation] = useState<LocationState>(idleHandshake().location);
  const [offlinePending, setOfflinePending] = useState(0);
  const [offlineNote, setOfflineNote] = useState<string | null>(null);
  const [lastFlush, setLastFlush] = useState<FlushResult | null>(null);

  const refreshOfflineCount = useCallback(async () => {
    setOfflinePending(await pendingOfflineCount());
  }, []);

  const applyFlush = useCallback((flushed: FlushResult) => {
    setLastFlush(flushed);
    if (flushed.conflicts_resolved > 0) {
      setOfflineNote(
        `${flushed.conflicts_resolved} queued action${flushed.conflicts_resolved === 1 ? "" : "s"} skipped (already applied on server)`
      );
    } else if (flushed.failed > 0) {
      setOfflineNote(
        `${flushed.failed} offline action${flushed.failed === 1 ? "" : "s"} failed — retry from sync`
      );
    } else if (flushed.synced && (flushed.queued > 0 || flushed.gps_flushed > 0)) {
      setOfflineNote(null);
    }
  }, []);

  const refreshHandshake = useCallback(async () => {
    setBusy(true);
    try {
      setHandshake(await runHandshake(location));
      await refreshOfflineCount();
      try {
        const flushed = await flushOfflineQueues();
        applyFlush(flushed);
        if (flushed.queued > 0 || flushed.gps_flushed > 0) {
          setHandshake(await runHandshake(location));
        }
        await refreshOfflineCount();
      } catch {
        /* keep local queue */
      }
    } finally {
      setBusy(false);
    }
  }, [applyFlush, location, refreshOfflineCount]);

  useEffect(() => {
    void refreshHandshake();
  }, [refreshHandshake]);

  useEffect(() => {
    const timer = setInterval(() => {
      void refreshOfflineCount();
    }, OFFLINE_POLL_MS);
    return () => clearInterval(timer);
  }, [refreshOfflineCount]);

  useEffect(() => {
    if (!handshake.online) {
      void stopBackgroundLocation();
      return;
    }
    void startBackgroundLocation().then((next) => {
      setLocation(next);
      setHandshake((prev) => ({ ...prev, location: next }));
    });
    return startLocationLoop(
      () => handshake.online === true,
      (next) => {
        setLocation(next);
        setHandshake((prev) => ({ ...prev, location: next }));
      }
    );
  }, [handshake.online]);

  const goOnDuty = useCallback(async (routeId: string | null) => {
    const access = await requestLocationAccess();
    setLocation(access);
    await startShift(routeId);
    const bg = await startBackgroundLocation();
    setLocation(bg);
  }, []);

  const goOffDuty = useCallback(async () => {
    await stopBackgroundLocation();
    await endShift();
  }, []);

  return {
    handshake,
    setHandshake,
    busy,
    setBusy,
    location,
    setLocation,
    offlinePending,
    offlineNote,
    setOfflineNote,
    lastFlush,
    refreshHandshake,
    refreshOfflineCount,
    applyFlush,
    goOnDuty,
    goOffDuty,
  };
}
