"use client";

import { useEffect, useMemo, useState } from "react";
import { AdvancedMarker, Map, Polyline } from "@vis.gl/react-google-maps";
import { Pause, Play } from "lucide-react";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { isGoogleMapsConfigured } from "@/lib/maps";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";

const FALLBACK_CENTER = { lat: 43.6532, lng: -79.3832 };

function RouteMapInner({ orderId }: { orderId: string }) {
  const { data } = useApiData((t) => ops.routeGeometry(t, orderId), [orderId], {
    key: "ops-route-geometry",
  });
  const { data: playback } = useApiData((t) => ops.playback(t, orderId), [orderId], {
    key: "ops-playback",
  });

  const path = useMemo(() => (data?.path ?? []).map(([lat, lng]) => ({ lat, lng })), [data]);
  const trail = useMemo(
    () => (playback?.points ?? []).map((p) => ({ lat: p.lat, lng: p.lng })),
    [playback]
  );
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    setCursor(0);
    setPlaying(false);
  }, [orderId, trail.length]);

  useEffect(() => {
    if (!playing || trail.length < 2) return;
    const id = window.setInterval(() => {
      setCursor((c) => {
        if (c >= trail.length - 1) {
          setPlaying(false);
          return c;
        }
        return c + 1;
      });
    }, 400);
    return () => window.clearInterval(id);
  }, [playing, trail.length]);

  const center = trail[0] ?? path[0] ?? FALLBACK_CENTER;
  const visibleTrail = trail.slice(0, Math.max(1, cursor + 1));
  const tip = trail[cursor];

  if (!data) {
    return <div className="h-52 animate-pulse rounded-xl bg-gray-bg" />;
  }

  return (
    <div className="space-y-2">
      <div className="relative overflow-hidden rounded-xl border border-primary/10">
        <Map
          defaultCenter={center}
          defaultZoom={11}
          gestureHandling="greedy"
          disableDefaultUI
          mapId="admin-order-route"
          style={{ height: 208 }}
        >
          {data.stops.map((s, i) => (
            <AdvancedMarker key={i} position={{ lat: s.lat, lng: s.lng }} title={s.label}>
              <div
                className={
                  s.kind === "pickup"
                    ? "rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold text-white"
                    : s.kind === "dropoff"
                      ? "rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white"
                      : "h-3 w-3 rounded-full border-2 border-white bg-amber-500 shadow"
                }
              >
                {s.kind === "pickup" ? "P" : s.kind === "dropoff" ? "D" : null}
              </div>
            </AdvancedMarker>
          ))}
          {path.length > 1 && (
            <Polyline path={path} strokeColor="#7c3aed" strokeWeight={4} strokeOpacity={0.45} />
          )}
          {visibleTrail.length > 1 && (
            <Polyline
              path={visibleTrail}
              strokeColor="#0ea5e9"
              strokeWeight={3}
              strokeOpacity={0.95}
            />
          )}
          {tip && (
            <AdvancedMarker position={tip} title="Playback">
              <div className="h-3.5 w-3.5 rounded-full border-2 border-white bg-sky-500 shadow" />
            </AdvancedMarker>
          )}
        </Map>
        <span className="absolute bottom-2 right-2 rounded-md bg-white/90 px-2 py-0.5 text-[10px] text-muted shadow">
          {data.source === "valhalla" || data.source === "osrm"
            ? `Road route (${data.source})`
            : "Direct line (not a road ETA)"}
          {data.distance_meters != null && ` · ${(data.distance_meters / 1000).toFixed(1)} km`}
          {(data.source === "valhalla" || data.source === "osrm") &&
            data.duration_seconds != null &&
            ` · ${Math.round(data.duration_seconds / 60)} min`}
        </span>
      </div>

      {trail.length >= 2 ? (
        <div className="flex items-center gap-2 rounded-xl border border-primary/10 bg-gray-bg/40 px-3 py-2">
          <button
            type="button"
            className="rounded-lg border border-primary/15 bg-white p-1.5 text-primary"
            onClick={() => setPlaying((p) => !p)}
            title={playing ? "Pause" : "Play"}
          >
            {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          </button>
          <input
            type="range"
            min={0}
            max={trail.length - 1}
            value={cursor}
            onChange={(e) => {
              setPlaying(false);
              setCursor(Number(e.target.value));
            }}
            className="flex-1 accent-sky-600"
          />
          <span className="whitespace-nowrap text-[10px] text-muted">
            {cursor + 1}/{trail.length}
            {playback?.source ? ` · ${playback.source.replace("fleetbase_", "")}` : ""}
          </span>
        </div>
      ) : (
        <p className="text-[11px] text-muted">
          {playback?.message ??
            "No Fleetbase position history yet — playback appears after the driver app reports GPS."}
        </p>
      )}
    </div>
  );
}

export function OrderRouteMap({ orderId }: { orderId: string }) {
  if (!isGoogleMapsConfigured()) return null;
  return (
    <GoogleMapsProvider>
      <RouteMapInner orderId={orderId} />
    </GoogleMapsProvider>
  );
}
