"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverEarningsSnapshot, StatementRow } from "@/lib/earnings";

const POLL_MS = 15_000;

export function useDriverEarnings() {
  const [data, setData] = useState<DriverEarningsSnapshot | null>(null);
  const [statements, setStatements] = useState<StatementRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const mounted = useRef(true);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const [snap, stmts] = await Promise.all([
        driverApi.earningsSnapshot(),
        driverApi.earningsStatements(),
      ]);
      if (mounted.current) {
        setData(snap);
        setStatements(stmts.statements);
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "earnings_refresh_failed");
    } finally {
      if (mounted.current) {
        setLoading(false);
        setRefreshing(false);
      }
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

  return { data, statements, error, loading, refreshing, refresh: () => refresh(true) };
}
