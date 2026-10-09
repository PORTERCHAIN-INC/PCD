export type AttributionRow = { key: string; count: number };

export type LeadAttributionSummary = {
  window_days: number;
  total: number;
  truncated?: boolean;
  calculator_leads: number;
  marketing_opt_in: number;
  by_source: AttributionRow[];
  by_industry: AttributionRow[];
  by_fsa: AttributionRow[];
  by_utm_source: AttributionRow[];
  by_utm_campaign: AttributionRow[];
};

function Table({ title, rows }: { title: string; rows: AttributionRow[] }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No leads in this window.</p>
      ) : (
        <table className="mt-3 w-full text-sm">
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-slate-100">
                <td className="py-1.5 pr-3 text-slate-700">{row.key}</td>
                <td className="w-1/2 py-1.5">
                  <div
                    className="h-2 rounded bg-blue-500"
                    style={{ width: `${(row.count / max) * 100}%` }}
                  />
                </td>
                <td className="py-1.5 pl-3 text-right font-medium tabular-nums text-slate-900">
                  {row.count}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/** Leads by source / industry / FSA / UTM (read-only marketing view). */
export default function LeadAttributionView({ data }: { data: LeadAttributionSummary | null }) {
  if (!data) {
    return (
      <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Lead attribution is unavailable. Sign in with a staff account that can read CRM leads.
      </p>
    );
  }
  const optInRate = data.total ? Math.round((data.marketing_opt_in / data.total) * 100) : 0;
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          ["Leads", String(data.total)],
          ["From calculator", String(data.calculator_leads)],
          ["Marketing opt-in (CASL)", `${data.marketing_opt_in} (${optInRate}%)`],
          ["Window", `${data.window_days} days`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-4">
            <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
            <dd className="mt-1 text-xl font-semibold text-slate-900">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="By source" rows={data.by_source} />
        <Table title="By industry" rows={data.by_industry} />
        <Table title="By FSA (pickup / service area)" rows={data.by_fsa} />
        <Table title="By UTM source" rows={data.by_utm_source} />
        <Table title="By UTM campaign" rows={data.by_utm_campaign} />
      </div>
      {data.truncated ? (
        <p className="text-xs text-slate-500">
          Showing the most recent 20,000 leads in the window.
        </p>
      ) : null}
    </div>
  );
}
