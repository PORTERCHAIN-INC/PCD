"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverJobsList, DriverJobsOptimizeResult } from "@/lib/jobs";
import { formatLastUpdated } from "@/lib/workspace";
import { optimizeEngineNote } from "@/lib/telemetryLabels";

const POLL_MS = 12_000;
const OPTIMIZE_POLL_MS = 1_000;
const OPTIMIZE_POLL_MAX = 45;

function formatDeltaMessage(result: DriverJobsOptimizeResult, applied: boolean): string {
  if (result.status === "error") {
    return result.message || "Could not update stop order";
  }
  const engineRaw = typeof result.metrics.engine === "string" ? result.metrics.engine : null;
  if (engineRaw === "haversine") {
    return "Stop order not updated — routing engine unavailable.";
  }
  const engine = optimizeEngineNote(engineRaw);
  const parts: string[] = [
    applied
      ? engine
        ? `Stop order applied (${engine})`
        : "Stop order applied"
      : engine
        ? `Preview ready (${engine})`
        : "Preview ready",
  ];
  const fuelDelta = result.metrics.fuel_delta_cents;
  const kmDelta = result.metrics.distance_delta_km;
  if (typeof fuelDelta === "number" && fuelDelta !== 0) {
    const dollars = (Math.abs(fuelDelta) / 100).toFixed(2);
    parts.push(fuelDelta > 0 ? `saves ~$${dollars} fuel` : `~$${dollars} more fuel estimate`);
  }
  if (typeof kmDelta === "number" && kmDelta !== 0) {
    parts.push(kmDelta > 0 ? `${kmDelta} km shorter` : `${Math.abs(kmDelta)} km longer`);
  } else if (
    typeof result.metrics.estimated_fuel_cents === "number" &&
    typeof fuelDelta !== "number"
  ) {
    parts.push(`est. fuel $${(result.metrics.estimated_fuel_cents / 100).toFixed(2)}`);
  }
  if (typeof result.metrics.after_distance_km === "number") {
    parts.push(`${result.metrics.after_distance_km} km proposed`);
  }
  return parts.join(" · ");
}

export function useDriverJobs() {
  const [data, setData] = useState<DriverJobsList | null>(null);
  const [history, setHistory] = useState<DriverJobsList["completed"]>([]);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeMessage, setOptimizeMessage] = useState("");
  const [preview, setPreview] = useState<DriverJobsOptimizeResult | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async (_silent = false) => {
    try {
      const [jobsResult, histResult] = await Promise.allSettled([
        driverApi.jobs(),
        driverApi.jobsHistory(),
      ]);
      if (!mounted.current) return;
      if (jobsResult.status === "fulfilled") {
        setData(jobsResult.value);
        setLastUpdated(new Date());
        setError("");
      } else {
        const reason = jobsResult.reason;
        setError(reason instanceof Error ? reason.message : "refresh_failed");
      }
      if (histResult.status === "fulfilled") {
        setHistory(histResult.value.history);
        setHistoryError("");
      } else {
        const reason = histResult.reason;
        setHistoryError(reason instanceof Error ? reason.message : "history_failed");
      }
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  const optimize = useCallback(async () => {
    setOptimizing(true);
    setOptimizeMessage("Building stop order preview…");
    setPreview(null);
    setError("");
    try {
      let result = await driverApi.optimizeJobs();
      const runId = result.run_id;
      if (result.status === "pending" && runId) {
        for (let i = 0; i < OPTIMIZE_POLL_MAX; i += 1) {
          await new Promise((r) => setTimeout(r, OPTIMIZE_POLL_MS));
          if (!mounted.current) return;
          result = await driverApi.optimizeRunStatus(runId);
          if (result.status !== "pending") break;
        }
      }
      if (!mounted.current) return;
      if (result.status === "pending") {
        setOptimizeMessage("Still building preview… refresh shortly.");
        return;
      }
      if (result.status === "error") {
        setOptimizeMessage(result.message || "Preview failed");
        setPreview(null);
        return;
      }
      setPreview(result);
      setOptimizeMessage(formatDeltaMessage(result, false));
    } catch (e) {
      if (mounted.current) {
        const msg = e instanceof Error ? e.message : "optimize_failed";
        setError(
          msg.includes("sequence_version_conflict") || msg.includes("Sequence conflict")
            ? "Stop order conflict — refresh and try again."
            : msg
        );
        setOptimizeMessage("");
        setPreview(null);
      }
    } finally {
      if (mounted.current) setOptimizing(false);
    }
  }, []);

  const acceptPreview = useCallback(async () => {
    if (!preview?.run_id) return;
    setOptimizing(true);
    setError("");
    try {
      const result = await driverApi.optimizeAccept(preview.run_id, preview.sequence_version);
      if (!mounted.current) return;
      setData(result.jobs);
      setPreview(null);
      setCanUndo(true);
      setLastUpdated(new Date());
      setOptimizeMessage(formatDeltaMessage(result, true));
      // Nav polyline follows applied sequence — force immediate refresh.
      try {
        window.dispatchEvent(new CustomEvent("pc:sequence-applied"));
      } catch {
        /* SSR / non-DOM */
      }
    } catch (e) {
      if (mounted.current) {
        const msg = e instanceof Error ? e.message : "accept_failed";
        setError(
          msg.includes("sequence_version_conflict") || msg.includes("Sequence conflict")
            ? "Stop order conflict — refresh and request a new preview."
            : msg
        );
      }
    } finally {
      if (mounted.current) setOptimizing(false);
    }
  }, [preview]);

  const discardPreview = useCallback(() => {
    setPreview(null);
    setOptimizeMessage("Kept current stop order.");
  }, []);

  const undoOptimize = useCallback(async () => {
    setOptimizing(true);
    setError("");
    try {
      const result = await driverApi.optimizeUndo();
      if (!mounted.current) return;
      if (result.error === "nothing_to_undo" || result.ok === false) {
        setOptimizeMessage(result.message || "Nothing to undo");
        setCanUndo(false);
        return;
      }
      setData(result.jobs);
      setCanUndo(false);
      setPreview(null);
      setLastUpdated(new Date());
      setOptimizeMessage(result.message || "Previous stop order restored.");
      try {
        window.dispatchEvent(new CustomEvent("pc:sequence-applied"));
      } catch {
        /* SSR / non-DOM */
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "undo_failed");
    } finally {
      if (mounted.current) setOptimizing(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh(true);
    }, POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(interval);
    };
  }, [refresh]);

  return {
    data,
    history,
    error,
    historyError,
    loading,
    optimizing,
    optimizeMessage,
    preview,
    canUndo,
    lastUpdated,
    lastUpdatedLabel: lastUpdated ? formatLastUpdated(lastUpdated) : null,
    refresh: () => refresh(true),
    optimize,
    acceptPreview,
    discardPreview,
    undoOptimize,
  };
}
