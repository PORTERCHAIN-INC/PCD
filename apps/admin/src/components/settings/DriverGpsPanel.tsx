"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, Input } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { drivers, type DriverRow } from "@/lib/drivers";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

type Gps = { enabled: boolean; disabled_driver_ids: string[] };

export default function DriverGpsPanel() {
  const { getApiToken } = useAdminAuth();
  const [gps, setGps] = useState<Gps | null>(null);
  const [rows, setRows] = useState<DriverRow[]>([]);
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const token = await getApiToken();
      const cfg = (await settingsApi.config(token)) as { config?: Record<string, unknown> };
      setGps((cfg.config?.driver_gps as Gps) ?? { enabled: true, disabled_driver_ids: [] });
      setRows(await drivers.list(token, {}).catch(() => []));
    })();
  }, [getApiToken]);

  const shown = useMemo(
    () => rows.filter((r) => r.full_name.toLowerCase().includes(q.toLowerCase())).slice(0, 50),
    [rows, q]
  );
  if (!gps) return <p className="text-sm text-muted">Loading…</p>;
  const off = new Set(gps.disabled_driver_ids);
  const toggle = (id: string) => {
    if (off.has(id)) off.delete(id);
    else off.add(id);
    setGps({ ...gps, disabled_driver_ids: [...off] });
  };

  async function save() {
    setMsg(null);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () =>
        settingsApi.updateConfig(token, "driver_gps", gps, "Driver GPS")
      );
      setMsg("Saved — takes effect now");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <label className="flex items-center justify-between rounded-xl border border-primary/10 p-4">
        <span>
          <span className="block font-semibold text-primary">Live driver GPS</span>
          <span className="text-xs text-muted">
            Off: apps stop sending location, Live map hides positions, customers see stop status and
            ETA only. Current pins are deleted on save; history ages out under GPS retention.
          </span>
        </span>
        <input
          type="checkbox"
          className="h-5 w-5"
          checked={gps.enabled}
          onChange={(e) => setGps({ ...gps, enabled: e.target.checked })}
        />
      </label>

      {gps.enabled && (
        <div className="rounded-xl border border-primary/10 p-4">
          <p className="text-sm font-semibold text-primary">Per driver</p>
          <Input
            className="mt-2"
            placeholder="Search drivers"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <ul className="mt-2 max-h-72 divide-y overflow-auto text-sm">
            {shown.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2">
                <span>{r.full_name}</span>
                <label className="flex items-center gap-2 text-xs text-muted">
                  {off.has(r.id) ? "GPS off" : "GPS on"}
                  <input type="checkbox" checked={!off.has(r.id)} onChange={() => toggle(r.id)} />
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button onClick={() => void save()}>Save</Button>
        {msg && <span className="text-xs text-muted">{msg}</span>}
      </div>
    </div>
  );
}
