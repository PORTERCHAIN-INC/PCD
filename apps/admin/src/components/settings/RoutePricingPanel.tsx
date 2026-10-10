"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from "react";
import { formatCents } from "@porterchain/ui/utils";
import { Button, Input } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { pricingApi, type SimulateQuoteResult } from "@/lib/pricing";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

type Cfg = Record<string, any>;
const VEHICLES = ["sedan_suv", "cargo_van", "sprinter_van", "box_16", "box_20"];
const MONEY: Array<[string, string]> = [
  ["base_cents", "Base"],
  ["minute_cents", "Per minute"],
  ["extra_drop_cents", "Extra drop"],
  ["extra_pickup_cents", "Extra pickup"],
  ["extra_parcel_cents", "Extra parcel"],
];

const pt = (v: string) =>
  /^[A-Za-z]\d[A-Za-z]/.test(v.trim())
    ? { postal: v.trim(), formatted: "" }
    : { formatted: v.trim() };

export default function RoutePricingPanel() {
  const { getApiToken } = useAdminAuth();
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [pickup, setPickup] = useState("L9T 1A1");
  const [drops, setDrops] = useState("L5M 1A1\nM5V 1A1");
  const [vehicle, setVehicle] = useState("cargo_van");
  const [preview, setPreview] = useState<SimulateQuoteResult | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    void (async () => {
      const c = (await settingsApi.config(await getApiToken())) as { config?: Cfg };
      setCfg((c.config?.smart_pricing as Cfg) ?? {});
    })();
  }, [getApiToken]);

  // Inline preview: current engine vs this draft, debounced on every edit.
  useEffect(() => {
    if (!cfg) return;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      const list = drops
        .split("\n")
        .map((d) => d.trim())
        .filter(Boolean);
      if (!pickup.trim() || !list.length) return;
      try {
        setPreview(
          await pricingApi.simulate(await getApiToken(), {
            vehicle_class: vehicle,
            pickup: pt(pickup),
            dropoff: pt(list[0]),
            extra_drops: list.slice(1).map(pt),
            total_drops: list.length,
            smart_overrides: cfg,
          })
        );
      } catch {
        setPreview(null);
      }
    }, 600);
  }, [cfg, pickup, drops, vehicle, getApiToken]);

  if (!cfg) return <p className="text-sm text-muted">Loading…</p>;
  const set = (k: string, v: unknown) => setCfg({ ...cfg, [k]: v });
  const setIn = (k: string, sub: string, v: unknown) =>
    setCfg({ ...cfg, [k]: { ...(cfg[k] ?? {}), [sub]: v } });
  const dollars = (c: number | undefined) => (c ?? 0) / 100;
  const cents = (v: string) => Math.round(Number(v) * 100);
  const curve: Array<{ from: number; cents: number }> = cfg.distance_curve ?? [];
  const unit = cfg.distance_unit ?? "km";

  async function save() {
    setMsg(null);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () =>
        settingsApi.updateConfig(token, "smart_pricing", cfg, "Route pricing")
      );
      setMsg("Saved");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  }

  const s = preview?.smart;
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <select
            className="rounded-lg border px-2 py-1"
            value={cfg.mode}
            onChange={(e) => set("mode", e.target.value)}
          >
            <option value="fsa">FSA → FSA</option>
            <option value="distance">Exact address distance</option>
          </select>
          <select
            className="rounded-lg border px-2 py-1"
            value={unit}
            onChange={(e) => set("distance_unit", e.target.value)}
          >
            <option value="km">km</option>
            <option value="mi">miles</option>
          </select>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!cfg.enabled}
              onChange={(e) => set("enabled", e.target.checked)}
            />
            Live for all merchants
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {MONEY.map(([k, label]) => (
            <label key={k} className="text-xs text-muted">
              {label} $
              <Input
                type="number"
                step={0.1}
                value={dollars(cfg[k])}
                onChange={(e) => set(k, cents(e.target.value))}
              />
            </label>
          ))}
        </div>

        <div>
          <p className="text-xs font-medium text-muted">
            Distance rate (per {unit}, from that point on)
          </p>
          <div className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {curve.map((b, i) => (
              <div key={i} className="flex items-center gap-1 text-xs">
                <Input
                  type="number"
                  value={b.from}
                  aria-label="from"
                  onChange={(e) =>
                    set(
                      "distance_curve",
                      curve.map((x, j) => (j === i ? { ...x, from: Number(e.target.value) } : x))
                    )
                  }
                />
                <span>→$</span>
                <Input
                  type="number"
                  step={0.05}
                  value={b.cents / 100}
                  aria-label="rate"
                  onChange={(e) =>
                    set(
                      "distance_curve",
                      curve.map((x, j) => (j === i ? { ...x, cents: cents(e.target.value) } : x))
                    )
                  }
                />
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <label className="text-xs text-muted">
            Return share %
            <Input
              type="number"
              value={Math.round((cfg.deadhead_share ?? 0) * 100)}
              onChange={(e) => set("deadhead_share", Number(e.target.value) / 100)}
            />
          </label>
          <label className="text-xs text-muted">
            Rush hour ×
            <Input
              type="number"
              step={0.05}
              value={cfg.peak?.factor ?? 1}
              onChange={(e) => setIn("peak", "factor", Number(e.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Downtown ×
            <Input
              type="number"
              step={0.05}
              value={cfg.downtown?.factor ?? 1}
              onChange={(e) => setIn("downtown", "factor", Number(e.target.value))}
            />
          </label>
          <label className="text-xs text-muted">
            Min margin over cost %
            <Input
              type="number"
              value={cfg.cost_floor_margin_pct ?? 0}
              onChange={(e) => set("cost_floor_margin_pct", Number(e.target.value))}
            />
          </label>
        </div>

        <table className="w-full text-xs">
          <thead className="text-muted">
            <tr>
              <th className="text-left font-medium">Vehicle</th>
              <th className="text-left font-medium">Price ×</th>
              <th className="text-left font-medium">Minimum $</th>
            </tr>
          </thead>
          <tbody>
            {VEHICLES.map((v) => (
              <tr key={v}>
                <td className="py-1">{v.replace("_", " ")}</td>
                <td className="pr-2">
                  <Input
                    type="number"
                    step={0.05}
                    value={cfg.vehicle_factor?.[v] ?? 1}
                    onChange={(e) => setIn("vehicle_factor", v, Number(e.target.value))}
                  />
                </td>
                <td>
                  <Input
                    type="number"
                    value={dollars(cfg.vehicle_minimum_cents?.[v])}
                    onChange={(e) => setIn("vehicle_minimum_cents", v, cents(e.target.value))}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex items-center gap-3">
          <Button onClick={() => void save()}>Save</Button>
          {msg && <span className="text-xs text-muted">{msg}</span>}
        </div>
      </div>

      <aside className="space-y-2 rounded-2xl border border-primary/10 p-4 text-sm">
        <p className="font-semibold text-primary">Preview</p>
        <Input value={pickup} onChange={(e) => setPickup(e.target.value)} aria-label="Pickup" />
        <textarea
          className="w-full rounded-lg border border-primary/15 p-2 text-sm"
          rows={3}
          value={drops}
          aria-label="Drops"
          onChange={(e) => setDrops(e.target.value)}
        />
        <select
          className="w-full rounded-lg border px-2 py-1"
          value={vehicle}
          onChange={(e) => setVehicle(e.target.value)}
        >
          {VEHICLES.map((v) => (
            <option key={v} value={v}>
              {v.replace("_", " ")}
            </option>
          ))}
        </select>
        {s && !s.error ? (
          <>
            <div className="grid grid-cols-2 gap-2 pt-2">
              <div className="rounded-lg bg-slate-50 p-2">
                <p className="text-xs text-muted">Current</p>
                <p className="text-lg font-semibold">{formatCents(s.current_cents ?? 0)}</p>
              </div>
              <div className="rounded-lg bg-emerald-50 p-2">
                <p className="text-xs text-muted">New</p>
                <p className="text-lg font-semibold">{formatCents(s.total_cents)}</p>
              </div>
            </div>
            <p className="text-xs text-muted">
              {s.route_distance} {s.unit} · {Math.round(s.drive_minutes)} min ·{" "}
              {s.sequence.join(" → ")} · {Math.round(s.confidence * 100)}% sure
            </p>
            <ul className="space-y-0.5 text-xs">
              {s.lines.map((l) => (
                <li key={l.code} className="flex justify-between">
                  <span className="truncate">{l.label}</span>
                  <span className="font-mono">{formatCents(l.cents)}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-xs text-muted">{s?.error ?? "Enter a pickup and drops."}</p>
        )}
      </aside>
    </div>
  );
}
