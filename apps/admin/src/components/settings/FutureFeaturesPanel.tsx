"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { adminFetch } from "@/lib/api";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

type Feature = {
  id: string;
  group: string;
  title: string;
  description: string;
  threshold: number;
  enabled: boolean;
  ready: boolean;
};
type Overview = { parcels_per_day: number; features: Feature[] };

export default function FutureFeaturesPanel() {
  const { getApiToken } = useAdminAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [on, setOn] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const t = await getApiToken();
      const o = await adminFetch<Overview>("/v1/admin/settings/future", t);
      setData(o);
      setOn(Object.fromEntries(o.features.map((f) => [f.id, f.enabled])));
    })();
  }, [getApiToken]);

  if (!data) return <p className="text-sm text-muted">Loading…</p>;
  const groups = [...new Set(data.features.map((f) => f.group))];
  const pct = Math.min(100, (data.parcels_per_day / 500) * 100);

  async function save() {
    setMsg(null);
    try {
      const t = await getApiToken();
      await withStaffStepUp(t, () =>
        settingsApi.updateConfig(t, "future_features", on, "Future features")
      );
      setMsg("Saved");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="max-w-3xl space-y-4">
      <div className="rounded-xl border border-primary/10 p-4">
        <div className="flex items-baseline justify-between text-sm">
          <span className="font-semibold text-primary">Volume</span>
          <span className="tabular-nums">{data.parcels_per_day} / 500 parcels a day</span>
        </div>
        <div className="mt-2 h-2 rounded-full bg-primary/10">
          <div className="h-2 rounded-full bg-primary" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-2 text-xs text-muted">
          Scoped, not built. Each switch stays off until volume passes its threshold and the feature
          ships; switching on records intent only.
        </p>
      </div>
      {groups.map((g) => (
        <div key={g} className="rounded-xl border border-primary/10 p-4">
          <p className="text-sm font-semibold text-primary">{g}</p>
          <ul className="mt-2 divide-y divide-primary/5">
            {data.features
              .filter((f) => f.group === g)
              .map((f) => (
                <li key={f.id} className="flex items-start justify-between gap-4 py-2.5">
                  <span>
                    <span className="block text-sm font-medium">{f.title}</span>
                    <span className="block text-xs text-muted">{f.description}</span>
                    <span className="text-[11px] text-muted">
                      Enable after {f.threshold} parcels/day {f.ready ? "· ready" : ""}
                    </span>
                  </span>
                  <input
                    type="checkbox"
                    aria-label={f.title}
                    className="mt-1 h-5 w-5 shrink-0"
                    checked={!!on[f.id]}
                    onChange={(e) => setOn({ ...on, [f.id]: e.target.checked })}
                  />
                </li>
              ))}
          </ul>
        </div>
      ))}
      <div className="flex items-center gap-3">
        <Button onClick={() => void save()}>Save</Button>
        {msg && <span className="text-xs text-muted">{msg}</span>}
      </div>
    </div>
  );
}
