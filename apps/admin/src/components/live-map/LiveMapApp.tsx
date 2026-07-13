"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Boxes,
  Circle,
  Compass,
  Hexagon,
  Layers,
  MapPin,
  Pause,
  Play,
  Radio,
  RefreshCw,
  Ruler,
  Search,
  Square,
  Truck,
  Users,
  X,
  Zap,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useLiveMapData } from "@/hooks/useLiveMapData";
import {
  DEFAULT_LAYERS,
  liveMapApi,
  parseLiveMapEntityId,
  type LiveMapFilters,
  type MapLayers,
} from "@/lib/live-map";
import { money, relativeTime } from "@/lib/crmFormat";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import MapCanvas from "@/components/live-map/MapCanvas";

type MapMode = "roadmap" | "satellite" | "hybrid" | "terrain";
type LeftTab = "queue" | "drivers" | "vehicles" | "incidents" | "claims" | "support" | "tasks";

const LAYER_LABELS: Record<keyof MapLayers, string> = {
  drivers: "Drivers",
  vehicles: "Vehicles",
  orders: "Orders",
  warehouses: "Warehouses",
  merchants: "Merchants",
  customers: "Customers",
  geofences: "Geofences",
  traffic: "Traffic / Transit / Bike",
  heatMap: "Heat Map",
  routes: "Routes",
  labels: "Labels",
  cluster: "Cluster",
};

