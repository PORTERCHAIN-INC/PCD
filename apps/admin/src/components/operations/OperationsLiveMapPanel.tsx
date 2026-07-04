"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ExternalLink,
  Layers,
  MapPin,
  Radio,
  RefreshCw,
  Truck,
  Users,
  X,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useLiveMapData } from "@/hooks/useLiveMapData";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import MapCanvas from "@/components/live-map/MapCanvas";
import { liveMapApi, parseLiveMapEntityId, type MapLayers } from "@/lib/live-map";
import { isGoogleMapsConfigured } from "@/lib/maps";
import { money, relativeTime, titleCase } from "@/lib/crmFormat";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";

const OPS_LAYERS: MapLayers = {
  drivers: true,
  vehicles: true,
  orders: true,
  warehouses: false,
  merchants: false,
  customers: false,
  geofences: false,
  traffic: false,
  heatMap: false,
  routes: false,
  labels: true,
  cluster: true,
};

type Props = {
  tick?: number;
  onFleetbase?: () => void;
};

export function OperationsLiveMapPanel({ tick = 0, onFleetbase }: Props) {
  const { getApiToken } = useAdminAuth();
  const { data, error, connected, refresh } = useLiveMapData();
  const [layers, setLayers] = useState<MapLayers>(OPS_LAYERS);
  const [selected, setSelected] = useState<{ type: string; id: string } | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    void refresh();
  }, [tick, refresh]);

  const loadDetail = useCallback(
    async (type: string, id: string) => {
      const { entityType, entityId } = parseLiveMapEntityId(type, id);
      setSelected({ type: entityType, id: entityId });
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

  const cc = data?.command_center;
  const stats = useMemo(
    () =>
      cc
        ? [
            { label: "In flight", value: data?.orders.length ?? 0, icon: Truck },
            { label: "Drivers online", value: cc.drivers_online, icon: Users },
            { label: "Waiting", value: cc.orders_waiting, icon: MapPin },
            {
              label: "Late",
              value: cc.late_orders,
              icon: AlertTriangle,
              alert: cc.late_orders > 0,
            },
          ]
        : [],
    [cc, data?.orders.length]
  );

  const onlineDrivers = useMemo(
    () => (data?.drivers ?? []).filter((d) => d.online),
    [data?.drivers]
  );

  function toggleLayer(key: keyof MapLayers) {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  if (!data && !error) {
    return (
      <SectionCard title="Live map">
        <Spinner label="Loading live map…" />
      </SectionCard>
    );
  }

  return (
    <GoogleMapsProvider>
      <div className="space-y-4">
        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {stats.length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {stats.map(({ label, value, icon: Icon, alert }) => (
              <div
                key={label}
                className={cn(
                  "rounded-xl border bg-white px-4 py-3",
                  alert ? "border-red-200 bg-red-50/50" : "border-primary/10"
                )}
              >
                <div className="flex items-center gap-2 text-muted">
                  <Icon className="h-4 w-4" />
                  <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
                </div>
                <p
                  className={cn("mt-1 text-2xl font-bold", alert ? "text-red-700" : "text-primary")}
                >
                  {value}
                </p>
              </div>
            ))}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
          <SectionCard
            title="Live network"
            action={
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={connected ? "green" : "amber"}>{connected ? "Live" : "Polling"}</Badge>
                {data && (
                  <span className="hidden text-xs text-muted sm:inline">
                    Updated {relativeTime(data.generated_at)}
                  </span>
                )}
                <Button
                  variant="outline"
                  className="gap-1.5 px-2 py-1 text-xs"
                  onClick={() => void refresh()}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refresh
                </Button>
                <Link href="/live-map">
                  <Button variant="outline" className="gap-1.5 px-2 py-1 text-xs">
                    <ExternalLink className="h-3.5 w-3.5" />
                    Full map
                  </Button>
                </Link>
              </div>
            }
            className="overflow-hidden"
          >
            <div className="flex flex-wrap items-center gap-2 border-b border-primary/10 px-4 py-2">
              <Layers className="h-4 w-4 text-muted" />
              {(["drivers", "vehicles", "orders", "cluster"] as const).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => toggleLayer(key)}
                  className={cn(
                    "rounded-lg px-2.5 py-1 text-xs font-medium transition-colors",
                    layers[key]
                      ? "bg-secondary text-white"
                      : "bg-gray-bg text-muted hover:text-primary"
                  )}
                >
                  {titleCase(key)}
                </button>
              ))}
            </div>

            <div className="relative h-[min(520px,58vh)] min-h-[360px] w-full">
              {data ? (
                <MapCanvas
                  data={data}
                  layers={layers}
                  mapMode="roadmap"
                  theme="light"
                  heatMetric="orders"
                  selectedId={selected?.id ?? null}
                  onSelect={loadDetail}
                  measureActive={false}
                  drawMode="none"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted">
                  No map data
                </div>
              )}

              {selected && (
                <div className="absolute bottom-3 left-3 right-3 z-10 max-h-[40%] overflow-y-auto rounded-xl border border-primary/10 bg-white/95 p-4 shadow-lg backdrop-blur-sm">
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                      Selected
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setSelected(null);
                        setDetail(null);
                        setDetailError(null);
                      }}
                      aria-label="Close detail"
                    >
                      <X className="h-4 w-4 text-muted" />
                    </button>
                  </div>
                  {detailLoading && <Spinner label="Loading…" />}
                  {!detailLoading && detailError && (
                    <p className="text-sm text-red-600">{detailError}</p>
                  )}
                  {!detailLoading && detail && <MapDetailCard detail={detail} />}
                </div>
              )}
            </div>

            {!isGoogleMapsConfigured() && (
              <p className="border-t border-primary/10 px-4 py-3 text-xs text-muted">
                Add <code className="rounded bg-gray-bg px-1">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code>{" "}
                to enable the interactive map. Driver and order lists remain available on the right.
              </p>
            )}
          </SectionCard>

          <div className="space-y-4">
            <SectionCard title={`Online drivers (${onlineDrivers.length})`}>
              <div className="max-h-[280px] divide-y divide-primary/5 overflow-y-auto">
                {onlineDrivers.length === 0 ? (
                  <EmptyState title="No drivers online" />
                ) : (
                  onlineDrivers.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-primary/[0.02]"
                      onClick={() => void loadDetail("driver", d.id)}
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-primary">{d.name}</p>
                        <p className="text-xs text-muted">
                          {titleCase(d.status)}
                          {d.vehicle_plate ? ` · ${d.vehicle_plate}` : ""}
                        </p>
                      </div>
                      <Badge tone="green">Online</Badge>
                    </button>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title={`Active orders (${data?.orders.length ?? 0})`}>
              <div className="max-h-[280px] divide-y divide-primary/5 overflow-y-auto">
                {(data?.orders ?? []).length === 0 ? (
                  <EmptyState title="No active orders on map" />
                ) : (
                  (data?.orders ?? []).slice(0, 30).map((o) => (
                    <button
                      key={`${o.order_id}-${o.stop_type}`}
                      type="button"
                      className="flex w-full items-start justify-between gap-2 px-4 py-3 text-left hover:bg-primary/[0.02]"
                      onClick={() => void loadDetail("order", `${o.order_id}-${o.stop_type}`)}
                    >
                      <div className="min-w-0">
                        <p className="font-mono text-xs font-semibold text-primary">
                          {o.tracking_number}
                        </p>
                        <p className="truncate text-xs text-muted">
                          {titleCase(o.stop_type)} · {titleCase(o.state)}
                          {o.merchant ? ` · ${o.merchant}` : ""}
                        </p>
                      </div>
                      {o.priority === "high" ? <Badge tone="red">High</Badge> : null}
                    </button>
                  ))
                )}
              </div>
            </SectionCard>

            {(data?.alerts.length ?? 0) > 0 && (
              <SectionCard title={`Alerts (${data!.alerts.length})`}>
                <div className="max-h-[200px] divide-y divide-primary/5 overflow-y-auto">
                  {data!.alerts.slice(0, 8).map((a) => (
                    <div key={a.id} className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Radio className="h-3.5 w-3.5 text-amber-600" />
                        <p className="text-sm font-medium text-primary">{a.title}</p>
                      </div>
                      <p className="mt-0.5 text-xs text-muted">{a.message}</p>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
          </div>
        </div>

        <p className="text-xs text-muted">
          Positions sync via Porterchain live map WebSocket.{" "}
          <Link href="/live-map" className="font-medium text-secondary underline">
            Open full Live Operations Map
          </Link>
          {onFleetbase ? (
            <>
              {" "}
              or{" "}
              <button
                type="button"
                onClick={onFleetbase}
                className="font-medium text-secondary underline"
              >
                Fleetbase console
              </button>
            </>
          ) : null}
          {cc ? <> · Today {money(cc.revenue_today_cents)} revenue</> : null}
        </p>
      </div>
    </GoogleMapsProvider>
  );
}

function MapDetailCard({ detail }: { detail: Record<string, unknown> }) {
  const actions = (detail.actions as Array<{ key: string; label: string; href: string }>) ?? [];
  const timeline = (detail.timeline as Array<{ label: string; at: string | null }>) ?? [];

  return (
    <div className="space-y-3">
      <div>
        <p className="font-semibold text-primary">{String(detail.title ?? "")}</p>
        {detail.subtitle ? <p className="text-sm text-muted">{String(detail.subtitle)}</p> : null}
        {detail.status ? <Badge className="mt-1">{String(detail.status)}</Badge> : null}
      </div>

      {detail.eta ? (
        <p className="text-xs text-muted">
          ETA: <span className="font-medium text-primary">{String(detail.eta)}</span>
        </p>
      ) : null}

      {timeline.length > 0 && (
        <ul className="space-y-1 border-l-2 border-secondary/20 pl-3 text-xs">
          {timeline.slice(0, 4).map((t, i) => (
            <li key={i}>
              <span className="font-medium">{t.label}</span>
              {t.at ? <span className="ml-2 text-muted">{relativeTime(t.at)}</span> : null}
            </li>
          ))}
        </ul>
      )}

      {actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {actions.map((a) => (
            <Link key={a.key} href={a.href.startsWith("/") ? a.href : "#"}>
              <Button variant="outline" className="px-2 py-1 text-xs">
                {a.label}
              </Button>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
