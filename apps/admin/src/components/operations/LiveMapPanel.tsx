"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AdvancedMarker,
  Circle,
  Map,
  Polygon,
  Polyline,
  useMap,
  useMapsLibrary,
} from "@vis.gl/react-google-maps";
import { Truck } from "lucide-react";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import { isGoogleMapsConfigured } from "@/lib/maps";
import { useApiData } from "@/hooks/useApiData";
import { ops, type LiveMapOrder } from "@/lib/operations";
import { Badge, Button, EmptyState, SectionCard } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";
import { gpsAgeLabel, gpsSourceLabel, isStaleGps } from "@/lib/telemetryLabels";
import { PageSkeleton } from "@porterchain/ui/loading";

const LIVE_GPS = new Set(["last_known", "mirror"]);

const GTA_CENTER = { lat: 43.6532, lng: -79.3832 };

function FitBounds({ points }: { points: { lat: number; lng: number }[] }) {
  const map = useMap();
  const core = useMapsLibrary("core");

  useEffect(() => {
    if (!map || !core || points.length < 2) return;
    const bounds = new core.LatLngBounds();
    points.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, 64);
  }, [map, core, points]);

  return null;
}

function StopMarker({
  stop,
  orderId,
  onSelect,
}: {
  stop: LiveMapOrder["stops"][number];
  orderId: string;
  onSelect: (orderId: string) => void;
}) {
  return (
    <AdvancedMarker
      position={{ lat: stop.lat, lng: stop.lng }}
      title={stop.label}
      onClick={() => onSelect(orderId)}
    >
      <div
        className={
          stop.kind === "pickup"
            ? "cursor-pointer rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold text-white shadow"
            : stop.kind === "dropoff"
              ? "cursor-pointer rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white shadow"
              : "h-3 w-3 cursor-pointer rounded-full border-2 border-white bg-amber-500 shadow"
        }
      >
        {stop.kind === "pickup" ? "P" : stop.kind === "dropoff" ? "D" : null}
      </div>
    </AdvancedMarker>
  );
}

