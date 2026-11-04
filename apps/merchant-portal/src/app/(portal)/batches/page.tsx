"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { BATCH_TONE_CLASS, batchStatusLabel } from "@porterchain/types/batch-status";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import { JobDocsPanel } from "@/components/jobs/JobDocsPanel";
import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { merchantDownload, merchantFetch } from "@/lib/api";
import type { Fetcher } from "@/lib/job-docs";

type BatchRow = {
  id: string;
  status: string;
  parcels?: number;
  routes?: number;
  waves?: number;
  pickup_docs: string[];
};
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

const DOC_FLAGS = [
  "bol",
  "packing_slip",
  "customs_docs",
  "rx_custody_log",
  "tdg",
  "sealed",
  "signed_handover",
] as const;
const DOC_LABEL: Record<string, string> = {
  bol: "Bill of lading",
  packing_slip: "Packing slip",
  customs_docs: "Customs documents",
  rx_custody_log: "Rx custody log",
  tdg: "Dangerous goods (TDG)",
  sealed: "Sealed load",
  signed_handover: "Signed handover",
};
const VEHICLES: Array<[string, string]> = [
  ["car", "Car"],
  ["suv", "SUV"],
  ["cargo_van", "Cargo van"],
  ["box_truck", "Box truck"],
];
const FIELD = "min-h-10 rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm";

