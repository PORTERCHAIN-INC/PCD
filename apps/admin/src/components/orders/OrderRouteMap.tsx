"use client";

import { useEffect, useMemo, useState } from "react";
import { Pause, Play } from "lucide-react";
import { OsmMap, type MapLine, type MapPoint } from "@/components/maps/OsmMap";
import { MAP_COLORS } from "@/components/maps/mapColors";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";

function RouteMapInner({ orderId }: { orderId: string }) {
  const { data } = useApiData((t) => ops.routeGeometry(t, orderId), [orderId], {
    key: "ops-route-geometry",
  });
  const { data: playback } = useApiData((t) => ops.playback(t, orderId), [orderId], {
    key: "ops-playback",
  });

  const trail = useMemo(
    () => (playback?.points ?? []).map((p) => [p.lat, p.lng] as [number, number]),
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

  const points = useMemo<MapPoint[]>(() => {
    const out: MapPoint[] = (data?.stops ?? []).map((s, i) => ({
      id: `stop-${i}`,
      lat: s.lat,
      lng: s.lng,
      title: s.label,
      color:
        s.kind === "pickup"
          ? MAP_COLORS.pickup
          : s.kind === "dropoff"
            ? MAP_COLORS.drop
            : MAP_COLORS.via,
    }));
    const tip = trail[cursor];
    if (tip) out.push({ id: "tip", lat: tip[0], lng: tip[1], color: MAP_COLORS.trail, size: 7 });
    return out;
  }, [data, trail, cursor]);
  const lines = useMemo<MapLine[]>(() => {
    const out: MapLine[] = [];
    if ((data?.path?.length ?? 0) > 1)
      out.push({ id: "route", path: data!.path, color: MAP_COLORS.route, opacity: 0.45 });
    const shown = trail.slice(0, Math.max(1, cursor + 1));
    if (shown.length > 1)
      out.push({ id: "trail", path: shown, color: MAP_COLORS.trail, width: 3, opacity: 0.95 });
    return out;
  }, [data, trail, cursor]);

  if (!data) {
    return <div className="h-52 animate-pulse rounded-xl bg-gray-bg" />;
  }

  return (
    <div className="space-y-2">
      <div className="relative overflow-hidden rounded-xl border border-primary/10">
        <OsmMap label="Order route map" points={points} lines={lines} className="h-52 w-full" />
        <span className="absolute bottom-2 right-2 rounded-md bg-white/90 px-2 py-0.5 text-[10px] text-muted shadow">
          {data.source === "valhalla" || data.source === "osrm"
            ? `Road route (${data.source})`
            : "Direct line (not a road ETA)"}
          {" · © OpenStreetMap"}
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
            {playback?.source ? ` · ${playback.source.replace(/_/g, " ")}` : ""}
          </span>
        </div>
      ) : (
        <p className="text-[11px] text-muted">
          {playback?.message ??
            "No position history yet. Playback appears after the driver app reports GPS."}
        </p>
      )}
    </div>
  );
}

export function OrderRouteMap({ orderId }: { orderId: string }) {
  return <RouteMapInner orderId={orderId} />;
}
