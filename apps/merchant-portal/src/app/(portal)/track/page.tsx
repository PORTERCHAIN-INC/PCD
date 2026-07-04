"use client";

import { LiveTrackingView } from "@/components/tracking/LiveTrackingView";
import { TrackingDashboardPanel } from "@/components/tracking/TrackingDashboardPanel";
import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import { isGoogleMapsConfigured } from "@/lib/env";
import { trackingApi, type LiveTracking, type TrackingDashboard } from "@/lib/tracking";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const POLL_MS = 10_000;

export default function TrackPage() {
  const searchParams = useSearchParams();
  const initial = searchParams.get("q") || "";
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [query, setQuery] = useState(initial);
  const [live, setLive] = useState<LiveTracking | null>(null);
  const [dashboard, setDashboard] = useState<TrackingDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const refreshDashboard = useCallback(async () => {
    if (!isSignedIn) return;
    try {
      const token = await getApiToken();
      const data = await trackingApi.dashboard(token, orgId);
      setDashboard(data);
    } catch {
      /* dashboard optional */
    }
  }, [getApiToken, isSignedIn, orgId]);

  const trackNumber = useCallback(
    async (number: string, silent = false) => {
      if (!number.trim() || !isSignedIn) return;
      if (!silent) setLoading(true);
      else setRefreshing(true);
      setError(null);
      try {
        const token = await getApiToken();
        const data = await trackingApi.byTrackingNumber(token, number.trim(), orgId);
        setLive(data.live_tracking);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Not found");
        setLive(null);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [getApiToken, isSignedIn, orgId]
  );

  const refresh = useCallback(async () => {
    await Promise.all([
      refreshDashboard(),
      query.trim() ? trackNumber(query.trim(), true) : Promise.resolve(),
    ]);
  }, [query, refreshDashboard, trackNumber]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void refreshDashboard();
  }, [isLoaded, isSignedIn, refreshDashboard]);

  useEffect(() => {
    if (!initial || !isSignedIn) return;
    void trackNumber(initial);
  }, [initial, isSignedIn, trackNumber]);

  useEffect(() => {
    if (!isSignedIn || !live) return;
    const timer = setInterval(() => void trackNumber(query.trim() || live.tracking_number, true), POLL_MS);
    return () => clearInterval(timer);
  }, [isSignedIn, live, query, trackNumber]);

  useMerchantRealtime(isLoaded && isSignedIn, orgId, getApiToken, refresh);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    await trackNumber(query);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-primary">Live Tracking</h1>
        <p className="text-sm text-muted">
          Fleetbase GPS · OSRM ETA · Valhalla routes · Google Maps display only
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex gap-3">
        <input
          className="flex-1 rounded-xl border border-primary/15 px-3 py-2 text-sm"
          placeholder="Tracking number"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Tracking…" : "Track"}
        </Button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {!isGoogleMapsConfigured() && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          Configure NEXT_PUBLIC_GOOGLE_MAPS_API_KEY for map rendering.
        </p>
      )}

      {live && <LiveTrackingView tracking={live} onRefresh={refresh} refreshing={refreshing} />}

      {!live && dashboard && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-primary">Active deliveries</h2>
          <TrackingDashboardPanel dashboard={dashboard} />
        </section>
      )}
    </div>
  );
}
