"use client";

import { useMemo, useState } from "react";
import { Truck } from "lucide-react";
import { OsmMap, type MapPoint } from "@/components/maps/OsmMap";
import { MAP_COLORS } from "@/components/maps/mapColors";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";
import { Badge, Button, SectionCard } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";
import { gpsSourceLabel, isStaleGps } from "@/lib/telemetryLabels";
import { PageSkeleton } from "@porterchain/ui/loading";

const LIVE_GPS = new Set(["last_known", "mirror"]);

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
  const [showArea, setShowArea] = useState(false);
  const [trackDriver, setTrackDriver] = useState<string | null>(null);
  const { data: area } = useApiData((t) => ops.serviceArea(t), [showArea], {
    key: "ops-service-area",
    enabled: showArea,
  });
  const { data: track } = useApiData(
    (t) => ops.driverTrack(t, trackDriver ?? ""),
    [trackDriver, tick],
    {
      key: "ops-driver-track",
      enabled: !!trackDriver,
    }
  );
  const { data: geometry } = useApiData((t) => ops.routeGeometry(t, selected ?? ""), [selected], {
    key: "ops-route-geometry",
    enabled: !!selected,
  });

  const orders = useMemo(() => data?.orders ?? [], [data]);
  const drivers = useMemo(() => data?.drivers ?? [], [data]);
  const selectedOrder = orders.find((o) => o.id === selected) ?? null;

  const points = useMemo<MapPoint[]>(() => {
    const out: MapPoint[] = [];
    orders.forEach((o) =>
      o.stops.forEach((s, i) =>
        out.push({
          id: o.id,
          lat: s.lat,
          lng: s.lng,
          title: `${o.tracking_number} ${s.kind} ${i}`,
          color:
            s.kind === "pickup"
              ? MAP_COLORS.pickup
              : s.kind === "dropoff"
                ? MAP_COLORS.drop
                : MAP_COLORS.via,
          size: o.id === selected ? 8 : 6,
        })
      )
    );
    drivers.forEach((d) =>
      out.push({
        id: `driver:${d.id}`,
        lat: d.lat,
        lng: d.lng,
        title: d.name,
        color: isStaleGps(d.recorded_at)
          ? MAP_COLORS.stale
          : d.online
            ? MAP_COLORS.driver
            : MAP_COLORS.offline,
        size: 7,
      })
    );
    return out;
  }, [orders, drivers, selected]);

  const lines = useMemo(() => {
    const out: Array<{
      id: string;
      path: [number, number][];
      color: string;
      width?: number;
      opacity?: number;
    }> = [];
    if ((geometry?.path?.length ?? 0) > 1)
      out.push({ id: "route", path: geometry!.path, color: MAP_COLORS.route });
    // Driver trail snapped to roads (Valhalla map-matching), drawn under the route.
    if ((track?.path?.length ?? 0) > 1)
      out.push({
        id: "track",
        path: track!.path,
        color: MAP_COLORS.driver,
        width: 4,
        opacity: 0.7,
      });
    return out;
  }, [geometry, track]);
  const areas = useMemo(() => {
    const out = showZones
      ? (data?.zones ?? []).map((z) => ({
          id: String(z.id ?? z.name),
          path: z.path,
          color: z.color || MAP_COLORS.zone,
        }))
      : [];
    if (showArea)
      (area?.areas ?? []).forEach((a, i) =>
        out.push({ id: `area-${a.minutes}-${i}`, path: a.path, color: MAP_COLORS.zone })
      );
    return out;
  }, [data, showZones, showArea, area]);
  const heat = useMemo(() => (showDensity ? (data?.density ?? []) : []), [data, showDensity]);

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
        <label className="flex items-center gap-1.5 text-muted">
          <input
            type="checkbox"
            checked={showArea}
            onChange={(e) => setShowArea(e.target.checked)}
          />
          Service area (30/60/90 min)
        </label>
        {trackDriver && (
          <button className="text-muted underline" onClick={() => setTrackDriver(null)}>
            Hide trail{track ? ` (${track.source === "raw" ? "raw GPS" : "road-matched"})` : ""}
          </button>
        )}
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
        <OsmMap
          label="Live map of orders and drivers"
          points={points}
          lines={lines}
          areas={areas}
          heat={heat}
          onPointClick={(id) =>
            id.startsWith("driver:") ? setTrackDriver(id.slice(7)) : setSelected(id)
          }
        />

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
              {geometry?.source === "valhalla" ? "Road route (Valhalla)" : "Direct line"} ·
              OpenStreetMap
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
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ background: MAP_COLORS.driver }}
          />{" "}
          Driver
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ background: MAP_COLORS.offline }}
          />{" "}
          Offline
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ background: MAP_COLORS.stale }}
          />{" "}
          GPS stale
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ background: MAP_COLORS.pickup }}
          />{" "}
          Pickup
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ background: MAP_COLORS.drop }}
          />{" "}
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
  const body = (
    <div className={embedded ? "flex min-h-0 flex-1 flex-col px-3 pb-3 pt-2" : "space-y-2"}>
      {!embedded && (
        <p className="flex items-center gap-1.5 text-xs text-muted">
          <Truck className="h-3.5 w-3.5" />
          Driver GPS and zones. Density is a nearby-driver weight, not live heat.
        </p>
      )}
      <LiveMapInner tick={tick} onOpenOrder={onOpenOrder} embedded={embedded} />
    </div>
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
