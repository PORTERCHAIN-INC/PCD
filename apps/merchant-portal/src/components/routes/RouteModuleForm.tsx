"use client";

import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { confirmRouteImport, createRouteImport, type RouteImportJob } from "@/lib/api";
import { billingApi, formatCycle, formatTerms, type BillingOverview } from "@/lib/billing";
import { formatCents, listSavedAddresses } from "@/lib/booking";
import { publicEnv } from "@/lib/env";
import { ordersApi } from "@/lib/orders";
import {
  allocateVehicle,
  VEHICLE_CHOICES,
  type VehicleRequest,
} from "@/lib/route-module/allocateVehicle";
import { parseRouteCsv, routeCsvTemplate, type RouteCsvError } from "@/lib/route-module/csv";
import { BulkErrorReport } from "@/components/bulk/BulkUploadReport";
import { QuoteLines } from "@/components/billing/QuoteLines";
import {
  DimensionUnit,
  RouteJobStatus,
  WeightUnit,
  type Parcel,
  type PickupLocation,
  type RouteJob,
  type RouteStop,
} from "@/lib/route-module/types";
import { sumActualWeightKg, withVolumetricWeight } from "@/lib/route-module/units";
import { toRouteImportPayload, validateRouteJob } from "@/lib/route-module/toRouteImport";
import MagicCard from "@/components/magic/MagicCard";
import ShimmerButton from "@/components/magic/ShimmerButton";
import Button from "@/components/ui/Button";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { DateTimePickerSeparateField } from "@porterchain/ui/datetime-picker-separate";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function emptyParcel(unitSystem: "imperial" | "metric", id = newId()): Parcel {
  return withVolumetricWeight({
    id,
    length: 0,
    width: 0,
    height: 0,
    dimensionsUnit: unitSystem === "imperial" ? DimensionUnit.IN : DimensionUnit.CM,
    weight: 0,
    weightUnit: unitSystem === "imperial" ? WeightUnit.LBS : WeightUnit.KG,
  });
}

function emptyStop(
  sequence: number,
  unitSystem: "imperial" | "metric",
  id = newId(),
  parcelId = newId()
): RouteStop {
  return {
    id,
    stopSequence: sequence,
    formattedAddress: "",
    postalCode: "",
    customerName: "",
    parcels: [emptyParcel(unitSystem, parcelId)],
  };
}

function emptyPickup(): PickupLocation {
  return { formattedAddress: "" };
}

function addressFromBooking(
  address: BookingAddress
): Pick<PickupLocation, "formattedAddress" | "latitude" | "longitude"> {
  return {
    formattedAddress: address.formatted,
    latitude: address.lat,
    longitude: address.lng,
  };
}

const inputClass = "w-full rounded-xl border border-primary/15 px-3 py-2 text-sm";