export default function MerchantBatchesPage() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const qc = useQueryClient();
  const fetcher = useCallback<Fetcher>(
    async (path, init) => merchantFetch(path, await getApiToken(), { ...init, orgId }),
    [getApiToken, orgId]
  );
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["merchant-batches", orgId ?? null],
    enabled: Boolean(isLoaded && isSignedIn && orgId),
    queryFn: () => fetcher<{ batches: BatchRow[] }>("/v1/merchant/batches"),
  });
  const [csv, setCsv] = useState("");
  const [vehicle, setVehicle] = useState("cargo_van");
  const [drivers, setDrivers] = useState(1);
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);

  const [dupes, setDupes] = useState<Array<{ code: string; row_no: number }> | null>(null);

  async function downloadEdi(id: string, kind: "214" | "856") {
    try {
      const { blob, filename } = await merchantDownload(
        `/v1/merchant/batches/${id}/edi/${kind}`,
        await getApiToken(),
        orgId
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setMsg(`EDI download failed: ${(e as Error).message}`);
    }
  }

  async function upload(confirmDuplicates = false) {
    try {
      const b = await fetcher<{
        id: string;
        plan: { parcels: number; routes: number; waves: number };
      }>("/v1/merchant/batches", {
        method: "POST",
        body: JSON.stringify({
          csv,
          vehicle_class: vehicle,
          drivers,
          doc_flags: flags,
          confirm_duplicates: confirmDuplicates,
        }),
      });
      setMsg(
        `Batch created: ${b.plan.parcels} parcels, ${b.plan.routes} routes, ${b.plan.waves} waves.`
      );
      setCsv("");
      setSel(b.id);
      setDupes(null);
      await qc.invalidateQueries({ queryKey: ["merchant-batches"] });
    } catch (e) {
      const d = e as {
        status?: number;
        detail?: { code?: string; warnings?: Array<{ code: string; row_no: number }> };
      };
      if (d.status === 409 && d.detail?.code === "duplicates_need_confirm") {
        setDupes(d.detail.warnings ?? []);
        setMsg(
          `Possible duplicate orders in ${d.detail.warnings?.length ?? 0} row(s). Review and confirm to upload anyway.`
        );
        return;
      }
      setMsg(e instanceof Error ? e.message : String(e));
    }
  }

  const batches = data?.batches ?? [];
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Bulk batches</h1>
        <p className="text-sm text-muted">
          Upload a CSV, we group stops by building and split routes by vehicle capacity.
        </p>
      </div>
      <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-4 text-sm sm:p-6">
        <p className="text-muted">
          One parcel and barcode per CSV row. Columns: address (required), recipient, unit,
          weight_kg, handling, client_label.
        </p>
        <label className="block">
          <span className="mb-1 block font-medium text-primary">CSV file</span>
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label="CSV file"
            className="block w-full text-sm text-muted file:mr-3 file:rounded-xl file:border-0 file:bg-gray-bg file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary hover:file:bg-primary/10"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (f) setCsv(await f.text());
            }}
          />
        </label>
        <label className="block">
          <span className="mb-1 block font-medium text-primary">Or paste CSV</span>
          <textarea
            aria-label="CSV"
            className={`${FIELD} w-full font-mono`}
            rows={5}
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
          />
        </label>
        <div className="flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="mb-1 block font-medium text-primary">Vehicle</span>
            <select
              aria-label="Vehicle"
              className={FIELD}
              value={vehicle}
              onChange={(e) => setVehicle(e.target.value)}
            >
              {VEHICLES.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block font-medium text-primary">Drivers</span>
            <input
              type="number"
              min={1}
              max={200}
              value={drivers}
              className={`${FIELD} w-24`}
              onChange={(e) => setDrivers(Number(e.target.value) || 1)}
            />
          </label>
        </div>
        <fieldset>
          <legend className="mb-2 font-medium text-primary">Documents needed at pickup</legend>
          <div className="flex flex-wrap gap-2">
            {DOC_FLAGS.map((f) => (
              <label
                key={f}
                className="inline-flex items-center gap-2 rounded-xl border border-primary/15 px-3 py-2"
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[#2563eb]"
                  checked={!!flags[f]}
                  onChange={(e) => setFlags({ ...flags, [f]: e.target.checked })}
                />{" "}
                {DOC_LABEL[f]}
              </label>
            ))}
          </div>
        </fieldset>
        <Button type="button" disabled={!csv.trim()} onClick={() => void upload()}>
          Create batch
        </Button>
        {msg && (
          <p role="status" className="rounded-xl border border-primary/10 bg-gray-bg px-3 py-2">
            {msg}
          </p>
        )}
        {dupes && dupes.length > 0 && (
          <div
            role="alert"
            className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900"
          >
            <ul className="space-y-1">
              {dupes.map((w, i) => (
                <li key={i}>
                  Row {w.row_no}: {w.code.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <Button type="button" size="sm" onClick={() => void upload(true)}>
                Upload anyway
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  setDupes(null);
                  setMsg("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </section>
      {isLoading ? (
        <PageSkeleton rows={4} />
      ) : error ? (
        <EmptyState
          title="Batches unavailable"
          hint={String(error)}
          action={<Button onClick={() => void refetch()}>Retry</Button>}
        />
      ) : batches.length === 0 ? (
        <EmptyState title="No batches yet" hint="Upload a CSV above to plan your first batch." />
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-b border-primary/10 bg-gray-50/80">
              <tr>
                <th className="px-3 py-3 font-medium">Batch</th>
                <th className="px-3 py-3 font-medium">Status</th>
                <th className="px-3 py-3 font-medium">Parcels</th>
                <th className="px-3 py-3 font-medium">Routes</th>
                <th className="px-3 py-3 font-medium">Pickup documents</th>
                <th className="px-3 py-3 font-medium">EDI</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr
                  key={b.id}
                  className={`border-b border-primary/5 hover:bg-gray-50/50 ${sel === b.id ? "bg-gray-50" : ""}`}
                >
                  <td className="px-3 py-3">
                    <button
                      type="button"
                      className="font-mono font-medium text-secondary hover:underline"
                      onClick={() => setSel(b.id)}
                    >
                      {b.id.slice(0, 8)}
                    </button>
                  </td>
                  <td className="px-3 py-3">
                    <BatchStatus status={b.status} />
                  </td>
                  <td className="px-3 py-3">{b.parcels ?? "—"}</td>
                  <td className="px-3 py-3">{b.routes ?? "—"}</td>
                  <td className="px-3 py-3 text-muted">
                    {b.pickup_docs.map((d) => DOC_LABEL[d] ?? d).join(", ") || "None"}
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => downloadEdi(b.id, "856")}
                        aria-label={`Download EDI 856 ship notice for batch ${b.id.slice(0, 8)}`}
                      >
                        856
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => downloadEdi(b.id, "214")}
                        aria-label={`Download EDI 214 status for batch ${b.id.slice(0, 8)}`}
                      >
                        214
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {sel && (
        <JobDocsPanel
          key={sel}
          fetcher={fetcher}
          base="/v1/merchant/jobs"
          kind="batches"
          id={sel}
        />
      )}
    </div>
  );
}
