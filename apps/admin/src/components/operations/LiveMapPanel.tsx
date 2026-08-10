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
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

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
}: {
  tick: number;
  onOpenOrder?: (orderId: string) => void;
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

  if (loading && !data) return <Spinner label="Loading live map…" />;

  return (
    <div className="space-y-3">
      {data && data.drivers_source !== "fleetbase" && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          Driver positions unavailable — Fleetbase bridge offline. Order stops still shown from the
          Porterchain mirror.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <label className="flex items-center gap-1.5 text-muted">
          <input
            type="checkbox"
            checked={showDensity}
            onChange={(e) => setShowDensity(e.target.checked)}
          />
          Order density
        </label>
        <label className="flex items-center gap-1.5 text-muted">
          <input
            type="checkbox"
            checked={showZones}
            onChange={(e) => setShowZones(e.target.checked)}
          />
          Zones
          {data?.zones_source && data.zones_source !== "fleetbase" && (
            <span className="text-amber-700">(none from Fleetbase)</span>
          )}
        </label>
      </div>
      <div className="relative overflow-hidden rounded-2xl border border-primary/10">
        <Map
          defaultCenter={GTA_CENTER}
          defaultZoom={11}
          gestureHandling="greedy"
          mapId="admin-ops-live-map"
          style={{ height: 560 }}
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

          {drivers.map((d) => (
            <AdvancedMarker
              key={d.id}
              position={{ lat: d.lat, lng: d.lng }}
              title={`${d.name}${d.online ? "" : " (offline)"}`}
            >
              <div
                className={
                  d.online
                    ? "h-3.5 w-3.5 rounded-full border-2 border-white bg-blue-600 shadow"
                    : "h-3.5 w-3.5 rounded-full border-2 border-white bg-gray-400 shadow opacity-70"
                }
              />
            </AdvancedMarker>
          ))}

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

      <div className="flex flex-wrap items-center gap-4 px-1 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-600" /> Driver (online)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-400" /> Driver (offline)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-green-600 px-1.5 text-[9px] font-bold text-white">
            P
          </span>{" "}
          Pickup
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-red-600 px-1.5 text-[9px] font-bold text-white">D</span>{" "}
          Delivery
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-500" /> Density / waypoint
        </span>
        <span className="ml-auto">
          {orders.length} active orders · {drivers.length} drivers · {zones.length} zones · click a
          stop for its route
        </span>
      </div>
    </div>
  );
}

export function LiveMapPanel({
  tick,
  onOpenOrder,
}: {
  tick: number;
  onOpenOrder?: (orderId: string) => void;
}) {
  if (!isGoogleMapsConfigured()) {
    return (
      <SectionCard title="Live map">
        <EmptyState
          title="Google Maps not configured"
          hint="Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to enable the live map."
        />
      </SectionCard>
    );
  }
  return (
    <GoogleMapsProvider>
      <div className="space-y-3">
        <p className="flex items-center gap-1.5 text-xs text-muted">
          <Truck className="h-3.5 w-3.5" />
          Driver positions + zones poll Fleetbase via the adapter — no SocketCluster in the browser.
          Density is computed from Porterchain order stops (circles; HeatmapLayer removed from Maps
          JS).
        </p>
        <LiveMapInner tick={tick} onOpenOrder={onOpenOrder} />
      </div>
    </GoogleMapsProvider>
  );
}
