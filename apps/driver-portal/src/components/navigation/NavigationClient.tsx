"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Clock, MapPin, Navigation, Radio, Route } from "lucide-react";
import { PageSkeleton } from "@porterchain/ui/loading";
import DriverShell from "@/components/DriverShell";
import WithGoogleMaps from "@/components/maps/WithGoogleMaps";
import { DriverNavigationMap } from "@/components/navigation/DriverNavigationMap";
import { useDriverNavigation } from "@/hooks/useDriverNavigation";
import { hasDriverSession } from "@/lib/api";
import { isGoogleMapsConfigured } from "@/lib/env";
import { formatDistance, formatEta } from "@/lib/navigation";

export default function NavigationClient() {
  return (
    <Suspense
      fallback={
        <div className="p-6">
          <PageSkeleton rows={3} />
        </div>
      }
    >
      <WithGoogleMaps>
        <NavigationPageContent />
      </WithGoogleMaps>
    </Suspense>
  );
}

function NavigationPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order") || undefined;
  const { session, error, loading, deviceLocation, gps, refresh } = useDriverNavigation(orderId);
  const [showTraffic, setShowTraffic] = useState(false);
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [replayIndex, setReplayIndex] = useState<number | null>(null);

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  const replay = session?.replay ?? [];

  useEffect(() => {
    if (!replayPlaying || replay.length < 2) return;
    let idx = 0;
    setReplayIndex(0);
    const timer = setInterval(() => {
      idx += 1;
      if (idx >= replay.length) {
        setReplayPlaying(false);
        clearInterval(timer);
        return;
      }
      setReplayIndex(idx);
    }, 700);
    return () => clearInterval(timer);
  }, [replayPlaying, replay.length]);

  return (
    <DriverShell>
      <header className="border-b border-[var(--primary)]/8 pb-6">
        <p className="text-sm font-medium text-[var(--muted)]">Driver Navigation</p>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Live Route</h1>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Live GPS · remaining ETA · planned corridor · map display
        </p>
        {gps && !gps.enabled && (
          <p role="status" className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
            {gps.message}
          </p>
        )}
      </header>

      {!isGoogleMapsConfigured() && (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Set <code className="text-xs">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> to render maps.
          Routing data still loads from Porterchain API.
        </p>
      )}

      {loading && !session && (
        <div className="mt-6">
          <PageSkeleton rows={3} />
        </div>
      )}
      {error && <p className="mt-4 text-red-600">{error}</p>}

      {session?.idle && (
        <div className="mt-6 rounded-2xl border border-primary/10 bg-white p-8 text-center shadow-sm">
          <Navigation className="mx-auto h-10 w-10 text-muted" />
          <h2 className="mt-4 text-lg font-bold">No active job</h2>
          <p className="mt-2 text-sm text-muted">
            Start a shift and accept a job to see live route navigation, GPS, and ETA.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              href="/jobs"
              className="rounded-xl bg-secondary px-4 py-2 text-sm font-semibold text-white"
            >
              View jobs
            </Link>
            <Link
              href="/shift"
              className="rounded-xl border border-primary/15 px-4 py-2 text-sm font-semibold"
            >
              Go to shift
            </Link>
          </div>
        </div>
      )}

      {session && !session.idle && (
        <div className="mt-6 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-mono text-lg font-bold">{session.tracking_number}</p>
              <p className="text-sm text-[var(--muted)]">
                {String(session.delivery_status?.label ?? session.state)}
                {session.gps_source && (
                  <span className="ml-2 inline-flex items-center gap-1 text-emerald-700">
                    <Radio className="h-3 w-3" />
                    GPS: {session.gps_source}
                  </span>
                )}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <label className="flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs">
                <input
                  type="checkbox"
                  checked={showTraffic}
                  onChange={(e) => setShowTraffic(e.target.checked)}
                />
                Traffic
              </label>
              {replay.length > 1 && (
                <button
                  type="button"
                  className="rounded-xl border px-3 py-1.5 text-xs font-semibold"
                  onClick={() => setReplayPlaying((p) => !p)}
                >
                  {replayPlaying ? "Stop replay" : "Route replay"}
                </button>
              )}
              <button
                type="button"
                className="rounded-xl border px-3 py-1.5 text-xs font-semibold text-[var(--secondary)]"
                onClick={() => refresh()}
              >
                Refresh
              </button>
              <Link
                href={`/jobs/${session.order_id}`}
                className="rounded-xl bg-[var(--primary)] px-3 py-1.5 text-xs font-semibold text-white"
              >
                Delivery 360
              </Link>
            </div>
          </div>

          {isGoogleMapsConfigured() ? (
            <DriverNavigationMap
              session={session}
              deviceLocation={deviceLocation}
              showTraffic={showTraffic}
              replayIndex={replayIndex ?? undefined}
            />
          ) : (
            <div className="flex h-[440px] items-center justify-center rounded-2xl bg-white text-[var(--muted)]">
              Map preview unavailable
            </div>
          )}

          <div className="flex flex-wrap gap-4 text-xs text-[var(--muted)]">
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-5 bg-sky-500" /> Pickup route (OSRM)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-5 bg-violet-600" /> Delivery route (Valhalla)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-5 bg-slate-400" /> Route replay
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              icon={Clock}
              label="ETA (OSRM)"
              value={session.eta?.eta_label ?? formatEta(session.eta?.duration_seconds)}
              hint={formatDistance(session.eta?.distance_meters)}
            />
            <Metric
              icon={Route}
              label="Optimized route"
              value={
                session.optimized_route?.eta_label ??
                formatEta(session.optimized_route?.duration_seconds)
              }
              hint={formatDistance(session.optimized_route?.distance_meters)}
            />
            <Metric
              icon={Navigation}
              label="Pickup leg"
              value={
                session.pickup_route?.eta_label ?? formatEta(session.pickup_route?.duration_seconds)
              }
              hint={formatDistance(session.pickup_route?.distance_meters)}
            />
            <Metric
              icon={MapPin}
              label="Stops"
              value={String(session.stops?.length ?? 0)}
              hint={`${session.geofences?.length ?? 0} geofences`}
            />
          </div>

          <section className="rounded-2xl bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold">Stops</h2>
            <ul className="mt-3 space-y-2">
              {(session.stops ?? []).map((stop) => (
                <li
                  key={String(stop.stop_id)}
                  className="flex items-center justify-between rounded-xl bg-[var(--gray-bg)] px-3 py-2 text-sm"
                >
                  <span className="font-medium capitalize">{String(stop.stop_type)}</span>
                  <span className="text-[var(--muted)]">{String(stop.status)}</span>
                </li>
              ))}
            </ul>
          </section>

          {session.offline_maps?.future_ready && (
            <p className="rounded-xl border border-dashed border-[var(--primary)]/20 bg-white px-4 py-3 text-xs text-[var(--muted)]">
              {session.offline_maps.message}
            </p>
          )}

          {session.navigation_url && (
            <a
              href={session.navigation_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex text-sm font-semibold text-[var(--secondary)] hover:underline"
            >
              Open in Google Maps ↗
            </a>
          )}
        </div>
      )}
    </DriverShell>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <p className="mt-2 text-xl font-bold">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-[var(--muted)]">{hint}</p>}
    </div>
  );
}
