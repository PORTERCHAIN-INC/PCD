"use client";

import MagicCard from "@/components/magic/MagicCard";
import Button from "@/components/ui/Button";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  confirmRouteImport,
  getRouteImport,
  patchOrderParcels,
  patchRouteImportStop,
  type RouteImportJob,
} from "@/lib/api";
import { formatCents } from "@/lib/booking";
import { VEHICLE_CHOICES } from "@/lib/route-module/allocateVehicle";
import Link from "next/link";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

type StopDraft = {
  sequence: number;
  stop_type: string;
  address: string;
  formatted: string;
  lat?: number | null;
  lng?: number | null;
  postal?: string;
  notes?: string;
  contact_name?: string;
  packages: ParcelDraft[];
};

type ParcelDraft = {
  id?: string;
  name: string;
  package_type: string;
  weight_kg: string;
  length_cm: string;
  width_cm: string;
  height_cm: string;
  notes: string;
};

export default function RouteJobDetail({ jobId }: { jobId: string }) {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [job, setJob] = useState<RouteImportJob | null>(null);
  const [stops, setStops] = useState<StopDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    const token = await getApiToken();
    const next = await getRouteImport(token, jobId, orgId);
    setJob(next);
    setStops(toDrafts(next.stops));
    setError(null);
  }, [getApiToken, isSignedIn, jobId, orgId]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "Could not load this route");
    });
  }, [isLoaded, isSignedIn, load]);

  const vehicleLabel = useMemo(() => {
    const id = job?.vehicle_class;
    return VEHICLE_CHOICES.find((item) => item.id === id)?.label || id || "Vehicle pending";
  }, [job?.vehicle_class]);

  const preview = job?.status !== "CONFIRMED" && job?.status !== "FAILED";
  const canEdit = Boolean(job?.parcel_amendable);
  const orderId = job?.order_id || job?.order_ids?.[0] || null;
  const statusLabel = job?.order_state
    ? job.order_state.replaceAll("_", " ")
    : job?.status === "PREVIEW"
      ? "Quoted"
      : job?.status || "";

  async function save() {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      const payload = stops.map(fromDraft);
      if (preview) {
        for (let i = 0; i < payload.length; i += 1) {
          await patchRouteImportStop(token, job.job_id, i, payload[i] ?? {}, orgId);
        }
      } else if (orderId) {
        await patchOrderParcels(
          token,
          orderId,
          { stops: payload, vehicle_class: job.vehicle_class || undefined },
          orgId
        );
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save parcels");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      if (canEdit) {
        const payload = stops.map(fromDraft);
        for (let i = 0; i < payload.length; i += 1) {
          await patchRouteImportStop(token, job.job_id, i, payload[i] ?? {}, orgId);
        }
      }
      await confirmRouteImport(token, job.job_id, orgId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm this route");
    } finally {
      setBusy(false);
    }
  }

  if (error && !job) return <p className="text-red-600">{error}</p>;
  if (!job) return <p className="text-muted">Loading route…</p>;

  return (
    <div className="mx-auto w-full min-w-0 max-w-5xl space-y-6">
      <div>
        <Link href="/routes" className="text-sm text-secondary hover:underline">
          ← Back to routes
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-primary sm:text-2xl">Route job</h1>
            <p className="mt-1 text-sm text-muted">
              {statusLabel}
              {job.scheduled_at ? ` · ${job.scheduled_at}` : ""} · {vehicleLabel}
            </p>
          </div>
          <div className="text-right">
            <p className="text-lg font-semibold text-primary">
              {job.quote?.amount_cents != null
                ? formatCents(job.quote.amount_cents)
                : "Quote pending"}
            </p>
            {orderId ? (
              <Link className="text-sm text-secondary hover:underline" href={`/orders/${orderId}`}>
                View order
              </Link>
            ) : null}
          </div>
        </div>
      </div>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {!canEdit && job.status === "CONFIRMED" ? (
        <p className="text-sm text-muted">
          Parcels are locked after a driver is assigned. Cancel this order and book again to change
          them.
        </p>
      ) : null}

      {stops.map((stop, stopIndex) => (
        <MagicCard
          key={`${stop.stop_type}-${stopIndex}`}
          className="space-y-4 p-4 sm:p-5"
          clip={false}
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
                {stop.stop_type === "pickup" ? "Pickup" : `Stop ${stopIndex}`}
              </p>
              {canEdit ? (
                <input
                  className="mt-1 w-full min-w-[16rem] rounded-xl border border-primary/15 px-3 py-2 text-sm"
                  value={stop.address}
                  onChange={(event) =>
                    setStops((current) =>
                      current.map((row, i) =>
                        i === stopIndex
                          ? { ...row, address: event.target.value, formatted: event.target.value }
                          : row
                      )
                    )
                  }
                />
              ) : (
                <p className="mt-1 font-medium text-primary">
                  {stop.formatted || stop.address || "—"}
                </p>
              )}
              {stop.contact_name ? (
                <p className="mt-1 text-xs text-muted">{stop.contact_name}</p>
              ) : null}
            </div>
            {canEdit ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  setStops((current) =>
                    current.map((row, i) =>
                      i === stopIndex ? { ...row, packages: [...row.packages, emptyParcel()] } : row
                    )
                  )
                }
              >
                Add parcel
              </Button>
            ) : null}
          </div>
          {canEdit ? (
            <label className="block text-sm font-medium text-primary">
              Notes
              <input
                className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm font-normal"
                value={stop.notes || ""}
                onChange={(event) =>
                  setStops((current) =>
                    current.map((row, i) =>
                      i === stopIndex ? { ...row, notes: event.target.value } : row
                    )
                  )
                }
              />
            </label>
          ) : stop.notes ? (
            <p className="text-sm text-muted">{stop.notes}</p>
          ) : null}
          <div className="space-y-3">
            {stop.packages.length === 0 ? (
              <p className="text-sm text-muted">No parcels on this stop.</p>
            ) : null}
            {stop.packages.map((parcel, parcelIndex) => (
              <div
                key={parcel.id || parcelIndex}
                className="rounded-xl border border-primary/10 p-3"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-xs font-bold uppercase tracking-wide text-muted">
                    Parcel {parcelIndex + 1}
                  </p>
                  {canEdit && stop.packages.length > 1 ? (
                    <button
                      type="button"
                      className="text-xs text-red-700"
                      onClick={() =>
                        setStops((current) =>
                          current.map((row, i) =>
                            i === stopIndex
                              ? {
                                  ...row,
                                  packages: row.packages.filter((_, j) => j !== parcelIndex),
                                }
                              : row
                          )
                        )
                      }
                    >
                      Remove
                    </button>
                  ) : null}
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Field
                    label="Name"
                    value={parcel.name}
                    disabled={!canEdit}
                    onChange={(value) =>
                      updateParcel(setStops, stopIndex, parcelIndex, { name: value })
                    }
                  />
                  <Field
                    label="Type"
                    value={parcel.package_type}
                    disabled={!canEdit}
                    onChange={(value) =>
                      updateParcel(setStops, stopIndex, parcelIndex, { package_type: value })
                    }
                  />
                  <Field
                    label="Weight (kg)"
                    value={parcel.weight_kg}
                    disabled={!canEdit}
                    onChange={(value) =>
                      updateParcel(setStops, stopIndex, parcelIndex, { weight_kg: value })
                    }
                  />
                  <Field
                    label="Notes"
                    value={parcel.notes}
                    disabled={!canEdit}
                    onChange={(value) =>
                      updateParcel(setStops, stopIndex, parcelIndex, { notes: value })
                    }
                  />
                  <Field
                    label="Length (cm)"
                    value={parcel.length_cm}
                    disabled={!canEdit}
                    onChange={(value) =>
                      updateParcel(setStops, stopIndex, parcelIndex, { length_cm: value })
                    }
                  />
                  <Field
                    label="Width (cm)"
                    value={parcel.width_cm}
                    disabled={!canEdit}
                    onChange={(value) =>
                      updateParcel(setStops, stopIndex, parcelIndex, { width_cm: value })
                    }
                  />
                  <Field
                    label="Height (cm)"
                    value={parcel.height_cm}
                    disabled={!canEdit}
                    onChange={(value) =>
                      updateParcel(setStops, stopIndex, parcelIndex, { height_cm: value })
                    }
                  />
                </div>
              </div>
            ))}
          </div>
        </MagicCard>
      ))}

      {job.quote?.line_items?.length ? (
        <MagicCard className="p-4 sm:p-5" clip={false}>
          <h2 className="text-sm font-semibold text-primary">Quote</h2>
          <ul className="mt-3 space-y-1 text-sm">
            {job.quote.line_items.map((item) => (
              <li key={item.code} className="flex justify-between gap-3">
                <span>{item.label}</span>
                <span className="tabular-nums">{formatCents(item.amount_cents)}</span>
              </li>
            ))}
          </ul>
        </MagicCard>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {canEdit ? (
          <Button type="button" disabled={busy} onClick={() => void save()}>
            {busy ? "Saving…" : "Save and re-quote"}
          </Button>
        ) : null}
        {preview ? (
          <Button type="button" variant="outline" disabled={busy} onClick={() => void confirm()}>
            Confirm route
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs font-medium text-primary">
      {label}
      <input
        className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm font-normal disabled:bg-gray-bg"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function emptyParcel(): ParcelDraft {
  return {
    name: "Parcel",
    package_type: "looseParcel",
    weight_kg: "",
    length_cm: "",
    width_cm: "",
    height_cm: "",
    notes: "",
  };
}

function toDrafts(stops: Array<Record<string, unknown>>): StopDraft[] {
  return stops.map((stop, index) => {
    const packages = Array.isArray(stop.packages) ? stop.packages : [];
    return {
      sequence: Number(stop.sequence || index + 1),
      stop_type: String(stop.stop_type || (index === 0 ? "pickup" : "drop")),
      address: String(stop.address || stop.formatted || ""),
      formatted: String(stop.formatted || stop.address || ""),
      lat: typeof stop.lat === "number" ? stop.lat : null,
      lng: typeof stop.lng === "number" ? stop.lng : null,
      postal: stop.postal ? String(stop.postal) : undefined,
      notes: stop.notes ? String(stop.notes) : "",
      contact_name: stop.contact_name ? String(stop.contact_name) : undefined,
      packages: packages
        .filter((pkg): pkg is Record<string, unknown> => Boolean(pkg) && typeof pkg === "object")
        .map((pkg) => ({
          id: pkg.id ? String(pkg.id) : undefined,
          name: String(pkg.name || pkg.sku || "Parcel"),
          package_type: String(pkg.package_type || "looseParcel"),
          weight_kg: pkg.weight_kg == null ? "" : String(pkg.weight_kg),
          length_cm: pkg.length_cm == null ? "" : String(pkg.length_cm),
          width_cm: pkg.width_cm == null ? "" : String(pkg.width_cm),
          height_cm: pkg.height_cm == null ? "" : String(pkg.height_cm),
          notes: pkg.notes ? String(pkg.notes) : "",
        })),
    };
  });
}

function fromDraft(stop: StopDraft): Record<string, unknown> {
  return {
    sequence: stop.sequence,
    stop_type: stop.stop_type,
    address: stop.address,
    formatted: stop.formatted || stop.address,
    lat: stop.lat,
    lng: stop.lng,
    postal: stop.postal,
    notes: stop.notes || undefined,
    contact_name: stop.contact_name,
    packages: stop.packages.map((parcel) => ({
      id: parcel.id,
      name: parcel.name,
      package_type: parcel.package_type || undefined,
      weight_kg: num(parcel.weight_kg),
      length_cm: num(parcel.length_cm),
      width_cm: num(parcel.width_cm),
      height_cm: num(parcel.height_cm),
      notes: parcel.notes || undefined,
    })),
  };
}

function num(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function updateParcel(
  setStops: Dispatch<SetStateAction<StopDraft[]>>,
  stopIndex: number,
  parcelIndex: number,
  patch: Partial<ParcelDraft>
) {
  setStops((current) =>
    current.map((stop, i) =>
      i === stopIndex
        ? {
            ...stop,
            packages: stop.packages.map((parcel, j) =>
              j === parcelIndex ? { ...parcel, ...patch } : parcel
            ),
          }
        : stop
    )
  );
}