function LiveMapInner({
  tick,
  onOpenOrder,
  embedded = false,
}: {
  tick: number;
  onOpenOrder?: (orderId: string) => void;
  embedded?: boolean;
}) {
  const { data, loading } = useApiData((t) => ops.liveMap(t), [tick], { key: "ops-live-map" });
  const [selected, setSelected] = useState<string | null>(null);
  const [showDensity, setShowDensity] = useState(true);
  const [showZones, setShowZones] = useState(true);
  const { data: geometry } = useApiData((t) => ops.routeGeometry(t, selected ?? ""), [selected], {
    key: "ops-route-geometry",
    enabled: !!selected,
  });

  const orders = useMemo(() => data?.orders ?? [], [data]);
  const drivers = useMemo(() => data?.drivers ?? [], [data]);
  const density = useMemo(() => data?.density ?? [], [data]);
  const zones = useMemo(() => data?.zones ?? [], [data]);
  const selectedOrder = orders.find((o) => o.id === selected) ?? null;
  const maxWeight = Math.max(1, ...density.map((d) => d.weight));

  const fitPoints = useMemo(() => {
    const pts: { lat: number; lng: number }[] = [];
    orders.forEach((o) => o.stops.forEach((s) => pts.push({ lat: s.lat, lng: s.lng })));
    drivers.forEach((d) => pts.push({ lat: d.lat, lng: d.lng }));
    return pts;
  }, [orders, drivers]);

  const polylinePath = useMemo(
    () => (geometry?.path ?? []).map(([lat, lng]) => ({ lat, lng })),
    [geometry]
  );

  if (loading && !data) {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-2 py-2">
        <p className="sr-only" role="status">
          Loading live map
        </p>
        <PageSkeleton rows={2} />
        <div className="min-h-[22rem] flex-1 rounded-xl border border-primary/10 bg-primary/[0.03]" />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {data && !LIVE_GPS.has(data.drivers_source) && (
        <p className="shrink-0 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
          Driver GPS offline — showing order stops only.
        </p>
      )}
      <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        {data && LIVE_GPS.has(data.drivers_source) && (
          <span className="text-muted">{gpsSourceLabel(data.drivers_source)}</span>
        )}
        <label className="flex items-center gap-1.5 text-muted">
          <input
            type="checkbox"
            checked={showDensity}
            onChange={(e) => setShowDensity(e.target.checked)}
          />
          Density
          {data?.density_source === "h3"
            ? " (H3)"
            : data?.density_source === "grid"
              ? " (grid)"
              : ""}
        </label>
        <label className="flex items-center gap-1.5 text-muted">
          <input
            type="checkbox"
            checked={showZones}
            onChange={(e) => setShowZones(e.target.checked)}
          />
          Zones
          {data?.zones_source &&
            !LIVE_GPS.has(data.zones_source) &&
            data.zones_source !== "miss" && <span className="text-amber-700">(none)</span>}
        </label>
        <span className="ml-auto text-muted">
          {orders.length} orders · {drivers.length} drivers
        </span>
      </div>
      <div
        className={
          embedded
            ? "relative h-[min(52vh,32rem)] min-h-[22rem] w-full overflow-hidden rounded-xl border border-primary/10"
            : "relative h-[32rem] w-full overflow-hidden rounded-xl border border-primary/10"
        }
      >
        <Map
          defaultCenter={GTA_CENTER}
          defaultZoom={11}
          gestureHandling="greedy"
          mapId="admin-ops-live-map"
          style={{ width: "100%", height: "100%" }}
        >
          {fitPoints.length >= 2 && <FitBounds points={fitPoints} />}

          {showZones &&
            zones.map((z) => (
              <Polygon
                key={String(z.id ?? z.name)}
                paths={z.path.map(([lat, lng]) => ({ lat, lng }))}
                fillColor={z.color || "#2563eb"}
                fillOpacity={0.12}
                strokeColor={z.stroke_color || "#2563eb"}
                strokeWeight={2}
                strokeOpacity={0.7}
              />
            ))}

          {showDensity &&
            density.map((cell, i) => (
              <Circle
                key={`d-${i}`}
                center={{ lat: cell.lat, lng: cell.lng }}
                radius={180 + (cell.weight / maxWeight) * 420}
                fillColor="#f59e0b"
                fillOpacity={0.12 + (cell.weight / maxWeight) * 0.35}
                strokeColor="#d97706"
                strokeOpacity={0.35}
                strokeWeight={1}
              />
            ))}

          {orders.map((o) =>
            o.stops.map((s, i) => (
              <StopMarker key={`${o.id}-${i}`} stop={s} orderId={o.id} onSelect={setSelected} />
            ))
          )}

          {drivers.map((d) => {
            const stale = isStaleGps(d.recorded_at);
            const age = gpsAgeLabel(d.recorded_at);
            const title = [d.name, d.online ? null : "offline", age].filter(Boolean).join(" · ");
            return (
              <AdvancedMarker key={d.id} position={{ lat: d.lat, lng: d.lng }} title={title}>
                <div
                  className={
                    stale
                      ? "h-3.5 w-3.5 rounded-full border-2 border-white bg-amber-500 shadow opacity-80"
                      : d.online
                        ? "h-3.5 w-3.5 rounded-full border-2 border-white bg-blue-600 shadow"
                        : "h-3.5 w-3.5 rounded-full border-2 border-white bg-gray-400 shadow opacity-70"
                  }
                />
              </AdvancedMarker>
            );
          })}

          {polylinePath.length > 1 && (
            <Polyline
              path={polylinePath}
              strokeColor="#7c3aed"
              strokeWeight={4}
              strokeOpacity={0.85}
            />
          )}
        </Map>

        {selectedOrder && (
          <div className="absolute left-3 top-3 w-72 rounded-xl border border-primary/10 bg-white/95 p-3 shadow-lg backdrop-blur">
            <p className="flex items-center gap-2 font-mono text-xs font-semibold text-primary">
              {selectedOrder.tracking_number}
              <Badge tone="sky">{titleCase(selectedOrder.state)}</Badge>
            </p>
            <p className="mt-1 text-xs text-muted">
              {selectedOrder.driver ?? "Unassigned"} · {selectedOrder.stops.length} stops
              {geometry?.distance_meters != null &&
                ` · ${(geometry.distance_meters / 1000).toFixed(1)} km`}
              {geometry?.duration_seconds != null &&
                ` · ${Math.round(geometry.duration_seconds / 60)} min`}
            </p>
            <p className="mt-0.5 text-[11px] text-muted">
              {geometry?.source === "valhalla" ? "Road route (Valhalla)" : "Direct line"}
            </p>
            <div className="mt-2 flex gap-2">
              {onOpenOrder && (
                <Button
                  className="px-3 py-1.5 text-xs"
                  onClick={() => onOpenOrder(selectedOrder.id)}
                >
                  Open 360
                </Button>
              )}
              <Button
                variant="outline"
                className="px-3 py-1.5 text-xs"
                onClick={() => setSelected(null)}
              >
                Clear
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-3 px-1 pb-1 text-[11px] text-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-600" /> Online
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-400" /> Offline
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-500" /> GPS stale
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-green-600 px-1.5 text-[9px] font-bold text-white">
            P
          </span>
          Pickup
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-red-600 px-1.5 text-[9px] font-bold text-white">D</span>
          Drop
        </span>
        <span className="ml-auto hidden sm:inline">Click a stop for route</span>
      </div>
    </div>
  );
}

export function LiveMapPanel({
  tick,
  onOpenOrder,
  embedded = false,
}: {
  tick: number;
  onOpenOrder?: (orderId: string) => void;
  /** Fill desk pane height (Control Tower Desk). */
  embedded?: boolean;
}) {
  if (!isGoogleMapsConfigured()) {
    return (
      <SectionCard
        title="Live map"
        className={embedded ? "flex h-full min-h-0 flex-col" : undefined}
      >
        <EmptyState
          title="Google Maps not configured"
          hint="Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable the live map."
        />
      </SectionCard>
    );
  }

  const body = (
    <GoogleMapsProvider>
      <div className={embedded ? "flex min-h-0 flex-1 flex-col px-3 pb-3 pt-2" : "space-y-2"}>
        {!embedded && (
          <p className="flex items-center gap-1.5 text-xs text-muted">
            <Truck className="h-3.5 w-3.5" />
            Driver GPS and zones. Density is a nearby-driver weight, not live heat.
          </p>
        )}
        <LiveMapInner tick={tick} onOpenOrder={onOpenOrder} embedded={embedded} />
      </div>
    </GoogleMapsProvider>
  );

  if (!embedded) {
    return (
      <SectionCard title="Live map" icon={<Truck className="h-4 w-4 text-secondary" />}>
        {body}
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title="Live map"
      icon={<Truck className="h-4 w-4 text-secondary" />}
      action={<span className="text-xs text-muted">Driver GPS</span>}
      className="flex h-full min-h-0 flex-col"
    >
      {body}
    </SectionCard>
  );
}
