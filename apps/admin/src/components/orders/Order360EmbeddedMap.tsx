"use client";

import { useMemo, useState } from "react";
import { Radio } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import MapCanvas from "@/components/live-map/MapCanvas";
import { useLiveMapData } from "@/hooks/useLiveMapData";
import { DEFAULT_LAYERS, type LiveMapSnapshot } from "@/lib/live-map";
import { Spinner } from "@/components/crm/primitives";

type Props = {
  orderId: string;
  driverId?: string | null;
  merchantId?: string | null;
};

function filterForOrder(
  data: LiveMapSnapshot,
  orderId: string,
  driverId?: string | null
): LiveMapSnapshot {
  const orders = data.orders.filter((o) => o.order_id === orderId);
  const drivers = driverId
    ? data.drivers.filter((d) => d.id === driverId)
    : data.drivers.filter((d) => d.current_order_id === orderId);
  const driverVehicleIds = new Set(
    drivers.map((d) => d.vehicle_id).filter((id): id is string => Boolean(id))
  );
  const vehicles = data.vehicles.filter(
    (v) => driverVehicleIds.has(v.id) || drivers.some((d) => d.id === v.driver_id)
  );
  const center =
    drivers.find((d) => d.location)?.location ??
    orders[0]?.location ??
    data.default_center;

  return {
    ...data,
    default_center: center,
    orders,
    drivers,
    vehicles,
    merchants: data.merchants,
    customers: data.customers,
    warehouses: data.warehouses.filter(
      (w) => orders.some((o) => o.merchant_id === w.merchant_id) || orders.length === 0
    ),
    alerts: data.alerts.filter((a) => a.entity_id === orderId || a.entity_id === driverId),
    events: data.events.filter(
      (e) => e.aggregate_id === orderId || e.aggregate_id === driverId
    ),
  };
}

export default function Order360EmbeddedMap({ orderId, driverId, merchantId }: Props) {
  const filters = useMemo(
    () => (merchantId ? { merchant_id: merchantId } : undefined),
    [merchantId]
  );
  const { data, connected, error } = useLiveMapData(filters);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const layers = useMemo(
    () => ({
      ...DEFAULT_LAYERS,
      traffic: true,
      warehouses: false,
      merchants: false,
      customers: false,
      cluster: false,
      heatMap: false,
      routes: true,
    }),
    []
  );

  const filtered = useMemo(
    () => (data ? filterForOrder(data, orderId, driverId) : null),
    [data, orderId, driverId]
  );

  if (error) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-xl border border-primary/10 bg-gray-bg text-sm text-muted">
        Map unavailable: {error}
      </div>
    );
  }

  if (!filtered) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-xl border border-primary/10">
        <Spinner />
      </div>
    );
  }

  const activeDriver = filtered.drivers[0];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium",
            connected ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
          )}
        >
          <Radio className="h-3 w-3" />
          {connected ? "Live" : "Polling"}
        </span>
        {activeDriver?.speed_kmh != null && (
          <span>Speed {Math.round(activeDriver.speed_kmh)} km/h</span>
        )}
        {activeDriver?.heading != null && <span>Heading {Math.round(activeDriver.heading)}°</span>}
        {filtered.orders[0]?.eta && <span>ETA {new Date(filtered.orders[0].eta).toLocaleString()}</span>}
      </div>
      <div className="relative h-[420px] overflow-hidden rounded-xl border border-primary/10">
        <GoogleMapsProvider>
          <MapCanvas
            data={filtered}
            layers={layers}
            mapMode="roadmap"
            theme="light"
            heatMetric="orders"
            selectedId={selectedId}
            onSelect={(_, id) => setSelectedId(id)}
            measureActive={false}
            drawMode="none"
          />
        </GoogleMapsProvider>
      </div>
    </div>
  );
}
