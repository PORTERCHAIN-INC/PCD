import { useCallback, useEffect, useRef, useState } from "react";
import { humanCustomerError } from "../errors";
import { isOfflineError } from "../format";

/**
 * Load-once + pull-to-refresh state for a remote resource. Keeps the last good
 * data on screen when a refresh fails (stale-while-error) and distinguishes
 * "offline" from other errors so screens can show the right banner.
 */
export function useRemote<T>(load: () => Promise<T>, initial: T | null = null) {
  const [data, setData] = useState<T | null>(initial);
  const [loading, setLoading] = useState(initial == null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const loader = useRef(load);
  loader.current = load;

  const run = useCallback(async (mode: "initial" | "refresh") => {
    if (mode === "refresh") setRefreshing(true);
    try {
      const next = await loader.current();
      setData(next);
      setError(null);
      setOffline(false);
    } catch (err) {
      const raw = err instanceof Error ? err.message : "request_failed";
      setOffline(isOfflineError(raw));
      setError(humanCustomerError(raw));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void run("initial");
  }, [run]);

  const refresh = useCallback(() => run("refresh"), [run]);
  return { data, setData, loading, refreshing, error, offline, refresh };
}
