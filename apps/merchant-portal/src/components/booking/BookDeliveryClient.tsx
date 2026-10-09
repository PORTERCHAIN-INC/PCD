"use client";

import Button from "@/components/ui/Button";
import { useBookingPreview } from "@/hooks/useBookingPreview";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { QuoteLines } from "@/components/billing/QuoteLines";
import { CopyPublicTrackLink } from "@/components/tracking/CopyPublicTrackLink";
import type { BookDeliveryPayload } from "@/lib/api";
import {
  confirmBooking,
  confirmMultiParcel,
  createBookingTemplate,
  deleteBookingTemplate,
  formatCents,
  getActiveDraft,
  listBookingTemplates,
  listRecipients,
  listSavedAddresses,
  saveBookingDraft,
  type BookingTemplate,
  type MultiParcelResult,
  type Recipient,
  type SavedAddress,
} from "@/lib/booking";
import { PACKAGE_OPTIONS, VEHICLE_OPTIONS, packageLabel, vehicleLabel } from "@/lib/catalog";
import MapsMissingBanner from "@/components/maps/MapsMissingBanner";
import { publicEnv } from "@/lib/env";
import { DimensionUnit, WeightUnit, type Parcel } from "@/lib/route-module/types";
import { serializeParcelsForLegacyAPI, withVolumetricWeight } from "@/lib/route-module/units";
import { packagePayload } from "@/lib/route-module/toRouteImport";
import { formatDate } from "@/lib/utils";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import { DateTimePickerSeparateField } from "@porterchain/ui/datetime-picker-separate";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Mode = "single" | "multi";
type Step = "details" | "review" | "confirmed";

const VEHICLES = VEHICLE_OPTIONS.map((v) => v.id);
const PACKAGES = PACKAGE_OPTIONS.map((p) => p.id);

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 focus-visible:ring-offset-2";

const emptyAddress = (): BookingAddress => ({ formatted: "" });

function addressToPayload(addr: BookingAddress) {
  return {
    formatted: addr.formatted,
    lat: addr.lat,
    lng: addr.lng,
    place_id: addr.placeId,
    postal: addr.postal,
  };
}

function payloadToAddress(data?: Record<string, unknown>): BookingAddress {
  if (!data) return emptyAddress();
  return {
    formatted: String(data.formatted ?? ""),
    lat: typeof data.lat === "number" ? data.lat : undefined,
    lng: typeof data.lng === "number" ? data.lng : undefined,
    placeId: typeof data.place_id === "string" ? data.place_id : undefined,
    postal: typeof data.postal === "string" ? data.postal : undefined,
  };
}

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function emptyParcel(id = newId()): Parcel {
  return withVolumetricWeight({
    id,
    length: 0,
    width: 0,
    height: 0,
    dimensionsUnit: DimensionUnit.CM,
    weight: 0,
    weightUnit: WeightUnit.KG,
  });
}

function isFilledParcel(parcel: Parcel): boolean {
  return (
    parcel.weight > 0 ||
    parcel.length > 0 ||
    parcel.width > 0 ||
    parcel.height > 0 ||
    Boolean(parcel.sku?.trim()) ||
    Boolean(parcel.name?.trim())
  );
}

function parcelFromPayload(pkg: Record<string, unknown>): Parcel {
  return withVolumetricWeight({
    id: typeof pkg.id === "string" && pkg.id ? pkg.id : newId(),
    name: typeof pkg.name === "string" ? pkg.name : undefined,
    sku: typeof pkg.sku === "string" ? pkg.sku : undefined,
    length: Number(pkg.length_cm ?? 0),
    width: Number(pkg.width_cm ?? 0),
    height: Number(pkg.height_cm ?? 0),
    dimensionsUnit: DimensionUnit.CM,
    weight: Number(pkg.weight_kg ?? 0),
    weightUnit: WeightUnit.KG,
  });
}

function pickerValue(raw: unknown): string {
  if (!raw) return "";
  return String(raw).slice(0, 16);
}

