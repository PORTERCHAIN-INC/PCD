"use client";

import Button from "@/components/ui/Button";
import { useBookingPreview } from "@/hooks/useBookingPreview";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
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
  type Recipient,
  type SavedAddress,
} from "@/lib/booking";
import { publicEnv } from "@/lib/env";
import { AddressAutocompleteInput, type BookingAddress } from "@porterchain/maps";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type Mode = "single" | "multi";
type Step = "details" | "review" | "confirmed";

const VEHICLES = ["sedan", "suv", "pickup", "cargoVan", "highRoof", "box16", "box20"];
const PACKAGES = ["looseParcel", "documents", "medical", "furniture", "foodBeverage"];

const emptyAddress = (): BookingAddress => ({ formatted: "" });

function addressToPayload(addr: BookingAddress) {
  return {
    formatted: addr.formatted,
    lat: addr.lat,
    lng: addr.lng,
    place_id: addr.placeId,
  };
}

function payloadToAddress(data?: Record<string, unknown>): BookingAddress {
  if (!data) return emptyAddress();
  return {
    formatted: String(data.formatted ?? ""),
    lat: typeof data.lat === "number" ? data.lat : undefined,
    lng: typeof data.lng === "number" ? data.lng : undefined,
    placeId: typeof data.place_id === "string" ? data.place_id : undefined,
  };
}

