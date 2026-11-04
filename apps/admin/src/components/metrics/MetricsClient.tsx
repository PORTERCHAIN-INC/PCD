"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/crm/primitives";
import AdminPage from "@/components/layout/AdminPage";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { fmtMetric, metrics, type MetricsBaseline } from "@/lib/metrics";

function Table({
  title,
  data,
}: {
  title: string;
  data?: Record<string, number | string | null> | null;
}) {
  return (
    <section className="rounded-lg border p-4">
      <h2 className="mb-2 font-semibold">{title}</h2>
      <dl className="grid grid-cols-2 gap-1 text-sm">
        {Object.entries(data ?? {}).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-muted-foreground">{k.replace(/_/g, " ")}</dt>
            <dd className="text-right tabular-nums">{v == null ? "—" : fmtMetric(k, v)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** Doc 79 Insights → finance baseline (finance / admin roles only; API enforces). */
export function MetricsClient() {
  const { getApiToken, authReady } = useAdminAuth();
  const [spd, setSpd] = useState(20);
  const [data, setData] = useState<MetricsBaseline | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!authReady) return;
    let live = true;
    void (async () => {
      try {
        const t = await getApiToken();
        const d = await metrics.baseline(t, spd);
        if (live) {
          setData(d);
          setErr(null);
        }
      } catch (e) {
        if (live) setErr(String(e));
      }
    })();
    return () => {
      live = false;
    };
  }, [authReady, getApiToken, spd]);

  return (
    <AdminPage
      title="Unit economics"
      description="Doc 79 baseline: route margin, EVA, break-even, payback and queueing."
    >
      <label className="mb-4 flex items-center gap-2 text-sm">
        Stops per day
        <Input
          type="number"
          min={1}
          value={spd}
          onChange={(e) => setSpd(Math.max(1, Number(e.target.value) || 1))}
          className="w-24"
        />
      </label>
      {err && <p className="text-sm text-red-600">{err}</p>}
      {data && (
        <div className="grid gap-4 md:grid-cols-2">
          <Table title="Route" data={data.route} />
          <Table title="Year" data={data.year} />
          <Table title="Break-even stops/day" data={data.break_even_stops_per_day} />
          <Table title="Payback (months) by stops/day" data={data.payback_months} />
          <Table title="Kingman wait (min) by utilisation" data={data.kingman} />
          <Table title="Compliance money" data={data.compliance_money} />
        </div>
      )}
    </AdminPage>
  );
}