export default function RouteModuleForm({
  onConfirmed,
  showTitle = true,
}: {
  onConfirmed?: () => void;
  showTitle?: boolean;
}) {
  const { getApiToken, orgId } = useMerchantAuth();
  const [routeId] = useState("route-draft");
  const [pickup, setPickup] = useState<PickupLocation>(emptyPickup);
  const [stops, setStops] = useState<RouteStop[]>([emptyStop(1, "metric", "stop-1", "parcel-1")]);
  const [scheduleMode, setScheduleMode] = useState<"now" | "later">("now");
  const [scheduledAt, setScheduledAt] = useState("");
  const [timezone, setTimezone] = useState("America/Toronto");
  const [internalReference, setInternalReference] = useState("");
  const [vehicleRequest, setVehicleRequest] = useState<VehicleRequest>("auto");
  const [constructionSite, setConstructionSite] = useState(false);
  const [siteAccessNotes, setSiteAccessNotes] = useState("");
  const [unitSystem, setUnitSystem] = useState<"metric" | "imperial">("metric");
  const csvInputRef = useRef<HTMLInputElement>(null);
  const [csvErrors, setCsvErrors] = useState<RouteCsvError[]>([]);
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [quote, setQuote] = useState<RouteImportJob | null>(null);
  const [quotedFingerprint, setQuotedFingerprint] = useState<string | null>(null);
  const [confirmResult, setConfirmResult] = useState<{
    orderId: string;
    amountCents?: number;
    trackingNumber?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const token = await getApiToken();
        const [overview, addrs] = await Promise.all([
          billingApi.overview(token, orgId),
          listSavedAddresses(token, orgId),
        ]);
        if (cancelled) return;
        setBilling(overview);
        const def = addrs.find((a) => a.is_default) ?? addrs[0];
        if (def?.formatted) {
          setPickup((prev) =>
            prev.formattedAddress
              ? prev
              : {
                  formattedAddress: def.formatted,
                  latitude: def.lat ?? undefined,
                  longitude: def.lng ?? undefined,
                  postalCode: def.postal ?? undefined,
                }
          );
        }
      } catch {
        if (!cancelled) setBilling(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getApiToken, orgId]);

  const parcels = useMemo(() => stops.flatMap((stop) => stop.parcels), [stops]);
  const allocation = useMemo(
    () => allocateVehicle(parcels, { requested: vehicleRequest, constructionSite }),
    [constructionSite, parcels, vehicleRequest]
  );
  const totalWeightKg = useMemo(() => sumActualWeightKg(parcels), [parcels]);

  const job: RouteJob = useMemo(
    () => ({
      routeId,
      merchantId: orgId,
      pickupLocation: pickup,
      stops: stops.map((stop, index) => ({ ...stop, stopSequence: index + 1 })),
      assignedVehicleClass: allocation.vehicleClass,
      totalRouteWeightKg: totalWeightKg,
      status: RouteJobStatus.DRAFT,
      scheduledAt: scheduleMode === "later" ? scheduledAt || undefined : undefined,
      internalReference: internalReference || undefined,
      constructionSite,
      siteAccessNotes,
      requiresLiftgate: constructionSite,
    }),
    [
      allocation.vehicleClass,
      constructionSite,
      internalReference,
      orgId,
      pickup,
      routeId,
      scheduleMode,
      scheduledAt,
      siteAccessNotes,
      stops,
      totalWeightKg,
    ]
  );

  const fingerprint = useMemo(() => {
    try {
      return JSON.stringify(toRouteImportPayload(job));
    } catch {
      return "";
    }
  }, [job]);
  const quoteStale = quote != null && quotedFingerprint !== fingerprint;
  const validation = useMemo(() => validateRouteJob(job), [job]);

  function applyUnitSystem(next: "metric" | "imperial") {
    setUnitSystem(next);
    setStops((current) =>
      current.map((stop) => ({
        ...stop,
        parcels: stop.parcels.map((parcel) =>
          withVolumetricWeight({
            ...parcel,
            dimensionsUnit: next === "imperial" ? DimensionUnit.IN : DimensionUnit.CM,
            weightUnit: next === "imperial" ? WeightUnit.LBS : WeightUnit.KG,
          })
        ),
      }))
    );
  }

  function updateStop(index: number, patch: Partial<RouteStop>) {
    setStops((current) => current.map((stop, i) => (i === index ? { ...stop, ...patch } : stop)));
  }

  function updateParcel(stopIndex: number, parcelIndex: number, patch: Partial<Parcel>) {
    setStops((current) =>
      current.map((stop, i) => {
        if (i !== stopIndex) return stop;
        return {
          ...stop,
          parcels: stop.parcels.map((parcel, j) =>
            j === parcelIndex ? withVolumetricWeight({ ...parcel, ...patch }) : parcel
          ),
        };
      })
    );
  }

  function moveStop(index: number, direction: -1 | 1) {
    setStops((current) => {
      const next = [...current];
      const target = index + direction;
      if (target < 0 || target >= next.length) return current;
      const [row] = next.splice(index, 1);
      next.splice(target, 0, row);
      return next;
    });
  }

  function downloadCsvTemplate() {
    const blob = new Blob([routeCsvTemplate()], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "route-planner-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function importCsv(file: File) {
    setError(null);
    setCsvErrors([]);
    const text = await file.text();
    const result = parseRouteCsv(text);
    if (!result.ok) {
      setCsvErrors(result.errors);
      return;
    }
    setPickup(result.route.pickup);
    setStops(result.route.stops);
    setConstructionSite(result.route.constructionSite);
    setSiteAccessNotes(result.route.siteAccessNotes);
    setInternalReference(result.route.internalReference);
    if (result.route.vehicleClass) setVehicleRequest(result.route.vehicleClass as VehicleRequest);
    if (result.route.scheduledAt) {
      setScheduleMode("later");
      setScheduledAt(result.route.scheduledAt);
    }
    setQuote(null);
    setQuotedFingerprint(null);
  }

  async function requestQuote() {
    setError(null);
    setCsvErrors([]);
    setConfirmResult(null);
    if (scheduleMode === "later" && !scheduledAt) {
      setError("Pick a pickup date and time");
      return;
    }
    if (!validation.ok) {
      setError(validation.errors[0] ?? "Route is incomplete");
      return;
    }
    if (allocation.blocked) {
      setError(allocation.message);
      return;
    }
    setQuoting(true);
    try {
      const token = await getApiToken();
      const payload = toRouteImportPayload(job);
      const jobResult = await createRouteImport(token, payload, orgId);
      if (!jobResult.quote?.amount_cents && jobResult.quote?.amount_cents !== 0) {
        setCsvErrors(jobResult.errors as RouteCsvError[]);
        setError(
          jobResult.errors.length
            ? "Quote unavailable until every stop can be located. Fix the rows below."
            : "Quote unavailable until every stop can be located"
        );
        setQuote(jobResult);
        setQuotedFingerprint(null);
        return;
      }
      setQuote(jobResult);
      setQuotedFingerprint(fingerprint);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not quote this route");
    } finally {
      setQuoting(false);
    }
  }

  async function confirmRoute() {
    if (!quote || quoteStale || allocation.blocked) return;
    setConfirming(true);
    setError(null);
    try {
      const token = await getApiToken();
      const confirmed = await confirmRouteImport(token, quote.job_id, orgId);
      const orderId = confirmed.order_ids[0];
      if (!orderId) {
        setError("Route confirmed but no order id was returned");
        return;
      }
      let amountCents: number | undefined;
      let trackingNumber: string | undefined;
      try {
        const detail = await ordersApi.detail360(token, orderId, orgId);
        amountCents = detail.amount_cents;
        trackingNumber = detail.tracking_number;
      } catch {
        amountCents = quote.quote?.amount_cents;
      }
      setConfirmResult({ orderId, amountCents, trackingNumber });
      onConfirmed?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm this route");
    } finally {
      setConfirming(false);
    }
  }

  const quotedAmount = quote?.quote?.amount_cents;

  return (
    <div className="space-y-6">
      {showTitle ? (
        <div>
          <h1 className="text-2xl font-semibold text-primary">Route planner</h1>
          <p className="mt-1 text-sm text-muted">
            One pickup, multiple Ontario stops, and a parcel on each stop. Confirming creates one
            billable order on your existing statement. Upload a CSV using the same columns as this
            form. Repeat the sequence to put more than one parcel on a stop.
          </p>
        </div>
      ) : null}

      {billing ? (
        <p className="rounded-xl border border-primary/10 bg-gray-bg px-4 py-3 text-sm text-primary">
          {formatTerms(billing.payment_terms)}
          {billing.net_terms_days ? ` · Net ${billing.net_terms_days}` : ""} ·{" "}
          {formatCycle(billing.billing_cycle)}
          {billing.contract_pricing.has_contract && billing.contract_pricing.contract_name
            ? ` · ${billing.contract_pricing.contract_name}`
            : ""}
        </p>
      ) : null}

      <MagicCard className="p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
              01 · Units
            </p>
            <h2 className="mt-1 text-sm font-semibold text-primary">Units for this route</h2>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant={unitSystem === "metric" ? "primary" : "outline"}
              onClick={() => applyUnitSystem("metric")}
            >
              Metric
            </Button>
            <Button
              type="button"
              size="sm"
              variant={unitSystem === "imperial" ? "primary" : "outline"}
              onClick={() => applyUnitSystem("imperial")}
            >
              Imperial
            </Button>
          </div>
        </div>
        <p className="mt-2 text-xs text-muted">
          Sets every parcel to{" "}
          {unitSystem === "imperial" ? "inches and pounds" : "centimetres and kilograms"}. You can
          still change a single parcel after that.
        </p>
      </MagicCard>

      <MagicCard className="space-y-3 p-4 sm:p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-secondary">02 · Vehicle</p>
        <label className="block text-sm font-medium text-primary">
          Vehicle
          <select
            className={`${inputClass} mt-1`}
            value={vehicleRequest}
            onChange={(event) => setVehicleRequest(event.target.value as VehicleRequest)}
          >
            <option value="auto">Recommended from parcel size and weight</option>
            {VEHICLE_CHOICES.map((vehicle) => (
              <option key={vehicle.id} value={vehicle.id}>
                {vehicle.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-start gap-2 text-sm text-primary">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 rounded border-primary/20"
            checked={constructionSite}
            onChange={(event) => setConstructionSite(event.target.checked)}
          />
          Delivery area is a construction site
        </label>
        {constructionSite ? (
          <label className="block text-sm font-medium text-primary">
            Site access
            <textarea
              className={`${inputClass} mt-1`}
              rows={2}
              value={siteAccessNotes}
              onChange={(event) => setSiteAccessNotes(event.target.value)}
              placeholder="Gate code, foreman, dock, liftgate instructions"
            />
          </label>
        ) : null}
        <p className="text-xs text-muted">
          A sedan is assigned only when every parcel fits a trunk. Construction sites use a cargo
          van or larger and add the liftgate charge already used on booking.
        </p>
      </MagicCard>

      <AllocationBanner
        blocked={allocation.blocked}
        label={allocation.vehicleLabel}
        message={allocation.message}
        stale={quoteStale}
      />

      <MagicCard className="space-y-3 p-4 sm:p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-secondary">03 · Pickup</p>
        <h2 className="text-sm font-semibold text-primary">Pickup</h2>
        <AddressField
          id="route-pickup"
          label="Pickup address"
          value={{
            formatted: pickup.formattedAddress,
            lat: pickup.latitude,
            lng: pickup.longitude,
          }}
          onChange={(address) =>
            setPickup((current) => ({ ...current, ...addressFromBooking(address) }))
          }
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-medium text-primary">
            Unit
            <input
              className={`${inputClass} mt-1`}
              value={pickup.unit ?? ""}
              onChange={(event) =>
                setPickup((current) => ({ ...current, unit: event.target.value }))
              }
            />
          </label>
          <label className="text-sm font-medium text-primary">
            Postal code
            <input
              className={`${inputClass} mt-1`}
              value={pickup.postalCode ?? ""}
              onChange={(event) =>
                setPickup((current) => ({ ...current, postalCode: event.target.value }))
              }
            />
          </label>
        </div>
      </MagicCard>

      <div className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-secondary">04 · Stops</p>
        {stops.map((stop, index) => (
          <MagicCard key={stop.id} className="space-y-3 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-primary">Stop {index + 1}</h2>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => moveStop(index, -1)}
                >
                  Up
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => moveStop(index, 1)}
                >
                  Down
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => setStops((current) => current.filter((_, i) => i !== index))}
                  disabled={stops.length === 1}
                >
                  Remove stop
                </Button>
              </div>
            </div>
            <AddressField
              id={`stop-${stop.id}`}
              label="Delivery address"
              value={{
                formatted: stop.formattedAddress,
                lat: stop.latitude,
                lng: stop.longitude,
              }}
              onChange={(address) => updateStop(index, addressFromBooking(address))}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Field
                label="Customer name"
                value={stop.customerName}
                onChange={(customerName) => updateStop(index, { customerName })}
              />
              <Field
                label="Ontario postal code"
                value={stop.postalCode}
                onChange={(postalCode) => updateStop(index, { postalCode })}
              />
              <Field
                label="Phone"
                value={stop.customerPhone ?? ""}
                onChange={(customerPhone) => updateStop(index, { customerPhone })}
              />
              <Field
                label="Email"
                value={stop.customerEmail ?? ""}
                onChange={(customerEmail) => updateStop(index, { customerEmail })}
              />
            </div>
            <label className="block text-sm font-medium text-primary">
              Delivery notes
              <textarea
                className={`${inputClass} mt-1`}
                rows={2}
                value={stop.deliveryNotes ?? ""}
                onChange={(event) => updateStop(index, { deliveryNotes: event.target.value })}
                placeholder="Gate code, suite, dock"
              />
            </label>
            <div className="space-y-3">
              {stop.parcels.map((parcel, parcelIndex) => (
                <div key={parcel.id} className="rounded-xl bg-gray-bg p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm font-medium text-primary">Parcel {parcelIndex + 1}</p>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        updateStop(index, {
                          parcels: stop.parcels.filter((_, j) => j !== parcelIndex),
                        })
                      }
                      disabled={stop.parcels.length === 1}
                    >
                      Remove
                    </Button>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-4">
                    <NumberField
                      label="Length"
                      value={parcel.length}
                      onChange={(length) => updateParcel(index, parcelIndex, { length })}
                    />
                    <NumberField
                      label="Width"
                      value={parcel.width}
                      onChange={(width) => updateParcel(index, parcelIndex, { width })}
                    />
                    <NumberField
                      label="Height"
                      value={parcel.height}
                      onChange={(height) => updateParcel(index, parcelIndex, { height })}
                    />
                    <label className="text-sm font-medium text-primary">
                      Unit
                      <select
                        className={`${inputClass} mt-1`}
                        value={parcel.dimensionsUnit}
                        onChange={(event) =>
                          updateParcel(index, parcelIndex, {
                            dimensionsUnit: event.target.value as Parcel["dimensionsUnit"],
                          })
                        }
                      >
                        <option value={DimensionUnit.CM}>cm</option>
                        <option value={DimensionUnit.IN}>in</option>
                        <option value={DimensionUnit.FT}>ft</option>
                      </select>
                    </label>
                    <NumberField
                      label="Weight"
                      value={parcel.weight}
                      onChange={(weight) => updateParcel(index, parcelIndex, { weight })}
                    />
                    <label className="text-sm font-medium text-primary">
                      Weight unit
                      <select
                        className={`${inputClass} mt-1`}
                        value={parcel.weightUnit}
                        onChange={(event) =>
                          updateParcel(index, parcelIndex, {
                            weightUnit: event.target.value as Parcel["weightUnit"],
                          })
                        }
                      >
                        <option value={WeightUnit.KG}>kg</option>
                        <option value={WeightUnit.LBS}>lbs</option>
                      </select>
                    </label>
                    <Field
                      label="SKU"
                      value={parcel.sku ?? ""}
                      onChange={(sku) => updateParcel(index, parcelIndex, { sku })}
                    />
                  </div>
                </div>
              ))}
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  updateStop(index, { parcels: [...stop.parcels, emptyParcel(unitSystem)] })
                }
              >
                + Add another parcel to stop
              </Button>
            </div>
          </MagicCard>
        ))}
        <Button
          type="button"
          variant="outline"
          onClick={() =>
            setStops((current) => [...current, emptyStop(current.length + 1, unitSystem)])
          }
        >
          Add stop
        </Button>
      </div>

      <MagicCard className="space-y-4 p-4 sm:p-5" clip={false}>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
            05 · Schedule
          </p>
          <h2 className="mt-1 text-sm font-semibold text-primary">Pickup date and time</h2>
          <p className="mt-1 text-xs text-muted">
            Choose ASAP, or pick a date and a time. Hours are 6:00 AM to 10:00 PM, America/Toronto.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            aria-pressed={scheduleMode === "now"}
            onClick={() => setScheduleMode("now")}
            className={`rounded-2xl border px-4 py-4 text-left ${
              scheduleMode === "now"
                ? "border-secondary bg-secondary/10"
                : "border-primary/10 bg-white"
            }`}
          >
            <p className="text-sm font-semibold text-primary">ASAP</p>
            <p className="mt-1 text-xs text-muted">Dispatch as soon as a vehicle is free.</p>
          </button>
          <button
            type="button"
            aria-pressed={scheduleMode === "later"}
            onClick={() => setScheduleMode("later")}
            className={`rounded-2xl border px-4 py-4 text-left ${
              scheduleMode === "later"
                ? "border-secondary bg-secondary/10"
                : "border-primary/10 bg-white"
            }`}
          >
            <p className="text-sm font-semibold text-primary">Schedule</p>
            <p className="mt-1 text-xs text-muted">Set a pickup date and time.</p>
          </button>
        </div>
        {scheduleMode === "later" ? (
          <div className="space-y-3 rounded-2xl border border-primary/10 bg-gray-bg/70 p-4">
            <DateTimePickerSeparateField
              dateLabel="Date"
              timeLabel="Time"
              value={scheduledAt}
              onChange={setScheduledAt}
              hourFormat={12}
              timeInterval={15}
              minDate={new Date()}
              minTime="06:00"
              maxTime="22:00"
              timezone={timezone}
              showTimezone
              onTimezoneChange={setTimezone}
              datePlaceholder="Pick a date"
              timePlaceholder="Pick a time"
            />
          </div>
        ) : null}
        <Field
          label="Internal reference"
          value={internalReference}
          onChange={setInternalReference}
        />
      </MagicCard>

      <section className="space-y-3 rounded-2xl border border-primary/10 p-4">
        <h2 className="text-sm font-semibold text-primary">Bulk CSV</h2>
        <p className="text-xs text-muted">
          Required columns: sequence, stop_type, address, unit, postal, contact_name, contact_phone,
          contact_email, notes, sku, length, width, height, dimensions_unit, weight, weight_unit,
          vehicle_class, construction_site, site_access, internal_reference, scheduled_at.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant="outline" onClick={downloadCsvTemplate}>
            Download CSV template
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => csvInputRef.current?.click()}
          >
            Upload CSV
          </Button>
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void importCsv(file);
              event.target.value = "";
            }}
          />
        </div>
      </section>

      <section className="rounded-2xl border border-primary/10 p-4">
        <h2 className="text-sm font-semibold text-primary">Quote</h2>
        <p className="mt-1 text-xs text-muted">
          Charged on confirm from vehicle, distance, and stops. Appears on your statement as
          uninvoiced. Weight is recorded for dispatch, not as a separate charge.
        </p>
        {quotedAmount != null ? (
          <div className="mt-3 space-y-1 text-sm">
            <p className="text-2xl font-bold text-primary">{formatCents(quotedAmount)}</p>
            {quote?.quote?.distance_meters != null ? (
              <p className="text-muted">{(quote.quote.distance_meters / 1000).toFixed(1)} km</p>
            ) : null}
            <QuoteLines
              breakdown={quote?.quote}
              quotedCents={quotedAmount}
              chargedCents={quotedAmount}
              currency={(quote?.quote?.currency || "cad").toUpperCase()}
            />
            {quoteStale ? (
              <p className="text-amber-800">Quote is out of date. Update it before confirming.</p>
            ) : null}
          </div>
        ) : (
          <p className="mt-3 text-sm text-muted">
            Update the quote after pickup, stops, and parcels are complete.
          </p>
        )}
      </section>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {csvErrors.length > 0 ? <BulkErrorReport errors={csvErrors} /> : null}
      {!validation.ok && !error ? (
        <p className="text-sm text-muted">{validation.errors[0]}</p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => void requestQuote()}
          disabled={quoting || allocation.blocked || (scheduleMode === "later" && !scheduledAt)}
        >
          {quoting ? "Quoting…" : "Update quote"}
        </Button>
        <ShimmerButton
          onClick={() => void confirmRoute()}
          disabled={
            confirming || !quote || quoteStale || allocation.blocked || quotedAmount == null
          }
        >
          {confirming ? "Confirming…" : "Confirm route"}
        </ShimmerButton>
      </div>

      {confirmResult ? (
        <section className="rounded-2xl border border-primary/10 p-4 text-sm">
          <p className="font-semibold text-primary">Route confirmed</p>
          <p className="mt-1">
            Charged{" "}
            {confirmResult.amountCents != null
              ? formatCents(confirmResult.amountCents)
              : "on your statement"}{" "}
            (net terms). This order is uninvoiced until delivery.
          </p>
          {confirmResult.trackingNumber ? (
            <p className="mt-1">Tracking {confirmResult.trackingNumber}</p>
          ) : null}
          <div className="mt-3 flex gap-4">
            <Link className="font-medium text-secondary" href={`/orders/${confirmResult.orderId}`}>
              View order
            </Link>
            <Link className="font-medium text-secondary" href="/billing">
              Billing statement
            </Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function AllocationBanner({
  blocked,
  label,
  message,
  stale,
}: {
  blocked: boolean;
  label: string;
  message: string;
  stale: boolean;
}) {
  return (
    <section
      className={`rounded-2xl px-4 py-3 text-sm ${
        blocked ? "bg-red-50 text-red-900" : "bg-primary/5 text-primary"
      }`}
    >
      <p className="font-semibold">{blocked ? "Cannot dispatch" : `Vehicle: ${label}`}</p>
      <p className="mt-1">{message}</p>
      {stale ? (
        <p className="mt-1">Stops or parcels changed. Update the quote before confirm.</p>
      ) : null}
    </section>
  );
}

function AddressField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: BookingAddress;
  onChange: (value: BookingAddress) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-medium text-primary">
        {label}
      </label>
      <div className="mt-1">
        <AddressAutocompleteInput
          id={id}
          value={value.formatted}
          onChange={(formatted) => onChange({ ...value, formatted })}
          onPlaceSelect={onChange}
          apiKey={publicEnv.googleMapsApiKey}
          placeholder={label}
          fallbackClassName={inputClass}
        />
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm font-medium text-primary">
      {label}
      <input
        className={`${inputClass} mt-1`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-sm font-medium text-primary">
      {label}
      <input
        className={`${inputClass} mt-1`}
        inputMode="decimal"
        value={Number.isFinite(value) ? String(value) : ""}
        onChange={(event) => {
          const next = event.target.value;
          if (next === "") {
            onChange(0);
            return;
          }
          const parsed = Number(next);
          if (!Number.isFinite(parsed) || parsed < 0) return;
          onChange(parsed);
        }}
      />
    </label>
  );
}
