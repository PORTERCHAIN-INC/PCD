"use client";

import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { trackOrder } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function TrackPage() {
  const searchParams = useSearchParams();
  const initial = searchParams.get("q") || "";
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [tracking, setTracking] = useState(initial);
  const [result, setResult] = useState<Awaited<ReturnType<typeof trackOrder>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onTrack(e?: React.FormEvent) {
    e?.preventDefault();
    if (!tracking || !isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const data = await trackOrder(token, tracking.trim(), orgId);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Not found");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!initial || !isSignedIn) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- auto-track from query param
    void onTrack();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial, isSignedIn]);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-primary">Track Shipment</h1>
      <form onSubmit={onTrack} className="flex gap-3">
        <input
          className="flex-1 rounded-xl border border-primary/15 px-3 py-2 text-sm"
          placeholder="Tracking number"
          value={tracking}
          onChange={(e) => setTracking(e.target.value)}
        />
        <Button type="submit" disabled={loading}>
          Track
        </Button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {result && (
        <div className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
          <div>
            <p className="font-mono text-lg font-bold">{result.order.tracking_number}</p>
            <p className="text-sm text-muted">
              {result.order.state} · Scheduled {formatDate(result.order.scheduled_at)}
            </p>
          </div>
          <div className="text-sm">
            <p>{result.order.pickup?.formatted}</p>
            <p className="text-muted">↓</p>
            <p>{result.order.dropoff?.formatted}</p>
          </div>
          <div>
            <h2 className="font-semibold">Timeline</h2>
            <ol className="mt-3 space-y-2">
              {result.timeline.map((ev, i) => (
                <li key={i} className="text-sm">
                  {String(ev.event_type)} {ev.to_state ? `(${String(ev.to_state)})` : ""}
                  <span className="ml-2 text-xs text-muted">{String(ev.occurred_at || "")}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
