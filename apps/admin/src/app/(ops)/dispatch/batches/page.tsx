"use client";

import { BATCH_TONE_CLASS, batchStatusLabel } from "@porterchain/types/batch-status";
import { useCallback, useState } from "react";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { JobDocsPanel } from "@/components/jobs/JobDocsPanel";
import AdminPage from "@/components/layout/AdminPage";
import { useAdminAuth } from "@/components/providers/AdminAuthProvider";
import { useApiData } from "@/hooks/useApiData";
import { adminFetch } from "@/lib/api";
import type { Fetcher } from "@/lib/job-docs";

function BatchStatus({ status }: { status: string }) {
  const s = batchStatusLabel(status);
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${BATCH_TONE_CLASS[s.tone]}`}
      data-status={status}
    >
      {s.label}
    </span>
  );
}

const DOC_LABEL: Record<string, string> = {
  bol: "Bill of lading",
  packing_slip: "Packing slip",
  customs_docs: "Customs documents",
  rx_custody_log: "Rx custody log",
  tdg: "Dangerous goods (TDG)",
  sealed: "Sealed load",
  signed_handover: "Signed handover",
};
const TH = "px-3 py-3 font-medium";
const TD = "px-3 py-3";

type BatchRow = {
  id: string;
  merchant_id: string;
  status: string;
  parcels?: number;
  routes?: number;
  waves?: number;
  pickup_docs: string[];
  created_at?: string | null;
};
type BatchDetail = {
  id: string;
  status: string;
  routes: Array<{
    id: string;
    route_no: number;
    wave: number;
    driver_id: string | null;
    status: string;
    parcels: number;
  }>;
};

export default function AdminBatchesPage() {
  const { getApiToken } = useAdminAuth();
  const { data, error, loading } = useApiData(
    (t) => adminFetch<{ batches: BatchRow[] }>("/v1/admin/batches", t),
    ["admin-batches"]
  );
  const [sel, setSel] = useState<string | null>(null);
  const [detail, setDetail] = useState<BatchDetail | null>(null);
  const fetcher = useCallback<Fetcher>(
    async (path, init) => adminFetch(path, await getApiToken(), init),
    [getApiToken]
  );

  async function open(id: string) {
    setSel(id);
    setDetail(await fetcher<BatchDetail>(`/v1/admin/batches/${id}`));
  }

  const batches = data?.batches ?? [];
  return (
    <AdminPage
      title="Bulk batches"
      description="CSV batches from merchants: routes, waves, drivers and pickup documents."
    >
      {loading ? (
        <PageSkeleton rows={4} />
      ) : error ? (
        <EmptyState title="Batches unavailable" hint={error} />
      ) : batches.length === 0 ? (
        <EmptyState
          title="No batches yet"
          hint="Merchant CSV batches show up here once uploaded."
        />
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
          <table className="w-full min-w-[48rem] text-left text-sm">
            <thead className="border-b border-primary/10 bg-gray-50/80 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className={TH}>Batch</th>
                <th className={TH}>Merchant</th>
                <th className={TH}>Status</th>
                <th className={TH}>Parcels</th>
                <th className={TH}>Routes / waves</th>
                <th className={TH}>Docs required</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr
                  key={b.id}
                  className={`cursor-pointer border-b border-primary/5 hover:bg-gray-50/50 ${sel === b.id ? "bg-gray-50" : ""}`}
                  onClick={() => void open(b.id)}
                >
                  <td className={`${TD} font-mono font-medium text-secondary`}>
                    {b.id.slice(0, 8)}
                  </td>
                  <td className={`${TD} font-mono text-muted`}>{b.merchant_id.slice(0, 8)}</td>
                  <td className={TD}>
                    <BatchStatus status={b.status} />
                  </td>
                  <td className={TD}>{b.parcels ?? "—"}</td>
                  <td className={TD}>
                    {b.routes ?? "—"} / {b.waves ?? "—"}
                  </td>
                  <td className={`${TD} text-muted`}>
                    {b.pickup_docs.map((d) => DOC_LABEL[d] ?? d).join(", ") || "None"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {sel && detail && (
        <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-primary">Routes</h2>
          <ul className="divide-y divide-primary/5 text-sm">
            {detail.routes.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center gap-2 py-2">
                <span className="font-medium text-primary">Route {r.route_no}</span>
                <span className="text-muted">
                  Wave {r.wave} · {r.parcels} parcels
                </span>
                <BatchStatus status={r.status} />
                <span className="text-muted">
                  Driver:{" "}
                  {r.driver_id ? (
                    <span className="font-mono">{r.driver_id.slice(0, 8)}</span>
                  ) : (
                    "Unassigned"
                  )}
                </span>
              </li>
            ))}
          </ul>
          <JobDocsPanel
            key={sel}
            fetcher={fetcher}
            base="/v1/admin/jobs"
            kind="batches"
            id={sel}
            canPartner
          />
        </section>
      )}
    </AdminPage>
  );
}
