"use client";

import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";

export default function MapPage() {
  const { data } = useApiData((t) => api.liveMap(t));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Live Map</h1>
      <p className="text-sm text-muted">
        Driver and order positions via Porterchain API bridge — Fleetbase UI is not embedded.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-primary/10 bg-white p-6">
          <h2 className="font-semibold">Online Drivers ({data?.drivers ? (data.drivers as unknown[]).length : 0})</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {((data?.drivers as Array<Record<string, unknown>>) || []).map((d) => (
              <li key={String(d.id)}>
                {String(d.name)} — {String(d.status)}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-primary/10 bg-white p-6">
          <h2 className="font-semibold">Active Orders ({data?.orders ? (data.orders as unknown[]).length : 0})</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {((data?.orders as Array<Record<string, unknown>>) || []).map((o) => (
              <li key={String(o.order_id)}>
                <span className="font-mono">{String(o.tracking)}</span> — {String(o.state)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