export default function BookDeliveryClient({ embedded = false }: { embedded?: boolean }) {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [mode, setMode] = useState<Mode>("single");
  const [step, setStep] = useState<Step>("details");
  const [pickup, setPickup] = useState<BookingAddress>(emptyAddress());
  const [dropoff, setDropoff] = useState<BookingAddress>(emptyAddress());
  const [parcels, setParcels] = useState<BookingAddress[]>([emptyAddress()]);
  const [readyFrom, setReadyFrom] = useState("");
  const [pickupBy, setPickupBy] = useState("");
  const [cargo, setCargo] = useState<Parcel[]>([emptyParcel()]);
  const [vehicleClass, setVehicleClass] = useState("cargo_van");
  const [packageType, setPackageType] = useState("looseParcel");
  const [internalRef, setInternalRef] = useState("");
  const [poNumber, setPoNumber] = useState("");
  const [costCentre, setCostCentre] = useState("");
  const [instructions, setInstructions] = useState("");
  const [siteAccessNotes, setSiteAccessNotes] = useState("");
  const [requiresLiftgate, setRequiresLiftgate] = useState(false);
  const [otpRequired, setOtpRequired] = useState(false);
  const [custodianName, setCustodianName] = useState("");
  const [specimenId, setSpecimenId] = useState("");
  const [sealNumber, setSealNumber] = useState("");
  const [requiresColdChain, setRequiresColdChain] = useState(false);
  const [tempMin, setTempMin] = useState("");
  const [tempMax, setTempMax] = useState("");
  const [deliveryWindowStart, setDeliveryWindowStart] = useState("");
  const [deliveryWindowEnd, setDeliveryWindowEnd] = useState("");
  const [recipientId, setRecipientId] = useState("");
  const [consigneeEmail, setConsigneeEmail] = useState("");
  const [draftId, setDraftId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmResult, setConfirmResult] = useState<{
    tracking_number: string;
    amount_cents: number;
    is_sandbox?: boolean;
    public_track_url?: string | null;
    consignee_emailed?: boolean;
    consignee_email?: string | null;
  } | null>(null);
  const [bookAsSandbox, setBookAsSandbox] = useState(false);
  const [multiResult, setMultiResult] = useState<MultiParcelResult["orders"]>([]);

  const [savedAddresses, setSavedAddresses] = useState<SavedAddress[]>([]);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [templates, setTemplates] = useState<BookingTemplate[]>([]);
  const [templateName, setTemplateName] = useState("");
  const [draftBanner, setDraftBanner] = useState<string | null>(null);
  const confirmKeyRef = useRef<string | null>(null);

  const bookingPayload = useMemo((): BookDeliveryPayload | null => {
    if (!pickup.formatted || !dropoff.formatted) return null;
    const filledCargo = cargo.filter(isFilledParcel);
    const legacy = filledCargo.length ? serializeParcelsForLegacyAPI(filledCargo) : null;
    return {
      pickup: addressToPayload(pickup),
      dropoff: addressToPayload(dropoff),
      vehicle_class: vehicleClass,
      package_type: packageType,
      weight_kg: legacy && legacy.weight_kg > 0 ? legacy.weight_kg : undefined,
      dimensions: legacy?.dimensions || undefined,
      scheduled_at: new Date(readyFrom || Date.now()).toISOString(),
      schedule_mode: readyFrom || pickupBy ? "later" : "now",
      pickup_window_start: readyFrom ? new Date(readyFrom).toISOString() : undefined,
      pickup_window_end: pickupBy ? new Date(pickupBy).toISOString() : undefined,
      packages: filledCargo.length
        ? filledCargo.map((parcel) => ({ ...packagePayload(parcel), package_type: packageType }))
        : undefined,
      special_instructions: instructions || undefined,
      site_access_notes: siteAccessNotes || undefined,
      requires_liftgate: requiresLiftgate || undefined,
      otp_required: otpRequired || undefined,
      custodian_name: custodianName || undefined,
      specimen_id: specimenId || undefined,
      seal_number: sealNumber || undefined,
      requires_cold_chain: requiresColdChain || undefined,
      temperature_min_c: tempMin ? Number(tempMin) : undefined,
      temperature_max_c: tempMax ? Number(tempMax) : undefined,
      delivery_window_start: deliveryWindowStart
        ? new Date(deliveryWindowStart).toISOString()
        : undefined,
      delivery_window_end: deliveryWindowEnd
        ? new Date(deliveryWindowEnd).toISOString()
        : undefined,
      internal_reference: internalRef || undefined,
      purchase_order_number: poNumber || undefined,
      cost_centre: costCentre || undefined,
      recipient_id: recipientId || undefined,
      consignee_email: consigneeEmail || undefined,
      is_sandbox: bookAsSandbox || undefined,
    };
  }, [
    pickup,
    dropoff,
    vehicleClass,
    packageType,
    cargo,
    readyFrom,
    pickupBy,
    instructions,
    siteAccessNotes,
    requiresLiftgate,
    otpRequired,
    custodianName,
    specimenId,
    sealNumber,
    requiresColdChain,
    tempMin,
    tempMax,
    deliveryWindowStart,
    deliveryWindowEnd,
    internalRef,
    poNumber,
    costCentre,
    recipientId,
    consigneeEmail,
    bookAsSandbox,
  ]);

  const [previewToken, setPreviewToken] = useState<string | null>(null);
  useEffect(() => {
    if (!isSignedIn) return;
    getApiToken()
      .then(setPreviewToken)
      .catch(() => setPreviewToken(null));
  }, [isSignedIn, getApiToken]);

  const { preview, loading: previewLoading } = useBookingPreview(
    previewToken,
    orgId,
    bookingPayload,
    step === "review" || step === "details"
  );

  const loadMeta = useCallback(async () => {
    if (!isSignedIn) return;
    const token = await getApiToken();
    const [addrs, recips, tmpls, draft] = await Promise.all([
      listSavedAddresses(token, orgId),
      listRecipients(token, orgId),
      listBookingTemplates(token, orgId),
      getActiveDraft(token, orgId),
    ]);
    setSavedAddresses(addrs);
    setRecipients(recips);
    setTemplates(tmpls);
    if (draft) {
      setDraftId(draft.draft_id);
      setPickup(payloadToAddress(draft.pickup));
      setDropoff(payloadToAddress(draft.dropoff));
      setVehicleClass(draft.vehicle_class || "cargo_van");
      setPackageType(draft.package_type || "looseParcel");
      setInstructions(draft.special_instructions || "");
      setSiteAccessNotes(
        String(
          (draft.dropoff as Record<string, unknown> | undefined)?.site_access_notes ||
            draft.merchant_meta?.site_access_notes ||
            ""
        )
      );
      setRequiresLiftgate(Boolean(draft.merchant_meta?.requires_liftgate));
      setOtpRequired(Boolean(draft.merchant_meta?.otp_required));
      const meta = draft.merchant_meta || {};
      setCustodianName(String(meta.custodian_name || ""));
      setSpecimenId(String(meta.specimen_id || ""));
      setSealNumber(String(meta.seal_number || ""));
      setRequiresColdChain(Boolean(meta.requires_cold_chain));
      setTempMin(meta.temperature_min_c != null ? String(meta.temperature_min_c) : "");
      setTempMax(meta.temperature_max_c != null ? String(meta.temperature_max_c) : "");
      setDeliveryWindowStart(
        meta.delivery_window_start ? String(meta.delivery_window_start).slice(0, 16) : ""
      );
      setDeliveryWindowEnd(
        meta.delivery_window_end ? String(meta.delivery_window_end).slice(0, 16) : ""
      );
      setReadyFrom(pickerValue(meta.pickup_window_start || meta.scheduled_at));
      setPickupBy(pickerValue(meta.pickup_window_end));
      const savedPackages = Array.isArray(meta.packages) ? meta.packages : [];
      setCargo(
        savedPackages.length
          ? savedPackages
              .filter(
                (pkg): pkg is Record<string, unknown> => Boolean(pkg) && typeof pkg === "object"
              )
              .map(parcelFromPayload)
          : [emptyParcel()]
      );
      setInternalRef(String(meta.internal_reference || ""));
      setPoNumber(String(meta.purchase_order_number || ""));
      setCostCentre(String(meta.cost_centre || ""));
      setRecipientId(String(meta.recipient_id || ""));
      setConsigneeEmail(String(meta.consignee_email || ""));
      setDraftBanner(
        `Draft recovered — expires ${draft.expires_at ? formatDate(draft.expires_at) : "soon"}`
      );
    } else {
      const def = addrs.find((a) => a.is_default) ?? addrs[0];
      if (def) {
        setPickup({
          formatted: def.formatted,
          lat: def.lat ?? undefined,
          lng: def.lng ?? undefined,
          postal: def.postal ?? undefined,
        });
      }
    }
  }, [getApiToken, isSignedIn, orgId]);

  useEffect(() => {
    loadMeta().catch(() => undefined);
  }, [loadMeta]);

  useEffect(() => {
    if (preview?.vehicle_recommendation?.recommended_vehicle && step === "details") {
      setVehicleClass(preview.vehicle_recommendation.recommended_vehicle);
    }
  }, [preview?.vehicle_recommendation?.recommended_vehicle, step]);

  useEffect(() => {
    if (packageType === "foodBeverage") {
      setRequiresColdChain(true);
      if (!tempMin) setTempMin("2");
      if (!tempMax) setTempMax("8");
    }
  }, [packageType, tempMin, tempMax]);

  function applySavedPickup(id: string) {
    const addr = savedAddresses.find((a) => a.id === id);
    if (!addr) return;
    setPickup({
      formatted: addr.formatted,
      lat: addr.lat ?? undefined,
      lng: addr.lng ?? undefined,
      postal: addr.postal ?? undefined,
    });
  }

  function applyTemplate(t: BookingTemplate) {
    const p = t.payload as Record<string, unknown>;
    if (p.pickup) setPickup(payloadToAddress(p.pickup as Record<string, unknown>));
    if (p.dropoff) setDropoff(payloadToAddress(p.dropoff as Record<string, unknown>));
    if (typeof p.vehicle_class === "string") setVehicleClass(p.vehicle_class);
    if (typeof p.package_type === "string") setPackageType(p.package_type);
    if (typeof p.internal_reference === "string") setInternalRef(p.internal_reference);
    if (typeof p.purchase_order_number === "string") setPoNumber(p.purchase_order_number);
    if (typeof p.cost_centre === "string") setCostCentre(p.cost_centre);
    if (typeof p.special_instructions === "string") setInstructions(p.special_instructions);
    if (typeof p.site_access_notes === "string") setSiteAccessNotes(p.site_access_notes);
    if (typeof p.consignee_email === "string") setConsigneeEmail(p.consignee_email);
    if (typeof p.recipient_id === "string") setRecipientId(p.recipient_id);
    if (typeof p.requires_liftgate === "boolean") setRequiresLiftgate(p.requires_liftgate);
    if (typeof p.otp_required === "boolean") setOtpRequired(p.otp_required);
    if (typeof p.custodian_name === "string") setCustodianName(p.custodian_name);
    if (typeof p.specimen_id === "string") setSpecimenId(p.specimen_id);
    if (typeof p.seal_number === "string") setSealNumber(p.seal_number);
    if (typeof p.requires_cold_chain === "boolean") setRequiresColdChain(p.requires_cold_chain);
    if (typeof p.temperature_min_c === "number") setTempMin(String(p.temperature_min_c));
    if (typeof p.temperature_max_c === "number") setTempMax(String(p.temperature_max_c));
    if (typeof p.delivery_window_start === "string") {
      setDeliveryWindowStart(p.delivery_window_start.slice(0, 16));
    }
    if (typeof p.delivery_window_end === "string") {
      setDeliveryWindowEnd(p.delivery_window_end.slice(0, 16));
    }
    if (typeof p.pickup_window_start === "string") {
      setReadyFrom(p.pickup_window_start.slice(0, 16));
    } else if (typeof p.scheduled_at === "string") {
      setReadyFrom(p.scheduled_at.slice(0, 16));
    }
    if (typeof p.pickup_window_end === "string") {
      setPickupBy(p.pickup_window_end.slice(0, 16));
    }
    if (Array.isArray(p.packages) && p.packages.length) {
      setCargo(
        p.packages
          .filter((pkg): pkg is Record<string, unknown> => Boolean(pkg) && typeof pkg === "object")
          .map(parcelFromPayload)
      );
    }
  }

  async function onSaveDraft() {
    if (!bookingPayload || !isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await saveBookingDraft(token, bookingPayload, orgId, step);
      setDraftId(result.draft_id);
      setDraftBanner("Draft saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save draft failed");
    } finally {
      setLoading(false);
    }
  }

  async function onSaveTemplate() {
    if (!bookingPayload || !templateName.trim() || !isSignedIn) return;
    setLoading(true);
    try {
      const token = await getApiToken();
      await createBookingTemplate(token, templateName.trim(), bookingPayload, orgId);
      setTemplateName("");
      await loadMeta();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save template failed");
    } finally {
      setLoading(false);
    }
  }

  async function onConfirm() {
    if (!bookingPayload || !isSignedIn || loading) return;
    setLoading(true);
    setError(null);
    // One key per attempted booking. Kept across retries so a retry replays the
    // same order instead of booking a second van (BH).
    if (!confirmKeyRef.current) confirmKeyRef.current = crypto.randomUUID();
    const idempotencyKey = confirmKeyRef.current;
    try {
      const token = await getApiToken();
      if (mode === "multi") {
        const parcelPayloads: BookDeliveryPayload[] = parcels
          .filter((p) => p.formatted.trim())
          .map((p) => ({
            ...bookingPayload,
            dropoff: addressToPayload(p),
          }));
        const result = await confirmMultiParcel(
          token,
          addressToPayload(pickup),
          parcelPayloads,
          orgId,
          idempotencyKey
        );
        confirmKeyRef.current = null;
        setMultiResult(result.orders);
        if (result.errors.length) {
          setError(`${result.errors.length} parcel(s) failed validation`);
        }
        setStep("confirmed");
        return;
      }
      const result = await confirmBooking(
        token,
        bookingPayload,
        orgId,
        draftId ?? undefined,
        idempotencyKey
      );
      confirmKeyRef.current = null;
      setConfirmResult({
        tracking_number: result.tracking_number,
        amount_cents: result.amount_cents,
        is_sandbox: result.is_sandbox,
        public_track_url: result.public_track_url,
        consignee_emailed: result.consignee_emailed,
        consignee_email: result.consignee_email,
      });
      setStep("confirmed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Booking failed");
    } finally {
      setLoading(false);
    }
  }

  if (step === "confirmed") {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="rounded-2xl border border-green-200 bg-green-50 p-6">
          <p className="font-semibold text-green-800">
            {confirmResult?.is_sandbox ? "Test booking created" : "Booking confirmed"}
          </p>
          {confirmResult && (
            <>
              <p className="mt-2 text-sm">
                Tracking: <span className="font-mono">{confirmResult.tracking_number}</span>
              </p>
              <p className="text-sm text-muted">
                Charged: {formatCents(confirmResult.amount_cents)} (net terms)
              </p>
              {confirmResult.consignee_emailed && confirmResult.consignee_email ? (
                <p className="mt-1 text-sm text-muted">
                  Tracking emailed to {confirmResult.consignee_email}
                </p>
              ) : null}
              <div className="mt-3">
                <CopyPublicTrackLink
                  trackingNumber={confirmResult.tracking_number}
                  publicUrl={confirmResult.public_track_url}
                  isSandbox={Boolean(confirmResult.is_sandbox) || !confirmResult.public_track_url}
                />
              </div>
            </>
          )}
          {multiResult.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm">
              {multiResult.map((o) => (
                <li key={o.parcel}>
                  Parcel {o.parcel}: <span className="font-mono">{o.tracking_number}</span> —{" "}
                  {formatCents(o.amount_cents)}
                  {o.already_booked ? <span className="text-muted"> · already booked</span> : null}
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4 flex gap-3">
            {confirmResult && (
              <Link
                href={`/track?q=${encodeURIComponent(confirmResult.tracking_number)}`}
                className="text-sm text-secondary hover:underline"
              >
                Track shipment
              </Link>
            )}
            <button
              type="button"
              className="text-sm text-muted hover:underline"
              onClick={() => {
                setStep("details");
                setConfirmResult(null);
                setMultiResult([]);
              }}
            >
              Book another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={embedded ? "space-y-6" : "mx-auto max-w-5xl space-y-6"}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        {embedded ? (
          <p className="text-sm text-muted">Net terms — contract pricing with live preview</p>
        ) : (
          <div>
            <h1 className="text-2xl font-bold text-primary">Request capacity</h1>
            <p className="text-sm text-muted">Book a vehicle and driver on your contract rates.</p>
          </div>
        )}
        <div className="flex gap-2">
          <ModeButton active={mode === "single"} onClick={() => setMode("single")}>
            Single
          </ModeButton>
          <ModeButton active={mode === "multi"} onClick={() => setMode("multi")}>
            Multiple deliveries
          </ModeButton>
          {embedded ? null : (
            <Link
              href="/routes?tab=csv"
              className="rounded-xl border border-primary/15 px-3 py-1.5 text-sm text-muted hover:bg-gray-bg"
            >
              CSV / Excel bulk
            </Link>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-primary/10 bg-gray-bg/60 px-4 py-3 text-sm text-muted">
        <p>
          <span className="font-medium text-primary">Single</span> — one pickup → one drop (one
          order). <span className="font-medium text-primary">Multiple deliveries</span> — same
          pickup, many drops as <span className="font-medium text-primary">separate orders</span>{" "}
          (not one multi-stop route). For one multi-stop route, use the Multi-stop route tab.
        </p>
      </div>

      {draftBanner && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {draftBanner}
        </div>
      )}

      <MapsMissingBanner />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="rounded-2xl border border-primary/10 bg-white p-6">
            <StepTabs step={step} onStep={setStep} />
            {step === "details" && (
              <div className="mt-4 space-y-4">
                {savedAddresses.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-primary">Saved pickup</label>
                    <select
                      aria-label="Saved pickup"
                      className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                      onChange={(e) => applySavedPickup(e.target.value)}
                      defaultValue=""
                    >
                      <option value="">Select saved address…</option>
                      {savedAddresses.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.label} — {a.formatted}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <AddressField
                  id="merchant-pickup"
                  label="Pickup address"
                  value={pickup}
                  onChange={setPickup}
                />
                {mode === "single" ? (
                  <AddressField
                    id="merchant-dropoff"
                    label="Dropoff address"
                    value={dropoff}
                    onChange={setDropoff}
                  />
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-primary">Dropoff parcels</p>
                    {parcels.map((p, i) => (
                      <div key={i} className="flex gap-2">
                        <div className="flex-1">
                          <AddressField
                            id={`parcel-${i}`}
                            label={`Parcel ${i + 1}`}
                            value={p}
                            onChange={(addr) =>
                              setParcels((prev) => prev.map((x, j) => (j === i ? addr : x)))
                            }
                          />
                        </div>
                        {parcels.length > 1 && (
                          <button
                            type="button"
                            className="self-end text-xs text-red-600"
                            onClick={() => setParcels((prev) => prev.filter((_, j) => j !== i))}
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      type="button"
                      className="text-sm text-secondary hover:underline"
                      onClick={() => setParcels((p) => [...p, emptyAddress()])}
                    >
                      + Add parcel
                    </button>
                  </div>
                )}
                {recipients.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-primary">Recipient</label>
                    <select
                      aria-label="Recipient"
                      className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                      value={recipientId}
                      onChange={(e) => {
                        const id = e.target.value;
                        setRecipientId(id);
                        const rec = recipients.find((r) => r.id === id);
                        if (rec?.email) setConsigneeEmail(rec.email);
                      }}
                    >
                      <option value="">None</option>
                      {recipients.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name}
                          {r.company ? ` (${r.company})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <Field
                  label="Receiver email (optional)"
                  value={consigneeEmail}
                  onChange={setConsigneeEmail}
                  type="email"
                />
                <div>
                  <p className="text-sm font-medium text-primary">Pickup window</p>
                  <p className="text-xs text-muted">
                    Leave blank to book for pickup as soon as a driver is available. Hours are
                    America/Toronto.
                  </p>
                  <div className="mt-2 grid gap-4 sm:grid-cols-2">
                    <DateTimeField label="Ready from" value={readyFrom} onChange={setReadyFrom} />
                    <DateTimeField
                      label="Pickup by"
                      value={pickupBy}
                      onChange={setPickupBy}
                      minDate={readyFrom ? new Date(readyFrom) : new Date()}
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm font-medium text-primary">Parcels on this pickup</p>
                    <p className="text-xs text-muted">
                      Weight and size are used for pricing. Add a line per box or bag.
                    </p>
                  </div>
                  {cargo.map((parcel, index) => (
                    <div key={parcel.id} className="rounded-xl bg-gray-bg p-3">
                      <div className="mb-2 flex items-center justify-between">
                        <p className="text-sm font-medium text-primary">Parcel {index + 1}</p>
                        {cargo.length > 1 ? (
                          <button
                            type="button"
                            className="text-xs text-red-600"
                            onClick={() => setCargo((prev) => prev.filter((_, i) => i !== index))}
                          >
                            Remove
                          </button>
                        ) : null}
                      </div>
                      <div className="grid gap-3 sm:grid-cols-4">
                        <NumberField
                          label="Length"
                          value={parcel.length}
                          onChange={(length) =>
                            setCargo((prev) =>
                              prev.map((row, i) =>
                                i === index ? withVolumetricWeight({ ...row, length }) : row
                              )
                            )
                          }
                        />
                        <NumberField
                          label="Width"
                          value={parcel.width}
                          onChange={(width) =>
                            setCargo((prev) =>
                              prev.map((row, i) =>
                                i === index ? withVolumetricWeight({ ...row, width }) : row
                              )
                            )
                          }
                        />
                        <NumberField
                          label="Height"
                          value={parcel.height}
                          onChange={(height) =>
                            setCargo((prev) =>
                              prev.map((row, i) =>
                                i === index ? withVolumetricWeight({ ...row, height }) : row
                              )
                            )
                          }
                        />
                        <label className="text-sm font-medium text-primary">
                          Unit
                          <select
                            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                            value={parcel.dimensionsUnit}
                            onChange={(event) =>
                              setCargo((prev) =>
                                prev.map((row, i) =>
                                  i === index
                                    ? withVolumetricWeight({
                                        ...row,
                                        dimensionsUnit: event.target
                                          .value as Parcel["dimensionsUnit"],
                                      })
                                    : row
                                )
                              )
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
                          onChange={(weight) =>
                            setCargo((prev) =>
                              prev.map((row, i) =>
                                i === index ? withVolumetricWeight({ ...row, weight }) : row
                              )
                            )
                          }
                        />
                        <label className="text-sm font-medium text-primary">
                          Weight unit
                          <select
                            className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                            value={parcel.weightUnit}
                            onChange={(event) =>
                              setCargo((prev) =>
                                prev.map((row, i) =>
                                  i === index
                                    ? withVolumetricWeight({
                                        ...row,
                                        weightUnit: event.target.value as Parcel["weightUnit"],
                                      })
                                    : row
                                )
                              )
                            }
                          >
                            <option value={WeightUnit.KG}>kg</option>
                            <option value={WeightUnit.LBS}>lbs</option>
                          </select>
                        </label>
                        <Field
                          label="SKU"
                          value={parcel.sku ?? ""}
                          onChange={(sku) =>
                            setCargo((prev) =>
                              prev.map((row, i) => (i === index ? { ...row, sku } : row))
                            )
                          }
                        />
                      </div>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="text-sm text-secondary hover:underline"
                    onClick={() => setCargo((prev) => [...prev, emptyParcel()])}
                  >
                    + Add parcel
                  </button>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-sm font-medium text-primary">Vehicle we send</label>
                    <p className="mt-0.5 text-xs text-muted">
                      {preview?.vehicle_recommendation?.coverage_note ??
                        "PorterChain sends the vehicle. You book a class for the job — you do not manage a fleet."}
                    </p>
                    <select
                      aria-label="Vehicle we send"
                      className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                      value={vehicleClass}
                      onChange={(e) => setVehicleClass(e.target.value)}
                    >
                      {VEHICLES.map((v) => {
                        const rec = preview?.vehicle_recommendation;
                        const recommended = rec?.recommended_vehicle === v;
                        const assigned =
                          rec?.assigned_vehicle_ids?.includes(v) ||
                          rec?.preferred_vehicles?.includes(v);
                        const mark = [
                          recommended ? "recommended" : null,
                          assigned && !recommended ? "assigned" : null,
                        ]
                          .filter(Boolean)
                          .join(", ");
                        return (
                          <option key={v} value={v}>
                            {vehicleLabel(v)}
                            {mark ? ` (${mark})` : ""}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-primary">Package type</label>
                    <select
                      aria-label="Package type"
                      className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                      value={packageType}
                      onChange={(e) => setPackageType(e.target.value)}
                    >
                      {PACKAGES.map((p) => (
                        <option key={p} value={p}>
                          {packageLabel(p)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <Field label="Internal reference" value={internalRef} onChange={setInternalRef} />
                <Field label="Purchase order" value={poNumber} onChange={setPoNumber} />
                <Field label="Cost centre" value={costCentre} onChange={setCostCentre} />
                <div>
                  <label className="text-sm font-medium text-primary">Site access</label>
                  <p className="mt-0.5 text-xs text-primary/60">
                    Gate code, liftgate, foreman contact — jobsite deliveries
                  </p>
                  <textarea
                    className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                    rows={2}
                    value={siteAccessNotes}
                    onChange={(e) => setSiteAccessNotes(e.target.value)}
                    placeholder="e.g. Gate 4 code 8821 · call Mike 416-555-0100"
                  />
                  <label className="mt-3 flex items-center gap-2 text-sm text-primary">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-primary/20"
                      checked={requiresLiftgate}
                      onChange={(e) => setRequiresLiftgate(e.target.checked)}
                    />
                    Liftgate required at delivery (+$45 surcharge)
                  </label>
                  <label className="mt-3 flex items-center gap-2 text-sm text-primary">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-primary/20"
                      checked={otpRequired}
                      onChange={(e) => setOtpRequired(e.target.checked)}
                    />
                    Require OTP verification at delivery
                  </label>
                </div>
                {packageType === "medical" && (
                  <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-4">
                    <h3 className="text-sm font-semibold text-primary">Chain of custody</h3>
                    <p className="mt-1 text-xs text-primary/60">
                      Required for medical / lab specimens
                    </p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <Field
                        label="Custodian name"
                        value={custodianName}
                        onChange={setCustodianName}
                      />
                      <Field label="Specimen ID" value={specimenId} onChange={setSpecimenId} />
                      <Field label="Seal number" value={sealNumber} onChange={setSealNumber} />
                    </div>
                  </div>
                )}
                {packageType === "foodBeverage" && (
                  <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4">
                    <h3 className="text-sm font-semibold text-primary">
                      Cold chain & delivery window
                    </h3>
                    <label className="mt-2 flex items-center gap-2 text-sm text-primary">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-primary/20"
                        checked={requiresColdChain}
                        onChange={(e) => setRequiresColdChain(e.target.checked)}
                      />
                      Refrigerated transport required
                    </label>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <Field
                        label="Min temp (°C)"
                        value={tempMin}
                        onChange={setTempMin}
                        type="number"
                      />
                      <Field
                        label="Max temp (°C)"
                        value={tempMax}
                        onChange={setTempMax}
                        type="number"
                      />
                      <DateTimeField
                        label="Window start"
                        value={deliveryWindowStart}
                        onChange={setDeliveryWindowStart}
                      />
                      <DateTimeField
                        label="Window end"
                        value={deliveryWindowEnd}
                        onChange={setDeliveryWindowEnd}
                      />
                    </div>
                  </div>
                )}
                <div>
                  <label
                    htmlFor="book-special-instructions"
                    className="text-sm font-medium text-primary"
                  >
                    Special instructions
                  </label>
                  <textarea
                    id="book-special-instructions"
                    className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                    rows={3}
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                  />
                </div>
              </div>
            )}
            {step === "review" && bookingPayload && (
              <div className="mt-4 space-y-3 text-sm">
                <ReviewRow label="Pickup" value={pickup.formatted} />
                <ReviewRow
                  label="Dropoff"
                  value={
                    mode === "single"
                      ? dropoff.formatted
                      : `${parcels.filter((p) => p.formatted).length} parcels`
                  }
                />
                <ReviewRow label="Vehicle we send" value={vehicleLabel(vehicleClass)} />
                <ReviewRow label="Package" value={packageLabel(packageType)} />
                {readyFrom ? (
                  <ReviewRow
                    label="Ready from"
                    value={formatDate(new Date(readyFrom).toISOString())}
                  />
                ) : null}
                {pickupBy ? (
                  <ReviewRow
                    label="Pickup by"
                    value={formatDate(new Date(pickupBy).toISOString())}
                  />
                ) : null}
                {cargo.filter(isFilledParcel).length > 0 ? (
                  <ReviewRow
                    label="Parcels"
                    value={cargo
                      .filter(isFilledParcel)
                      .map((parcel, i) => {
                        const spec = [
                          parcel.sku || `Parcel ${i + 1}`,
                          parcel.weight > 0 ? `${parcel.weight} ${parcel.weightUnit}` : null,
                        ]
                          .filter(Boolean)
                          .join(" · ");
                        return spec;
                      })
                      .join("; ")}
                  />
                ) : null}
                {consigneeEmail && <ReviewRow label="Receiver email" value={consigneeEmail} />}
                {internalRef && <ReviewRow label="Reference" value={internalRef} />}
                {siteAccessNotes && <ReviewRow label="Site access" value={siteAccessNotes} />}
                {requiresLiftgate && <ReviewRow label="Liftgate" value="Required (+$45)" />}
                {otpRequired && <ReviewRow label="Delivery OTP" value="Required" />}
                {packageType === "medical" && specimenId && (
                  <ReviewRow label="Specimen ID" value={specimenId} />
                )}
                {requiresColdChain && (
                  <ReviewRow label="Cold chain" value={`${tempMin || "?"}–${tempMax || "?"} °C`} />
                )}
                {deliveryWindowEnd && (
                  <ReviewRow label="Delivery window end" value={deliveryWindowEnd} />
                )}
                {poNumber && <ReviewRow label="PO" value={poNumber} />}
                <fieldset className="rounded-xl border border-primary/15 p-3">
                  <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-muted">
                    Booking environment
                  </legend>
                  <div className="mt-1 flex flex-wrap gap-3">
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="book-env"
                        checked={!bookAsSandbox}
                        onChange={() => setBookAsSandbox(false)}
                      />
                      Live — books real capacity
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="book-env"
                        checked={bookAsSandbox}
                        onChange={() => setBookAsSandbox(true)}
                      />
                      Test — no driver dispatched
                    </label>
                  </div>
                  <p className="mt-2 text-xs text-muted">
                    {bookAsSandbox
                      ? "Creates a sandbox order only. No public track link. It is not released to dispatch."
                      : "Confirms a live shipment on the network."}
                  </p>
                </fieldset>
                {preview?.contract_pricing && (
                  <p className="rounded-lg bg-blue-50 px-3 py-2 text-blue-800">
                    Contract pricing applied
                    {preview.payment_terms ? ` · ${preview.payment_terms}` : ""}
                  </p>
                )}
                {preview?.warnings?.map((w) => (
                  <p key={w} className="text-amber-700">
                    {w}
                  </p>
                ))}
                {preview?.address_errors?.map((e) => (
                  <p key={e.field} className="text-red-600">
                    {e.field}: {e.error}
                  </p>
                ))}
              </div>
            )}
            {error && (
              <p className="mt-3 text-sm text-red-600" role="alert" aria-live="polite">
                {error}
              </p>
            )}
            <div className="mt-6 flex flex-wrap gap-2">
              {step === "details" && (
                <Button type="button" onClick={() => setStep("review")}>
                  Review booking
                </Button>
              )}
              {step === "review" && (
                <>
                  <Button type="button" variant="secondary" onClick={() => setStep("details")}>
                    Back
                  </Button>
                  <Button
                    type="button"
                    onClick={onConfirm}
                    disabled={loading || preview?.valid === false}
                  >
                    {loading
                      ? "Confirming…"
                      : bookAsSandbox
                        ? "Confirm test booking"
                        : "Confirm live booking"}
                  </Button>
                </>
              )}
              <Button type="button" variant="secondary" onClick={onSaveDraft} disabled={loading}>
                Save draft
              </Button>
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <PricingPanel preview={preview} loading={previewLoading} />
          <div className="rounded-2xl border border-primary/10 bg-white p-4">
            <h3 className="font-medium text-primary">Saved templates</h3>
            {templates.length === 0 ? (
              <p className="mt-2 text-xs text-muted">No templates yet</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {templates.map((t) => (
                  <li key={t.id} className="flex items-center justify-between gap-2 text-sm">
                    <button
                      type="button"
                      className="text-left text-secondary hover:underline"
                      onClick={() => applyTemplate(t)}
                    >
                      {t.name}
                    </button>
                    <button
                      type="button"
                      className="text-xs text-red-600"
                      onClick={async () => {
                        const token = await getApiToken();
                        await deleteBookingTemplate(token, t.id, orgId);
                        await loadMeta();
                      }}
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-3 flex gap-2">
              <input
                placeholder="Template name"
                className="flex-1 rounded-lg border border-primary/15 px-2 py-1 text-xs"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
              />
              <Button
                type="button"
                variant="secondary"
                onClick={onSaveTemplate}
                disabled={!templateName.trim()}
              >
                Save
              </Button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl px-3 py-1.5 text-sm ${FOCUS_RING} ${
        active ? "bg-primary text-white" : "border border-primary/15 text-muted hover:bg-gray-bg"
      }`}
    >
      {children}
    </button>
  );
}

function StepTabs({ step, onStep }: { step: Step; onStep: (s: Step) => void }) {
  const items: Step[] = ["details", "review"];
  return (
    <nav className="flex gap-2 border-b border-primary/10 pb-3" aria-label="Booking steps">
      {items.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onStep(s)}
          aria-current={step === s ? "step" : undefined}
          className={`rounded-lg px-3 py-1 text-sm capitalize ${FOCUS_RING} ${
            step === s ? "bg-primary/10 font-medium text-primary" : "text-muted"
          }`}
        >
          {s}
        </button>
      ))}
    </nav>
  );
}

function PricingPanel({
  preview,
  loading,
}: {
  preview: ReturnType<typeof useBookingPreview>["preview"];
  loading: boolean;
}) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4">
      <h3 className="font-medium text-primary">Pricing preview</h3>
      {loading && <p className="mt-2 text-xs text-muted">Calculating…</p>}
      {!loading && preview?.valid && preview.amount_cents != null && (
        <div className="mt-2 space-y-2">
          <p className="text-2xl font-bold text-primary">{formatCents(preview.amount_cents)}</p>
          {preview.contract_pricing && (
            <span className="inline-block rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800">
              Contract rate
            </span>
          )}
          {preview.distance_meters != null && (
            <p className="text-xs text-muted">
              {(preview.distance_meters / 1000).toFixed(1)} km
              {preview.estimated_duration_minutes != null
                ? ` · ~${preview.estimated_duration_minutes} min travel estimate`
                : ""}
            </p>
          )}
          {preview.pricing_breakdown && (
            <QuoteLines
              breakdown={preview.pricing_breakdown}
              quotedCents={preview.amount_cents}
              chargedCents={preview.amount_cents}
              currency={(preview.currency || "cad").toUpperCase()}
            />
          )}
        </div>
      )}
      {!loading && preview && !preview.valid && (
        <div className="mt-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          <p className="font-semibold">Cannot quote this capacity request</p>
          <p className="mt-1">{preview.message || preview.error || "Invalid"}</p>
          {(preview.message || preview.error || "")
            .toLowerCase()
            .match(/fsa|tile|coverage|out of|ontario|postal/) && (
            <p className="mt-1 text-red-600/80">
              Pickup and drop-off must be inside the GTA ±150 km served FSA tile with a rate on
              file.
            </p>
          )}
        </div>
      )}
      {!loading && !preview && (
        <p className="mt-2 text-xs text-muted">Enter addresses for live pricing</p>
      )}
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-primary/5 py-1">
      <span className="text-muted">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
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
  onChange: (v: BookingAddress) => void;
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
          fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
        />
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  id,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  id?: string;
}) {
  const fieldId = id ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div>
      <label htmlFor={fieldId} className="text-sm font-medium text-primary">
        {label}
      </label>
      <input
        id={fieldId}
        type={type}
        className={`mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm ${FOCUS_RING}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function DateTimeField({
  label,
  value,
  onChange,
  minDate,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  minDate?: Date;
}) {
  return (
    <div>
      <span className="text-sm font-medium text-primary">{label}</span>
      <p className="text-xs text-muted">America/Toronto</p>
      <div className="mt-1">
        <DateTimePickerSeparateField
          value={value}
          onChange={onChange}
          timezone="America/Toronto"
          showTimezone={false}
          hourFormat={12}
          timeInterval={15}
          minDate={minDate ?? new Date()}
          datePlaceholder="Pick a date"
          timePlaceholder="Pick time"
        />
      </div>
    </div>
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
        className={`mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm ${FOCUS_RING}`}
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
