"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { dispatch } from "@/lib/dispatch";
import { canAssignPartner, COURIER_KINDS, openCourierLeg } from "@/lib/partner-assign";

const LEG_LABEL: Record<string, string> = {
  planned: "Planned",
  requested: "Requested",
  accepted: "Accepted",
  picked_up: "Picked up",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

/** L97 "Assign to fleet partner": a contractor courier carries the whole order.
 *  Progress (request, accept, picked up, delivered) is tracked in Partners → Partner jobs,
 *  and delivered legs land on the partner's payable statement. */
export function PartnerAssignPanel({
  orderId,
  orderState,
  hasDriver,
  getApiToken,
  onChanged,
}: {
  orderId: string;
  orderState?: string | null;
  hasDriver: boolean;
  getApiToken: () => Promise<string>;
  onChanged?: () => void;
}) {
  const qc = useQueryClient();
  const legsKey = ["partner-legs-for-order", orderId];
  const legs = useQuery({
    queryKey: legsKey,
    queryFn: async () =>
      (await dispatch.partnerLegs(await getApiToken())).items.filter(
        (l) => l.order_id === orderId && l.mode === "courier"
      ),
  });
  const [open, setOpen] = useState(false);
  const partners = useQuery({
    queryKey: ["dispatch-partners"],
    enabled: open,
    queryFn: async () => dispatch.partners(await getApiToken()),
  });
  const [partnerId, setPartnerId] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mine = legs.data ?? [];
  const openLeg = openCourierLeg(mine);
  const canAssign = canAssignPartner(orderState, hasDriver, mine);
  if (!mine.length && !canAssign) return null;
  const couriers = (partners.data?.items || []).filter(
    (p) => p.active && COURIER_KINDS.has(p.kind)
  );

  async function submit() {
    if (!partnerId) return;
    setBusy(true);
    setError(null);
    try {
      await dispatch.assignPartnerLeg(await getApiToken(), orderId, {
        partner_id: partnerId,
        note: note.trim() || undefined,
      });
      setOpen(false);
      setPartnerId("");
      setNote("");
      await qc.invalidateQueries({ queryKey: legsKey });
      await qc.invalidateQueries({ queryKey: ["partner-legs"] });
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not assign the partner");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-slate-900">Fleet partner</h3>
        {canAssign && !open ? (
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-50"
            onClick={() => setOpen(true)}
          >
            Assign to fleet partner
          </button>
        ) : null}
      </div>
      {mine.length ? (
        <ul className="mt-2 space-y-1 text-slate-600">
          {mine.map((l) => (
            <li key={l.id} data-testid="partner-leg-row">
              {l.partner_name ?? "Partner"} · {LEG_LABEL[l.status] ?? l.status}
              {l.est_cost_cents ? ` · est. $${(l.est_cost_cents / 100).toFixed(2)}` : ""}
            </li>
          ))}
          {openLeg ? (
            <li className="text-xs text-slate-500">Update progress in Partners → Partner jobs.</li>
          ) : null}
        </ul>
      ) : (
        <p className="mt-2 text-slate-500">
          Our drivers carry this order. A contractor fleet can take it instead.
        </p>
      )}
      {open ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            aria-label="Fleet partner"
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            value={partnerId}
            onChange={(e) => setPartnerId(e.target.value)}
          >
            <option value="">{partners.isLoading ? "Loading…" : "Choose fleet partner"}</option>
            {couriers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <input
            aria-label="Note for the partner"
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            placeholder="Note (optional)"
            value={note}
            maxLength={300}
            onChange={(e) => setNote(e.target.value)}
          />
          <button
            type="button"
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
            disabled={!partnerId || busy}
            onClick={() => void submit()}
          >
            {busy ? "Assigning…" : "Confirm partner"}
          </button>
          <button
            type="button"
            className="px-2 py-1.5 text-xs text-slate-500"
            onClick={() => setOpen(false)}
          >
            Cancel
          </button>
          {!partners.isLoading && couriers.length === 0 ? (
            <span className="text-xs text-slate-500">
              No active courier partner yet. Add one under Partners.
            </span>
          ) : null}
        </div>
      ) : null}
      {error ? (
        <p role="alert" className="mt-2 text-xs text-red-700">
          {error}
        </p>
      ) : null}
    </section>
  );
}
