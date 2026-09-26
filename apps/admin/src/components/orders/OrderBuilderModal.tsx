"use client";

import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { adminFetch } from "@/lib/api";
import { merchants, type MerchantRow } from "@/lib/merchants";
import { Badge, Button, Drawer, Select } from "@/components/crm/primitives";
import { DateTimeField, parseDateString } from "@porterchain/ui/date-fields";

export type OrderKind = "single" | "hub_spoke" | "multi_pickup_delivery" | "scheduled_pickup";

type StopDraft = {
  key: string;
  type: "pickup" | "dropoff";
  formatted: string;
  lat: string;
  lng: string;
  time_window_start: string;
  time_window_end: string;
  service_time_minutes: string;
  notes: string;
};

const KINDS: { id: OrderKind; label: string; hint: string }[] = [
  { id: "single", label: "Single P→D", hint: "One pickup, one delivery" },
  { id: "hub_spoke", label: "Hub & spoke", hint: "One pickup, many deliveries" },
  { id: "multi_pickup_delivery", label: "Multi P/D", hint: "Multiple pickups and deliveries" },
  { id: "scheduled_pickup", label: "Scheduled pickup", hint: "Merchant appointment window" },
];

function seedStops(kind: OrderKind): StopDraft[] {
  const base = (type: "pickup" | "dropoff", n: number): StopDraft => ({
    key: `${type}-${n}-${Math.random().toString(36).slice(2, 7)}`,
    type,
    formatted: "",
    lat: "",
    lng: "",
    time_window_start: "",
    time_window_end: "",
    service_time_minutes: "",
    notes: "",
  });
  if (kind === "hub_spoke") return [base("pickup", 0), base("dropoff", 1), base("dropoff", 2)];
  if (kind === "multi_pickup_delivery") {
    return [base("pickup", 0), base("pickup", 1), base("dropoff", 2), base("dropoff", 3)];
  }
  return [base("pickup", 0), base("dropoff", 1)];
}

