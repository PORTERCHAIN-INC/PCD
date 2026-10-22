"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { dispatch, HUB_SPLITTABLE, HUB_STAGE_LABEL } from "@/lib/dispatch";

/** "Split at warehouse": the pickup van drops at our hub, a delivery van takes it from there.
 *  The delivery driver is set with the normal Assign/Reassign action or by "Plan the day". */
export function HubSplitPanel({
  orderId,
  orderState,
  getApiToken,
  onChanged,
}: {
  orderId: string;
  orderState?: string | null;
  getApiToken: () => Promise<string>;
  onChanged?: () => void;
}) {
  const qc = useQueryClient();
  const key = ["hub-split", orderId];
  const split = useQuery({
    queryKey: key,
    queryFn: async () => dispatch.hubSplit(await getApiToken(), orderId),
  });
  const [open, setOpen] = useState(false);
  const partners = useQuery({
    queryKey: ["dispatch-partners"],
    enabled: open,
    queryFn: async () => dispatch.partners(await getApiToken()),
  });
  const [hubId, setHubId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const data = split.data;
  const canSplit = !data?.split && HUB_SPLITTABLE.has(String(orderState || ""));
  if (!data?.split && !canSplit) return null;
  const hubs = (partners.data?.items || []).filter(
    (p) => p.kind === "warehouse" && p.active && p.lat != null && p.lng != null
  );

  async function submit() {
    if (!hubId) return;
    setBusy(true);
    setError(null);
    try {
      await dispatch.splitAtHub(await getApiToken(), orderId, { hub_partner_id: hubId });
      setOpen(false);
      await qc.invalidateQueries({ queryKey: key });
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Split failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-slate-900">Warehouse split</h3>
        {canSplit && !open ? (
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-50"
            onClick={() => setOpen(true)}
          >
            Split at warehouse
          </button>
        ) : null}
      </div>
      {data?.split ? (
        <p className="mt-2 text-slate-700">
          {data.stage ? HUB_STAGE_LABEL[data.stage] : "Split"} · Hub:{" "}
          <span className="font-medium">{data.hub?.name || data.hub?.formatted || "—"}</span>
          {data.stage === "at_hub" && !data.delivery_driver_id
            ? " · No delivery driver yet (assign one or use Plan the day)"
            : ""}
        </p>
      ) : (
        <p className="mt-2 text-slate-500">
          Pickup and delivery run as one trip. Split to drop at our warehouse first.
        </p>
      )}
      {open ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            aria-label="Warehouse"
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            value={hubId}
            onChange={(e) => setHubId(e.target.value)}
          >
            <option value="">{partners.isLoading ? "Loading…" : "Choose warehouse"}</option>
            {hubs.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!hubId || busy}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
            onClick={() => void submit()}
          >
            {busy ? "Splitting…" : "Confirm split"}
          </button>
          <button
            type="button"
            className="px-2 py-1.5 text-xs text-slate-500"
            onClick={() => setOpen(false)}
          >
            Cancel
          </button>
          {!partners.isLoading && hubs.length === 0 ? (
            <span className="text-xs text-amber-700">
              No geocoded warehouse yet. Add one under Dispatch → Partners.
            </span>
          ) : null}
        </div>
      ) : null}
      {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}
    </section>
  );
}