export default function BookDeliveryClient() {
  const { getApiToken, orgId, isSignedIn } = useMerchantAuth();
  const [mode, setMode] = useState<Mode>("single");
  const [step, setStep] = useState<Step>("details");
  const [pickup, setPickup] = useState<BookingAddress>(emptyAddress());
  const [dropoff, setDropoff] = useState<BookingAddress>(emptyAddress());
  const [parcels, setParcels] = useState<BookingAddress[]>([emptyAddress()]);
  const [scheduledAt, setScheduledAt] = useState("");
  const [vehicleClass, setVehicleClass] = useState("cargoVan");
  const [packageType, setPackageType] = useState("looseParcel");
  const [weightKg, setWeightKg] = useState("");
  const [internalRef, setInternalRef] = useState("");
  const [poNumber, setPoNumber] = useState("");
  const [costCentre, setCostCentre] = useState("");
  const [instructions, setInstructions] = useState("");
  const [recipientId, setRecipientId] = useState("");
  const [draftId, setDraftId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmResult, setConfirmResult] = useState<{
    tracking_number: string;
    amount_cents: number;
  } | null>(null);
  const [multiResult, setMultiResult] = useState<
    Array<{ parcel: number; tracking_number: string; amount_cents: number }>
  >([]);

  const [savedAddresses, setSavedAddresses] = useState<SavedAddress[]>([]);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [templates, setTemplates] = useState<BookingTemplate[]>([]);
  const [templateName, setTemplateName] = useState("");
  const [draftBanner, setDraftBanner] = useState<string | null>(null);

  const bookingPayload = useMemo((): BookDeliveryPayload | null => {
    if (!pickup.formatted || !dropoff.formatted) return null;
    return {
      pickup: addressToPayload(pickup),
      dropoff: addressToPayload(dropoff),
      vehicle_class: vehicleClass,
      package_type: packageType,
      weight_kg: weightKg ? Number(weightKg) : undefined,
      scheduled_at: new Date(scheduledAt || Date.now()).toISOString(),
      schedule_mode: "now",
      special_instructions: instructions || undefined,
      internal_reference: internalRef || undefined,
      purchase_order_number: poNumber || undefined,
      cost_centre: costCentre || undefined,
      recipient_id: recipientId || undefined,
    };
  }, [
    pickup,
    dropoff,
    vehicleClass,
    packageType,
    weightKg,
    scheduledAt,
    instructions,
    internalRef,
    poNumber,
    costCentre,
    recipientId,
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
      setVehicleClass(draft.vehicle_class || "cargoVan");
      setPackageType(draft.package_type || "looseParcel");
      setWeightKg(draft.weight_kg ? String(draft.weight_kg) : "");
      setInstructions(draft.special_instructions || "");
      const meta = draft.merchant_meta || {};
      setInternalRef(String(meta.internal_reference || ""));
      setPoNumber(String(meta.purchase_order_number || ""));
      setCostCentre(String(meta.cost_centre || ""));
      setRecipientId(String(meta.recipient_id || ""));
      setDraftBanner(
        `Draft recovered — expires ${draft.expires_at ? new Date(draft.expires_at).toLocaleString() : "soon"}`
      );
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

  function applySavedPickup(id: string) {
    const addr = savedAddresses.find((a) => a.id === id);
    if (!addr) return;
    setPickup({ formatted: addr.formatted });
  }

  function applyTemplate(t: BookingTemplate) {
    const p = t.payload as Record<string, unknown>;
    if (p.pickup) setPickup(payloadToAddress(p.pickup as Record<string, unknown>));
    if (p.dropoff) setDropoff(payloadToAddress(p.dropoff as Record<string, unknown>));
    if (typeof p.vehicle_class === "string") setVehicleClass(p.vehicle_class);
    if (typeof p.package_type === "string") setPackageType(p.package_type);
    if (typeof p.weight_kg === "number") setWeightKg(String(p.weight_kg));
    if (typeof p.internal_reference === "string") setInternalRef(p.internal_reference);
    if (typeof p.purchase_order_number === "string") setPoNumber(p.purchase_order_number);
    if (typeof p.cost_centre === "string") setCostCentre(p.cost_centre);
    if (typeof p.special_instructions === "string") setInstructions(p.special_instructions);
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
    if (!bookingPayload || !isSignedIn) return;
    setLoading(true);
    setError(null);
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
          orgId
        );
        setMultiResult(result.orders);
        if (result.errors.length) {
          setError(`${result.errors.length} parcel(s) failed validation`);
        }
        setStep("confirmed");
        return;
      }
      const result = await confirmBooking(token, bookingPayload, orgId, draftId ?? undefined);
      setConfirmResult({
        tracking_number: result.tracking_number,
        amount_cents: result.amount_cents,
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
          <p className="font-semibold text-green-800">Booking confirmed</p>
          {confirmResult && (
            <>
              <p className="mt-2 text-sm">
                Tracking: <span className="font-mono">{confirmResult.tracking_number}</span>
              </p>
              <p className="text-sm text-muted">
                Charged: {formatCents(confirmResult.amount_cents)} (net terms)
              </p>
            </>
          )}
          {multiResult.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm">
              {multiResult.map((o) => (
                <li key={o.parcel}>
                  Parcel {o.parcel}: <span className="font-mono">{o.tracking_number}</span> —{" "}
                  {formatCents(o.amount_cents)}
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4 flex gap-3">
            {confirmResult && (
              <Link
                href={`/track/${confirmResult.tracking_number}`}
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
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Book Delivery</h1>
          <p className="text-sm text-muted">Net terms — contract pricing with live preview</p>
        </div>
        <div className="flex gap-2">
          <ModeButton active={mode === "single"} onClick={() => setMode("single")}>
            Single
          </ModeButton>
          <ModeButton active={mode === "multi"} onClick={() => setMode("multi")}>
            Multi parcel
          </ModeButton>
          <Link
            href="/bulk"
            className="rounded-xl border border-primary/15 px-3 py-1.5 text-sm text-muted hover:bg-gray-bg"
          >
            CSV / Excel bulk
          </Link>
        </div>
      </div>

      {draftBanner && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {draftBanner}
        </div>
      )}

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
                      className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                      value={recipientId}
                      onChange={(e) => setRecipientId(e.target.value)}
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
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field
                    label="Scheduled at"
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={setScheduledAt}
                  />
                  <Field
                    label="Weight (kg)"
                    value={weightKg}
                    onChange={setWeightKg}
                    type="number"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-sm font-medium text-primary">Vehicle</label>
                    <select
                      className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                      value={vehicleClass}
                      onChange={(e) => setVehicleClass(e.target.value)}
                    >
                      {VEHICLES.map((v) => (
                        <option key={v} value={v}>
                          {v}
                          {preview?.vehicle_recommendation?.recommended_vehicle === v
                            ? " (recommended)"
                            : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-primary">Package type</label>
                    <select
                      className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
                      value={packageType}
                      onChange={(e) => setPackageType(e.target.value)}
                    >
                      {PACKAGES.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <Field label="Internal reference" value={internalRef} onChange={setInternalRef} />
                <Field label="Purchase order" value={poNumber} onChange={setPoNumber} />
                <Field label="Cost centre" value={costCentre} onChange={setCostCentre} />
                <div>
                  <label className="text-sm font-medium text-primary">Special instructions</label>
                  <textarea
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
                <ReviewRow label="Vehicle" value={vehicleClass} />
                <ReviewRow label="Package" value={packageType} />
                {internalRef && <ReviewRow label="Reference" value={internalRef} />}
                {poNumber && <ReviewRow label="PO" value={poNumber} />}
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
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
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
                    {loading ? "Confirming…" : "Confirm booking"}
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
      className={`rounded-xl px-3 py-1.5 text-sm ${
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
    <div className="flex gap-2 border-b border-primary/10 pb-3">
      {items.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onStep(s)}
          className={`rounded-lg px-3 py-1 text-sm capitalize ${
            step === s ? "bg-primary/10 font-medium text-primary" : "text-muted"
          }`}
        >
          {s}
        </button>
      ))}
    </div>
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
              {(preview.distance_meters / 1000).toFixed(1)} km · ~
              {preview.estimated_duration_minutes ?? "—"} min
            </p>
          )}
          {preview.pricing_breakdown && (
            <pre className="max-h-40 overflow-auto rounded-lg bg-gray-bg p-2 text-[10px]">
              {JSON.stringify(preview.pricing_breakdown, null, 2)}
            </pre>
          )}
        </div>
      )}
      {!loading && preview && !preview.valid && (
        <p className="mt-2 text-xs text-red-600">{preview.message || preview.error || "Invalid"}</p>
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
      <label className="text-sm font-medium text-primary">{label}</label>
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
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-primary">{label}</label>
      <input
        type={type}
        className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
