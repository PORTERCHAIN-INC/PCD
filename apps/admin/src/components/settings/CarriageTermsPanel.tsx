"use client";

import { useEffect, useState } from "react";
import { Button, Input } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

type Terms = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// [section, key, label, unit] — cents are edited in dollars.
const FIELDS: Array<[string, string, string, "$" | "min" | "%" | "days"]> = [
  ["waiting", "pickup_included_minutes", "Pickup wait included", "min"],
  ["waiting", "stop_included_minutes", "Stop wait included", "min"],
  ["waiting", "cents_per_hour", "Waiting rate / hour", "$"],
  ["waiting", "increment_minutes", "Billing increment", "min"],
  ["failed_delivery", "van_pct", "Van return (of stop rate)", "%"],
  ["failed_delivery", "compact_pct", "Compact return (of stop rate)", "%"],
  ["failed_delivery", "compact_min_cents", "Compact return minimum", "$"],
  ["concierge", "past_designated_point_cents", "Past designated point", "$"],
  ["claims", "window_business_days", "Claim window", "days"],
];

export default function CarriageTermsPanel() {
  const { getApiToken } = useAdminAuth();
  const [terms, setTerms] = useState<Terms | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const cfg = (await settingsApi.config(await getApiToken())) as {
        config?: Record<string, unknown>;
      };
      setTerms((cfg.config?.carriage_terms as Terms) ?? {});
    })();
  }, [getApiToken]);

  if (!terms) return <p className="text-sm text-muted">Loading…</p>;

  const get = (s: string, k: string) => Number((terms[s] as Record<string, unknown>)?.[k] ?? 0);
  const set = (s: string, k: string, v: number) =>
    setTerms({ ...terms, [s]: { ...(terms[s] ?? {}), [k]: v } });

  async function save() {
    setMsg(null);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () =>
        settingsApi.updateConfig(token, "carriage_terms", terms, "Carriage terms")
      );
      setMsg("Saved");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        PorterChain&apos;s default Conditions of Carriage for every merchant. A merchant contract
        can override any value. Cargo coverage lives under Coverage.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {FIELDS.map(([s, k, label, unit]) => (
          <label key={`${s}.${k}`} className="text-xs text-muted">
            {label} ({unit})
            <Input
              type="number"
              min={0}
              step={unit === "$" ? 0.5 : 1}
              value={unit === "$" ? get(s, k) / 100 : get(s, k)}
              onChange={(e) =>
                set(
                  s,
                  k,
                  unit === "$" ? Math.round(Number(e.target.value) * 100) : Number(e.target.value)
                )
              }
            />
          </label>
        ))}
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={terms.liftgate_available !== false}
          onChange={(e) => setTerms({ ...terms, liftgate_available: e.target.checked })}
        />
        Liftgate trucks offered (off = liftgate requests need a quote)
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={Boolean(
            (terms.declarations as Record<string, unknown>)?.dangerous_goods_require_approval ??
            true
          )}
          onChange={(e) =>
            setTerms({
              ...terms,
              declarations: {
                ...(terms.declarations ?? {}),
                dangerous_goods_require_approval: e.target.checked,
              },
            })
          }
        />
        Dangerous goods need written approval before booking
      </label>
      <div className="flex items-center gap-3">
        <Button onClick={() => void save()}>Save</Button>
        {msg && <span className="text-xs text-muted">{msg}</span>}
      </div>
    </div>
  );
}