export default function LiveMapApp() {
  const { getApiToken } = useAdminAuth();
  const [filters, setFilters] = useState<LiveMapFilters>({});
  const { data, error, connected, refresh } = useLiveMapData(filters);

  const [layers, setLayers] = useState<MapLayers>(DEFAULT_LAYERS);
  const [mapMode, setMapMode] = useState<MapMode>("roadmap");
  const theme = "light" as const;
  const [heatMetric, setHeatMetric] = useState<
    "orders" | "pickups" | "deliveries" | "drivers" | "revenue"
  >("orders");
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(false);
  const [bottomOpen, setBottomOpen] = useState(true);
  const [layersOpen, setLayersOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [leftTab, setLeftTab] = useState<LeftTab>("queue");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<
    Array<{ type: string; id: string; label: string; subtitle?: string }>
  >([]);
  const [selected, setSelected] = useState<{ type: string; id: string } | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const mountedRef = useRef(true);
  const [measureActive, setMeasureActive] = useState(false);
  const [drawMode, setDrawMode] = useState<"none" | "rectangle" | "circle" | "polygon">("none");
  const [playbackDate, setPlaybackDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [playbackFrames, setPlaybackFrames] = useState<
    Array<{ lat: number; lng: number; driver_id: string }>
  >([]);
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const loadDetail = useCallback(
    async (type: string, id: string) => {
      const { entityType, entityId } = parseLiveMapEntityId(type, id);
      if (!mountedRef.current) return;
      setSelected({ type: entityType, id: entityId });
      setRightOpen(true);
      setDetail(null);
      setDetailError(null);
      setDetailLoading(true);
      try {
        const token = await getApiToken();
        const d = await liveMapApi.detail(token, entityType, entityId);
        if (!mountedRef.current) return;
        setDetail(d);
      } catch (err) {
        if (!mountedRef.current) return;
        setDetail(null);
        setDetailError(err instanceof Error ? err.message : "Failed to load detail");
      } finally {
        if (mountedRef.current) setDetailLoading(false);
      }
    },
    [getApiToken]
  );

  useEffect(() => {
    if (!search || search.length < 2) {
      setSearchResults([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      void (async () => {
        try {
          const token = await getApiToken();
          const results = await liveMapApi.search(token, search);
          if (!cancelled) setSearchResults(results);
        } catch {
          if (!cancelled) setSearchResults([]);
        }
      })();
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [search, getApiToken]);

  useEffect(() => {
    if (!playing || !playbackFrames.length) return;
    const iv = setInterval(() => {
      setPlaybackIndex((i) => (i + 1) % playbackFrames.length);
    }, 800);
    return () => clearInterval(iv);
  }, [playing, playbackFrames.length]);

  async function loadPlayback() {
    const token = await getApiToken();
    const res = await liveMapApi.playback(token, playbackDate);
    const frames = (res.frames as Array<{ lat: number; lng: number; driver_id: string }>) ?? [];
    if (!mountedRef.current) return;
    setPlaybackFrames(frames);
    setPlaybackIndex(0);
  }

  const cc = data?.command_center;
  const widgets = useMemo(
    () =>
      cc
        ? [
            { label: "Orders Today", value: cc.orders_today, icon: Boxes },
            { label: "Drivers Online", value: cc.drivers_online, icon: Users },
            { label: "Vehicles Active", value: cc.vehicles_active, icon: Truck },
            { label: "Waiting", value: cc.orders_waiting, icon: Zap },
            {
              label: "Late Orders",
              value: cc.late_orders,
              icon: AlertTriangle,
              alert: cc.late_orders > 0,
            },
            { label: "Delayed Drivers", value: cc.delayed_drivers, icon: Radio },
            { label: "Support", value: cc.support_tickets, icon: Users },
            { label: "Revenue Today", value: money(cc.revenue_today_cents), icon: Boxes },
          ]
        : [],
    [cc]
  );

  if (!data && !error) {
    return (
      <div className="flex h-[calc(100vh-3rem)] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <GoogleMapsProvider>
      <div className="relative flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-gray-bg">
        {/* Top toolbar */}
        <header className="z-30 flex shrink-0 flex-wrap items-center gap-2 border-b border-primary/10 bg-white px-3 py-2 shadow-sm">
          <div className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-secondary" />
            <h1 className="text-sm font-bold text-primary">Live Operations Map</h1>
            <Badge tone={connected ? "green" : "amber"}>{connected ? "Live" : "Polling"}</Badge>
          </div>

          <div className="relative min-w-[200px] flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Driver, vehicle, tracking, phone, address…"
              className="w-full rounded-xl border border-primary/10 bg-gray-bg py-2 pl-9 pr-3 text-sm outline-none focus:border-secondary"
              aria-label="Global search"
            />
            {searchResults.length > 0 && (
              <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-auto rounded-xl border border-primary/10 bg-white shadow-xl">
                {searchResults.map((r) => (
                  <button
                    key={`${r.type}-${r.id}`}
                    type="button"
                    className="flex w-full flex-col px-3 py-2 text-left text-sm hover:bg-gray-bg"
                    onClick={() => {
                      void loadDetail(r.type, r.id);
                      setSearch("");
                      setSearchResults([]);
                    }}
                  >
                    <span className="font-medium text-primary">{r.label}</span>
                    <span className="text-xs text-muted capitalize">
                      {r.type}
                      {r.subtitle ? ` · ${r.subtitle}` : ""}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1">
            <ToolbarBtn
              icon={Layers}
              label="Layers"
              active={layersOpen}
              onClick={() => setLayersOpen((v) => !v)}
            />
            <ToolbarBtn
              icon={FilterIcon}
              label="Filters"
              active={filtersOpen}
              onClick={() => setFiltersOpen((v) => !v)}
            />
            <select
              value={mapMode}
              onChange={(e) => setMapMode(e.target.value as MapMode)}
              className="rounded-lg border border-primary/10 bg-white px-2 py-1.5 text-xs"
              aria-label="Map type"
            >
              <option value="roadmap">Road</option>
              <option value="satellite">Satellite</option>
              <option value="hybrid">Hybrid</option>
              <option value="terrain">Terrain</option>
            </select>
            <ToolbarBtn
              icon={Ruler}
              label="Measure"
              active={measureActive}
              onClick={() => setMeasureActive((v) => !v)}
            />
            <ToolbarBtn
              icon={Square}
              label="Rect"
              active={drawMode === "rectangle"}
              onClick={() => setDrawMode(drawMode === "rectangle" ? "none" : "rectangle")}
            />
            <ToolbarBtn
              icon={Circle}
              label="Circle"
              active={drawMode === "circle"}
              onClick={() => setDrawMode(drawMode === "circle" ? "none" : "circle")}
            />
            <ToolbarBtn
              icon={Hexagon}
              label="Polygon"
              active={drawMode === "polygon"}
              onClick={() => setDrawMode(drawMode === "polygon" ? "none" : "polygon")}
            />
            <ToolbarBtn icon={RefreshCw} label="Refresh" onClick={() => void refresh()} />
          </div>
        </header>

        {/* Layers popover */}
        <AnimatePresence>
          {layersOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="absolute left-3 top-14 z-40 w-56 rounded-2xl border border-primary/10 bg-white p-3 shadow-xl"
            >
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                Layers
              </p>
              {(Object.keys(DEFAULT_LAYERS) as Array<keyof MapLayers>).map((key) => (
                <label key={key} className="flex cursor-pointer items-center gap-2 py-1 text-sm">
                  <input
                    type="checkbox"
                    checked={layers[key]}
                    onChange={(e) => setLayers((l) => ({ ...l, [key]: e.target.checked }))}
                    className="rounded border-primary/20 text-secondary"
                  />
                  {LAYER_LABELS[key]}
                </label>
              ))}
              {layers.heatMap && (
                <select
                  value={heatMetric}
                  onChange={(e) => setHeatMetric(e.target.value as typeof heatMetric)}
                  className="mt-2 w-full rounded-lg border border-primary/10 px-2 py-1 text-xs"
                >
                  <option value="orders">Order density</option>
                  <option value="pickups">Pickup density</option>
                  <option value="deliveries">Delivery density</option>
                  <option value="drivers">Driver density</option>
                  <option value="revenue">Revenue density</option>
                </select>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Filters popover */}
        <AnimatePresence>
          {filtersOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="absolute left-64 top-14 z-40 w-72 rounded-2xl border border-primary/10 bg-white p-4 shadow-xl"
            >
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
                Filters
              </p>
              <div className="space-y-2 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!filters.online_only}
                    onChange={(e) =>
                      setFilters((f) => ({ ...f, online_only: e.target.checked || undefined }))
                    }
                  />
                  Online drivers only
                </label>
                <select
                  value={filters.priority ?? "all"}
                  onChange={(e) =>
                    setFilters((f) => ({
                      ...f,
                      priority: e.target.value as LiveMapFilters["priority"],
                    }))
                  }
                  className="w-full rounded-lg border border-primary/10 px-2 py-1.5"
                >
                  <option value="all">All priorities</option>
                  <option value="high">High priority</option>
                  <option value="normal">Normal</option>
                </select>
                <input
                  type="text"
                  placeholder="City"
                  value={filters.city ?? ""}
                  onChange={(e) => setFilters((f) => ({ ...f, city: e.target.value || undefined }))}
                  className="w-full rounded-lg border border-primary/10 px-2 py-1.5"
                />
                <input
                  type="date"
                  value={filters.date ?? ""}
                  onChange={(e) => setFilters((f) => ({ ...f, date: e.target.value || undefined }))}
                  className="w-full rounded-lg border border-primary/10 px-2 py-1.5"
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Command center widgets */}
        {data && (
          <div className="pointer-events-none absolute left-1/2 top-16 z-20 flex -translate-x-1/2 flex-wrap justify-center gap-2 px-2">
            {widgets.map((w) => (
              <div
                key={w.label}
                className={cn(
                  "pointer-events-auto flex items-center gap-2 rounded-xl border border-primary/10 bg-white/95 px-3 py-1.5 text-xs shadow-md backdrop-blur",
                  w.alert && "border-red-200 bg-red-50/95"
                )}
              >
                <w.icon className="h-3.5 w-3.5 text-secondary" />
                <span className="text-muted">{w.label}</span>
                <span className="font-bold text-primary">{w.value}</span>
              </div>
            ))}
          </div>
        )}

        <div className="relative min-h-0 flex-1">
          {/* Left operations panel */}
          <AnimatePresence>
            {leftOpen && data && (
              <motion.aside
                initial={{ x: -280 }}
                animate={{ x: 0 }}
                exit={{ x: -280 }}
                className="absolute bottom-0 left-0 top-0 z-20 flex w-72 flex-col border-r border-primary/10 bg-white/95 shadow-lg backdrop-blur"
              >
                <div className="flex gap-1 overflow-x-auto border-b border-primary/5 p-2">
                  {(
                    [
                      ["queue", "Queue"],
                      ["drivers", "Drivers"],
                      ["vehicles", "Vehicles"],
                      ["incidents", "Incidents"],
                      ["claims", "Claims"],
                      ["support", "Support"],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setLeftTab(id)}
                      className={cn(
                        "shrink-0 rounded-lg px-2 py-1 text-xs font-medium",
                        leftTab === id
                          ? "bg-secondary/10 text-secondary"
                          : "text-muted hover:bg-gray-bg"
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                  <LeftPanelContent tab={leftTab} data={data} onSelect={loadDetail} />
                </div>
              </motion.aside>
            )}
          </AnimatePresence>

          {/* Map */}
          <div className={cn("h-full", leftOpen && "lg:pl-72", rightOpen && "lg:pr-96")}>
            {data ? (
              <MapCanvas
                data={data}
                layers={layers}
                mapMode={mapMode}
                theme={theme}
                heatMetric={heatMetric}
                selectedId={selected?.id ?? null}
                onSelect={loadDetail}
                measureActive={measureActive}
                drawMode={drawMode}
                playbackFrames={playbackFrames}
                playbackIndex={playbackIndex}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-red-600">
                {error}
              </div>
            )}
          </div>

          {/* Right detail drawer */}
          <AnimatePresence>
            {rightOpen && (
              <motion.aside
                initial={{ x: 384 }}
                animate={{ x: 0 }}
                exit={{ x: 384 }}
                className="absolute bottom-0 right-0 top-0 z-20 flex w-96 flex-col border-l border-primary/10 bg-white shadow-xl"
              >
                <div className="flex items-center justify-between border-b border-primary/10 px-4 py-3">
                  <h2 className="font-semibold text-primary">Details</h2>
                  <button
                    type="button"
                    onClick={() => setRightOpen(false)}
                    aria-label="Close drawer"
                  >
                    <X className="h-5 w-5 text-muted" />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  {detailLoading ? <Spinner label="Loading details…" /> : null}
                  {!detailLoading && detailError ? (
                    <p className="text-sm text-red-600">{detailError}</p>
                  ) : null}
                  {!detailLoading && detail ? <DetailPanel detail={detail} /> : null}
                </div>
              </motion.aside>
            )}
          </AnimatePresence>

          <button
            type="button"
            onClick={() => setLeftOpen((v) => !v)}
            className="absolute left-2 top-2 z-30 rounded-lg bg-white/90 px-2 py-1 text-xs font-medium shadow lg:hidden"
          >
            {leftOpen ? "Hide panel" : "Ops panel"}
          </button>
        </div>

        {/* Bottom panel: events + playback */}
        <div
          className={cn(
            "shrink-0 border-t border-primary/10 bg-white transition-all",
            bottomOpen ? "max-h-44" : "max-h-10"
          )}
        >
          <div className="flex items-center justify-between px-3 py-1.5">
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="text-xs font-semibold text-primary"
                onClick={() => setBottomOpen((v) => !v)}
              >
                {bottomOpen ? "Hide events" : "Show events"}
              </button>
              <span className="text-xs text-muted">Playback</span>
              <input
                type="date"
                value={playbackDate}
                onChange={(e) => setPlaybackDate(e.target.value)}
                className="rounded border border-primary/10 px-2 py-0.5 text-xs"
              />
              <Button
                variant="outline"
                className="!px-2 !py-1 text-xs"
                onClick={() => void loadPlayback()}
              >
                Load
              </Button>
              <button
                type="button"
                onClick={() => setPlaying((p) => !p)}
                className="rounded-lg p-1 hover:bg-gray-bg"
                aria-label={playing ? "Pause playback" : "Play playback"}
              >
                {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              </button>
            </div>
            {data && (
              <span className="text-xs text-muted">
                Updated {relativeTime(data.generated_at)} · {data.alerts.length} alerts
              </span>
            )}
          </div>
          {bottomOpen && data && (
            <div className="grid max-h-32 grid-cols-1 gap-2 overflow-y-auto px-3 pb-2 md:grid-cols-2">
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase text-muted">
                  Live notifications
                </p>
                <ul className="space-y-1">
                  {data.alerts.slice(0, 6).map((a) => (
                    <li key={a.id} className="flex items-start gap-2 text-xs">
                      <AlertTriangle
                        className={cn(
                          "mt-0.5 h-3 w-3 shrink-0",
                          a.severity === "critical"
                            ? "text-red-500"
                            : a.severity === "warning"
                              ? "text-amber-500"
                              : "text-blue-500"
                        )}
                      />
                      <button
                        type="button"
                        className="text-left hover:text-secondary"
                        onClick={() =>
                          a.entity_id && a.entity_type && loadDetail(a.entity_type, a.entity_id)
                        }
                      >
                        <span className="font-medium">{a.title}</span> — {a.message}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase text-muted">System events</p>
                <ul className="space-y-1 text-xs text-muted">
                  {data.events.slice(0, 6).map((e) => (
                    <li key={e.id}>
                      {e.title} · {e.occurred_at ? relativeTime(e.occurred_at) : "—"}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Smart features strip */}
        {data?.smart &&
          (data.smart.traffic_warnings.length > 0 || data.smart.suggested_drivers.length > 0) && (
            <div className="absolute bottom-48 right-4 z-20 max-w-xs rounded-xl border border-primary/10 bg-white/95 p-3 text-xs shadow-lg backdrop-blur">
              <p className="mb-1 font-semibold text-primary">Smart ops</p>
              {data.smart.traffic_warnings.map((w) => (
                <p key={w} className="text-amber-700">
                  {w}
                </p>
              ))}
              {data.smart.suggested_drivers.length > 0 && (
                <p className="mt-1 text-muted">
                  Suggested: {data.smart.suggested_drivers.map((d) => d.name).join(", ")}
                </p>
              )}
            </div>
          )}
      </div>
    </GoogleMapsProvider>
  );
}

function FilterIcon({ className }: { className?: string }) {
  return <Compass className={className} />;
}

function ToolbarBtn({
  icon: Icon,
  label,
  onClick,
  active,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      title={label}
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors",
        active ? "bg-secondary/10 text-secondary" : "text-primary/70 hover:bg-gray-bg"
      )}
    >
      <Icon className="h-4 w-4" />
      <span className="hidden xl:inline">{label}</span>
    </button>
  );
}

function LeftPanelContent({
  tab,
  data,
  onSelect,
}: {
  tab: LeftTab;
  data: NonNullable<ReturnType<typeof useLiveMapData>["data"]>;
  onSelect: (type: string, id: string) => void;
}) {
  if (tab === "drivers") {
    return (
      <ul className="space-y-1">
        {data.drivers.map((d) => (
          <li key={d.id}>
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-sm hover:bg-gray-bg"
              onClick={() => onSelect("driver", d.id)}
            >
              <span className="font-medium">{d.name}</span>
              <Badge tone={d.online ? "green" : "slate"}>{d.availability}</Badge>
            </button>
          </li>
        ))}
      </ul>
    );
  }
  if (tab === "vehicles") {
    return (
      <ul className="space-y-1">
        {data.vehicles.map((v) => (
          <li key={v.id}>
            <button
              type="button"
              className="w-full rounded-lg px-2 py-2 text-left text-sm hover:bg-gray-bg"
              onClick={() => onSelect("vehicle", v.id)}
            >
              <span className="font-medium">{v.plate_number}</span>
              <span className="ml-2 text-xs text-muted">{v.vehicle_class}</span>
            </button>
          </li>
        ))}
      </ul>
    );
  }
  if (tab === "incidents") {
    return (
      <ul className="space-y-1">
        {data.alerts
          .filter((a) => a.alert_type === "incident")
          .map((a) => (
            <li key={a.id} className="rounded-lg bg-amber-50 px-2 py-2 text-xs">
              {a.message}
            </li>
          ))}
      </ul>
    );
  }
  if (tab === "claims") {
    return (
      <ul className="space-y-1">
        {data.alerts
          .filter((a) => a.alert_type === "claim")
          .map((a) => (
            <li key={a.id} className="rounded-lg bg-blue-50 px-2 py-2 text-xs">
              {a.message}
            </li>
          ))}
      </ul>
    );
  }
  if (tab === "support") {
    return (
      <p className="px-2 text-xs text-muted">{data.command_center.support_tickets} open tickets</p>
    );
  }
  // queue default
  const waiting = data.orders.filter(
    (o) => o.stop_type === "pickup" && ["BOOKED", "DISPATCH_READY"].includes(o.state)
  );
  return (
    <ul className="space-y-1">
      {waiting.map((o) => (
        <li key={o.order_id}>
          <button
            type="button"
            className="w-full rounded-lg px-2 py-2 text-left text-sm hover:bg-gray-bg"
            onClick={() => onSelect("order", o.order_id)}
          >
            <span className="font-mono text-xs">{o.tracking_number}</span>
            <p className="text-xs text-muted">{o.merchant ?? "—"}</p>
          </button>
        </li>
      ))}
      {!waiting.length && <p className="px-2 text-xs text-muted">Dispatch queue is clear</p>}
    </ul>
  );
}

function DetailPanel({ detail }: { detail: Record<string, unknown> }) {
  const actions = (detail.actions as Array<{ key: string; label: string; href: string }>) ?? [];
  const timeline = (detail.timeline as Array<{ label: string; at: string | null }>) ?? [];
  const contact = detail.contact as Record<string, string | null> | undefined;
  const currentJob = detail.current_job as Record<string, unknown> | null | undefined;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-lg font-bold text-primary">{String(detail.title ?? "")}</p>
        {detail.subtitle ? <p className="text-sm text-muted">{String(detail.subtitle)}</p> : null}
        {detail.status ? <Badge className="mt-2">{String(detail.status)}</Badge> : null}
      </div>

      {currentJob && (
        <section>
          <h3 className="text-xs font-semibold uppercase text-muted">Current job</h3>
          <pre className="mt-1 rounded-lg bg-gray-bg p-2 text-xs">
            {JSON.stringify(currentJob, null, 2)}
          </pre>
        </section>
      )}

      {contact && (contact.phone || contact.email) && (
        <section>
          <h3 className="text-xs font-semibold uppercase text-muted">Contact</h3>
          {contact.phone && <p className="text-sm">{contact.phone}</p>}
          {contact.email && <p className="text-sm">{contact.email}</p>}
        </section>
      )}

      {detail.eta ? (
        <section>
          <h3 className="text-xs font-semibold uppercase text-muted">ETA</h3>
          <p className="text-sm">{String(detail.eta)}</p>
        </section>
      ) : null}

      {timeline.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase text-muted">Timeline</h3>
          <ul className="mt-2 space-y-2 border-l-2 border-secondary/20 pl-3">
            {timeline.map((t, i) => (
              <li key={i} className="text-xs">
                <span className="font-medium">{t.label}</span>
                {t.at && <span className="ml-2 text-muted">{relativeTime(t.at)}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="flex flex-wrap gap-2">
        {actions.map((a) => (
          <Link key={a.key} href={a.href.startsWith("/") ? a.href : "#"}>
            <Button variant="outline" className="text-xs">
              {a.label}
            </Button>
          </Link>
        ))}
      </section>
    </div>
  );
}
