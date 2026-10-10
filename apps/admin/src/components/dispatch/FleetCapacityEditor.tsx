"use client";

import { useEffect, useState } from "react";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { dispatch, type FleetCapacity, type FleetVehicle } from "@/lib/dispatch";

const NUM = "w-full min-w-0 rounded-lg border border-primary/15 bg-white px-2 py-1.5 text-sm tabular-nums text-primary";

export function FleetCapacityEditor({ tick }: { tick: number }) {
  const { getApiToken } = useAdminAuth();
  const { data, error } = useApiData((t) => dispatch.fleet(t), [tick], { key: "dispatch-fleet" });
  const [draft, setDraft] = useState<FleetCapacity | null>(null);
  const [state, setState] = useState<string | null>(null);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!draft) return <p className="text-sm text-muted">Loading fleet…</p>;

  const setVehicle = (i: number, patch: Partial<FleetVehicle>) =>
    setDraft({ ...draft, vehicles: draft.vehicles.map((v, j) => (j === i ? { ...v, ...patch } : v)) });

  const save = async () => {
    setState("Saving…");
    try {
      setDraft(await dispatch.saveFleet(await getApiToken(), draft));
      setState("Saved");
    } catch (e) {
      setState(e instanceof Error ? e.message : "Save failed");
    }
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-base font-semibold text-primary">Vehicle capacity</h2>
        <p className="text-xs text-muted">
          Recommendation picks the smallest vehicle at or under {Math.round(draft.max_fill * 100)}% full.
        </p>
      </header>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <label className="text-xs text-muted">
          Driver cost $/hr
          <input
            className={NUM}
            type="number"
            min={0}
            step={0.5}
            value={draft.hourly_cost_cents / 100}
            onChange={(e) => setDraft({ ...draft, hourly_cost_cents: Math.round(Number(e.target.value) * 100) })}
          />
        </label>
        <label className="text-xs text-muted">
          Max fill %
          <input
            className={NUM}
            type="number"
            min={10}
            max={100}
            value={Math.round(draft.max_fill * 100)}
            onChange={(e) => setDraft({ ...draft, max_fill: Number(e.target.value) / 100 })}
          />
        </label>
        <label className="text-xs text-muted">
          Offer expires (sec)
          <input
            className={NUM}
            type="number"
            min={30}
            value={draft.offer_ttl_seconds}
            onChange={(e) => setDraft({ ...draft, offer_ttl_seconds: Number(e.target.value) })}
          />
        </label>
        <label className="text-xs text-muted">
          At-risk window (min)
          <input
            className={NUM}
            type="number"
            min={0}
            value={draft.at_risk_minutes}
            onChange={(e) => setDraft({ ...draft, at_risk_minutes: Number(e.target.value) })}
          />
        </label>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead>
            <tr className="text-left text-xs text-muted">
              <th className="py-1.5 pr-2 font-medium">Vehicle</th>
              <th className="py-1.5 pr-2 font-medium">Max kg</th>
              <th className="py-1.5 pr-2 font-medium">Max m³</th>
              <th className="py-1.5 pr-2 font-medium">Max boxes</th>
              <th className="py-1.5 font-medium">On</th>
            </tr>
          </thead>
          <tbody>
            {draft.vehicles.map((v, i) => (
              <tr key={v.id} className="border-t border-primary/5">
                <td className="py-2 pr-2 font-medium text-primary">{v.label}</td>
                <td className="py-2 pr-2">
                  <input aria-label={`${v.label} max kg`} className={NUM} type="number" min={1} value={v.max_kg} onChange={(e) => setVehicle(i, { max_kg: Number(e.target.value) })} />
                </td>
                <td className="py-2 pr-2">
                  <input aria-label={`${v.label} max cubic metres`} className={NUM} type="number" min={0.1} step={0.1} value={v.max_m3} onChange={(e) => setVehicle(i, { max_m3: Number(e.target.value) })} />
                </td>
                <td className="py-2 pr-2">
                  <input aria-label={`${v.label} max boxes`} className={NUM} type="number" min={1} value={v.max_boxes} onChange={(e) => setVehicle(i, { max_boxes: Number(e.target.value) })} />
                </td>
                <td className="py-2">
                  <input aria-label={`${v.label} enabled`} type="checkbox" className="h-5 w-5 accent-[var(--secondary)]" checked={v.enabled} onChange={(e) => setVehicle(i, { enabled: e.target.checked })} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <button type="button" onClick={save} className="min-h-10 rounded-xl border border-primary/15 px-4 text-sm font-semibold text-primary">
          Save capacity
        </button>
        {state && <span className="text-xs text-muted">{state}</span>}
      </div>
    </section>
  );
}
