"use client";

import { LiveTrackingView } from "@/components/tracking/LiveTrackingView";
import { TrackingDashboardPanel } from "@/components/tracking/TrackingDashboardPanel";
import Button from "@/components/ui/Button";
import WithGoogleMaps from "@/components/maps/WithGoogleMaps";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { useMerchantRealtime } from "@/hooks/useMerchantRealtime";
import { orderStateLabel } from "@/lib/catalog";
import MapsMissingBanner from "@/components/maps/MapsMissingBanner";
import {
  AmbiguousTrackingError,
  trackingApi,
  type LiveTracking,
  type TrackingChoice,
  type TrackingDashboard,
} from "@/lib/tracking";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

const POLL_MS = 10_000;

export default function TrackPageClient() {
  return (
    <Suspense fallback={<p className="text-muted">Loading track…</p>}>
      <WithGoogleMaps>
        <TrackPageInner />
      </WithGoogleMaps>
    </Suspense>
  );
}

function TrackPageInner() {
  const searchParams = useSearchParams();
  const initial = searchParams.get("q") || "";
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [query, setQuery] = useState(initial);
  const [live, setLive] = useState<LiveTracking | null>(null);
  const [dashboard, setDashboard] = useState<TrackingDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [choices, setChoices] = useState<TrackingChoice[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const ready = Boolean(isLoaded && isSignedIn && orgId);

  const refreshDashboard = useCallback(async () => {
    if (!isSignedIn || !orgId) return;
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
      if (!number.trim() || !isSignedIn || !orgId) return;
      if (!silent) setLoading(true);
      else setRefreshing(true);
      setError(null);
      setChoices([]);
      try {
        const token = await getApiToken();
        const data = await trackingApi.byTrackingNumber(token, number.trim(), orgId);
        setLive(data.live_tracking);
      } catch (err) {
        if (err instanceof AmbiguousTrackingError) {
          // One PO, several drops — ask which one instead of guessing.
          setChoices(err.choices);
          setError(err.message);
        } else {
          setError(
            err instanceof Error
              ? err.message
              : "No shipment matches that tracking number, order number, or PO."
          );
        }
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
    if (!ready) return;
    void refreshDashboard();
  }, [ready, refreshDashboard]);

  useEffect(() => {
    if (!ready || !initial) return;
    void trackNumber(initial);
  }, [initial, ready, trackNumber]);

  useEffect(() => {
    if (!ready || !live) return;
    const timer = setInterval(
      () => void trackNumber(query.trim() || live.tracking_number, true),
      POLL_MS
    );
    return () => clearInterval(timer);
  }, [live, query, ready, trackNumber]);

  useMerchantRealtime(ready, orgId, getApiToken, refresh);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    await trackNumber(query);
  }

  if (!isLoaded) return <p className="text-muted">Loading…</p>;
  if (!isSignedIn) return <p className="text-muted">Please sign in.</p>;
  if (!orgId) return <p className="text-muted">Loading company…</p>;

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-primary">Track</h1>
        <p className="text-sm text-muted">
          Look up a tracking number, an order number, or your customer&apos;s PO. Driver GPS from
          Fleetbase appears once dispatched (polled, not a map WebSocket).
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex gap-3">
        <input
          className="flex-1 rounded-xl border border-primary/15 px-3 py-2 text-sm"
          placeholder="Tracking number, order number, or PO"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Looking up…" : "Track"}
        </Button>
      </form>

      {error && (
        <p className={choices.length ? "text-sm text-muted" : "text-sm text-red-600"}>{error}</p>
      )}

      {choices.length > 0 && (
        <ul className="divide-y divide-primary/10 overflow-hidden rounded-2xl border border-primary/10">
          {choices.map((c) => (
            <li key={c.order_id}>
              <button
                type="button"
                className="flex w-full flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-3 text-left text-sm hover:bg-primary/5"
                onClick={() => {
                  setQuery(c.tracking_number);
                  void trackNumber(c.tracking_number);
                }}
              >
                <span className="font-mono text-primary">{c.tracking_number}</span>
                <span className="text-muted">{orderStateLabel(c.state)}</span>
                {c.dropoff ? <span className="text-muted">→ {c.dropoff}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      )}

      <MapsMissingBanner />

      {live && (
        <LiveTrackingView
          tracking={live}
          onRefresh={refresh}
          refreshing={refreshing}
          getApiToken={getApiToken}
          orgId={orgId}
        />
      )}

      {!live && dashboard && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-primary">Active deliveries</h2>
          <TrackingDashboardPanel dashboard={dashboard} />
        </section>
      )}
    </div>
  );
}