function defaultSchedule(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export type OrderBuilderPrefill = {
  title?: string;
  merchant_id?: string | null;
  vehicle_class?: string | null;
  special_instructions?: string | null;
  stops?: Array<{
    type: "pickup" | "dropoff";
    formatted: string;
    lat?: string;
    lng?: string;
    notes?: string;
  }>;
};

function stopDraftFromPrefill(stops: NonNullable<OrderBuilderPrefill["stops"]>): StopDraft[] {
  return stops.map((s, i) => ({
    key: `${s.type}-${i}-${Math.random().toString(36).slice(2, 7)}`,
    type: s.type,
    formatted: s.formatted,
    lat: s.lat ?? "",
    lng: s.lng ?? "",
    time_window_start: "",
    time_window_end: "",
    service_time_minutes: "",
    notes: s.notes ?? "",
  }));
}

export function OrderBuilderModal({
  open,
  onClose,
  onCreated,
  prefill,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (orderId: string) => void;
  prefill?: OrderBuilderPrefill | null;
}) {
  const { getApiToken } = useAdminAuth();
  const [kind, setKind] = useState<OrderKind>("single");
  const [stops, setStops] = useState<StopDraft[]>(() => seedStops("single"));
  const [merchantId, setMerchantId] = useState("");
  const [merchantList, setMerchantList] = useState<MerchantRow[]>([]);
  const [vehicleClass, setVehicleClass] = useState("cargo_van");
  const [scheduledAt, setScheduledAt] = useState(defaultSchedule);
  const [instructions, setInstructions] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setKind("single");
    setScheduledAt(defaultSchedule());
    setError(null);
    setBusy(false);
    if (prefill?.stops?.length) {
      setStops(stopDraftFromPrefill(prefill.stops));
    } else {
      setStops(seedStops("single"));
    }
    setMerchantId(prefill?.merchant_id?.trim() || "");
    setVehicleClass(prefill?.vehicle_class?.trim() || "cargo_van");
    setInstructions(prefill?.special_instructions?.trim() || "");
  }, [open, prefill]);

  useEffect(() => {
    if (!open) return;
    void (async () => {
      try {
        const token = await getApiToken();
        const rows = await merchants.list(token, { status: "ACTIVE" });
        setMerchantList(rows);
        setMerchantId((current) => current || rows[0]?.id || "");
      } catch {
        /* list failure surfaces on submit */
      }
    })();
  }, [open, getApiToken]);

  function changeKind(next: OrderKind) {
    setKind(next);
    setStops(seedStops(next));
  }

  function updateStop(key: string, patch: Partial<StopDraft>) {
    setStops((prev) => prev.map((s) => (s.key === key ? { ...s, ...patch } : s)));
  }

  function moveStop(index: number, dir: -1 | 1) {
    setStops((prev) => {
      const next = [...prev];
      const j = index + dir;
      if (j < 0 || j >= next.length) return prev;
      [next[index], next[j]] = [next[j], next[index]];
      return next;
    });
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      const body = {
        merchant_id: merchantId,
        order_kind: kind,
        vehicle_class: vehicleClass,
        package_type: "looseParcel",
        scheduled_at: new Date(scheduledAt).toISOString(),
        schedule_mode: kind === "scheduled_pickup" ? "later" : "now",
        special_instructions: instructions || null,
        stops: stops.map((s, i) => ({
          type: s.type,
          sequence: i,
          formatted: s.formatted.trim(),
          lat: s.lat ? Number(s.lat) : null,
          lng: s.lng ? Number(s.lng) : null,
          time_window_start: s.time_window_start
            ? new Date(s.time_window_start).toISOString()
            : null,
          time_window_end: s.time_window_end ? new Date(s.time_window_end).toISOString() : null,
          service_time_seconds: s.service_time_minutes
            ? Math.round(Number(s.service_time_minutes) * 60)
            : null,
          notes: s.notes || null,
        })),
      };
      const result = await adminFetch<{ order_id: string; tracking_number: string }>(
        "/v1/admin/orders",
        token,
        { method: "POST", body: JSON.stringify(body) }
      );
      onCreated(result.order_id);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width="max-w-2xl"
      title={prefill?.title ?? "Create multi-stop order"}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => void submit()} disabled={busy || !merchantId}>
            {busy ? "Creating…" : "Create & dispatch-ready"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
            Order type
          </p>
          <div className="grid grid-cols-2 gap-2">
            {KINDS.map((k) => (
              <button
                key={k.id}
                type="button"
                onClick={() => changeKind(k.id)}
                className={
                  kind === k.id
                    ? "rounded-xl border border-secondary bg-secondary/10 px-3 py-2 text-left"
                    : "rounded-xl border border-primary/10 px-3 py-2 text-left hover:bg-gray-bg"
                }
              >
                <p className="text-sm font-medium text-primary">{k.label}</p>
                <p className="text-[11px] text-muted">{k.hint}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-xs font-medium text-muted">Merchant</span>
            <Select
              value={merchantId}
              onChange={(e) => setMerchantId(e.target.value)}
              className="mt-1 w-full"
            >
              <option value="">Select…</option>
              {merchantList.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.company_name}
                </option>
              ))}
            </Select>
          </label>
          <label className="block text-sm">
            <span className="text-xs font-medium text-muted">Vehicle</span>
            <Select
              value={vehicleClass}
              onChange={(e) => setVehicleClass(e.target.value)}
              className="mt-1 w-full"
            >
              <option value="sedan_suv">Sedan / SUV</option>
              <option value="pickup">Pickup</option>
              <option value="cargo_van">Cargo van</option>
              <option value="sprinter_van">Sprinter / high-roof</option>
              <option value="box_16">16 ft</option>
              <option value="box_20">20 ft</option>
            </Select>
          </label>
          <div className="sm:col-span-2">
            <DateTimeField
              label="Scheduled at"
              value={scheduledAt}
              onChange={setScheduledAt}
              hourFormat={12}
              timeInterval={15}
            />
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Stops · {stops.length}
            </p>
            <Button
              variant="outline"
              className="px-2 py-1 text-xs"
              onClick={() =>
                setStops((prev) => [
                  ...prev,
                  {
                    key: `stop-${Date.now()}`,
                    type: "dropoff",
                    formatted: "",
                    lat: "",
                    lng: "",
                    time_window_start: "",
                    time_window_end: "",
                    service_time_minutes: "",
                    notes: "",
                  },
                ])
              }
            >
              <Plus className="h-3.5 w-3.5" /> Add stop
            </Button>
          </div>

          <div className="space-y-3">
            {stops.map((s, i) => (
              <div key={s.key} className="rounded-xl border border-primary/10 p-3">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge tone={s.type === "pickup" ? "green" : "red"}>
                    {i + 1}. {s.type}
                  </Badge>
                  <Select
                    value={s.type}
                    onChange={(e) =>
                      updateStop(s.key, { type: e.target.value as "pickup" | "dropoff" })
                    }
                    className="w-28"
                  >
                    <option value="pickup">Pickup</option>
                    <option value="dropoff">Dropoff</option>
                  </Select>
                  <div className="ml-auto flex gap-1">
                    <button
                      type="button"
                      className="rounded p-1 text-muted hover:bg-gray-bg"
                      onClick={() => moveStop(i, -1)}
                      title="Move up"
                    >
                      <ArrowUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      className="rounded p-1 text-muted hover:bg-gray-bg"
                      onClick={() => moveStop(i, 1)}
                      title="Move down"
                    >
                      <ArrowDown className="h-3.5 w-3.5" />
                    </button>
                    {stops.length > 2 && (
                      <button
                        type="button"
                        className="rounded p-1 text-red-600 hover:bg-red-50"
                        onClick={() => setStops((prev) => prev.filter((x) => x.key !== s.key))}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
                <input
                  value={s.formatted}
                  onChange={(e) => updateStop(s.key, { formatted: e.target.value })}
                  placeholder="Address"
                  className="mb-2 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm outline-none focus:border-secondary"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={s.lat}
                    onChange={(e) => updateStop(s.key, { lat: e.target.value })}
                    placeholder="Lat"
                    className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs outline-none focus:border-secondary"
                  />
                  <input
                    value={s.lng}
                    onChange={(e) => updateStop(s.key, { lng: e.target.value })}
                    placeholder="Lng"
                    className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs outline-none focus:border-secondary"
                  />
                  <div className="col-span-2">
                    <DateTimeField
                      label="Window start"
                      value={s.time_window_start}
                      onChange={(value) => updateStop(s.key, { time_window_start: value })}
                      hourFormat={12}
                      timeInterval={15}
                    />
                  </div>
                  <div className="col-span-2">
                    <DateTimeField
                      label="Window end"
                      value={s.time_window_end}
                      onChange={(value) => updateStop(s.key, { time_window_end: value })}
                      hourFormat={12}
                      timeInterval={15}
                      minDate={parseDateString(s.time_window_start)}
                    />
                  </div>
                  <input
                    value={s.service_time_minutes}
                    onChange={(e) => updateStop(s.key, { service_time_minutes: e.target.value })}
                    placeholder="Service min"
                    className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs outline-none focus:border-secondary"
                  />
                  <input
                    value={s.notes}
                    onChange={(e) => updateStop(s.key, { notes: e.target.value })}
                    placeholder="Stop notes"
                    className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs outline-none focus:border-secondary"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <label className="block text-sm">
          <span className="text-xs font-medium text-muted">Special instructions</span>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={2}
            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm outline-none focus:border-secondary"
          />
        </label>
      </div>
    </Drawer>
  );
}
