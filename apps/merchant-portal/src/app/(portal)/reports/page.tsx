"use client";

import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { getReports } from "@/lib/api";
import { formatCents } from "@/lib/utils";
import { useEffect, useState } from "react";

export default function ReportsPage() {
  const { getApiToken, orgId, isSignedIn, isLoaded } = useMerchantAuth();
  const [data, setData] = useState<Awaited<ReturnType<typeof getReports>> | null>(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      const token = await getApiToken();
      setData(await getReports(token, orgId));
    })();
  }, [getApiToken, orgId, isLoaded, isSignedIn]);

  if (!data) return <p className="text-muted">Loading reports…</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-primary">Reports</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="Monthly orders" value={String(data.monthly_orders)} />
        <Metric label="Monthly spend" value={formatCents(data.monthly_spend_cents)} />
        <Metric label="Delivery success" value={`${data.delivery_success_percent}%`} />
        <Metric label="Invoice summary" value={formatCents(data.invoice_summary_cents)} />
      </div>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Top routes</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {data.top_routes.length === 0 && <li className="text-muted">No route data this month</li>}
          {data.top_routes.map((r) => (
            <li key={r.route} className="flex justify-between gap-4">
              <span className="truncate text-muted">{r.route}</span>
              <span className="font-medium">{r.count}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
    </div>
  );
}
