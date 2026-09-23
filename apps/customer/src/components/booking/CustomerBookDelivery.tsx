"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  AddressAutocompleteInput,
  GoogleMapsProvider,
  type BookingAddress,
} from "@porterchain/maps";
import { DateTimePickerSeparateField } from "@porterchain/ui/datetime-picker-separate";
import {
  createQuote,
  formatCents,
  getQuote,
  previewQuote,
  mockCompleteCheckout,
  startBooking,
  type QuoteResult,
} from "@/lib/booking";
import CustomerMotion from "@/components/motion/CustomerMotion";
import {
  FieldSuggestions,
  INSTRUCTION_OPTIONS,
  VALUE_OPTIONS,
  formatCanadianPhone,
  parseDeclaredCents,
} from "@/components/booking/FieldSuggestions";
import { REBOOK_STORAGE_KEY } from "@/lib/api";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import { cn } from "@/lib/utils";
import {
  captureVisitorHandoff,
  getVisitorSessionId,
  getVisitorTrackingPayload,
} from "@/lib/visitor-session";

import ParcelEditor from "./ParcelEditor";
import {
  FALLBACK_PRESETS,
  FALLBACK_VEHICLES,
  blankParcel,
  canonicalVehicle,
  humanQuoteError,
  nextFittingVehicle,
  pieceFits,
  type BookingPreset,
  type BookingVehicle,
  type ParcelDraft,
} from "./parcelModel";

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 focus-visible:ring-offset-2";

type Step = "details" | "quote" | "checkout" | "confirmed";

function toPayload(addr: BookingAddress) {
  return {
    formatted: addr.formatted,
    lat: addr.lat,
    lng: addr.lng,
    place_id: addr.placeId,
    postal: addr.postal,
  };
}

function placeChosen(address: BookingAddress, mapsOn: boolean): boolean {
  if (!address.formatted.trim()) return false;
  if (!mapsOn) return true;
  return address.lat != null && address.lng != null && Boolean(address.placeId);
}

function editAddress(current: BookingAddress, next: string): BookingAddress {
  return next === current.formatted ? current : { formatted: next };
}

function draftsFromSaved(items: Array<Record<string, unknown>> | null | undefined): ParcelDraft[] {
  if (!items?.length) return [blankParcel()];
  return items.map((item) => ({
    preset_id: String(item.preset_id || "small"),
    quantity: 1,
    instructions: String(item.instructions || ""),
    length_in: item.length_cm ? String(Math.round((Number(item.length_cm) / 2.54) * 10) / 10) : "",
    width_in: item.width_cm ? String(Math.round((Number(item.width_cm) / 2.54) * 10) / 10) : "",
    height_in: item.height_cm ? String(Math.round((Number(item.height_cm) / 2.54) * 10) / 10) : "",
    weight_lb: item.weight_kg
      ? String(Math.round((Number(item.weight_kg) / 0.45359237) * 10) / 10)
      : "",
  }));
}

function defaultScheduledAt(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() + 30);
  return d.toISOString().slice(0, 16);
}

export default function CustomerBookDelivery() {
  if (!isClerkConfigured()) {
    return <CustomerBookDeliveryBody getToken={async () => "dev"} userId={null} email="" />;
  }
  return <CustomerBookDeliveryWithClerk />;
}

function CustomerBookDeliveryWithClerk() {
  const { getToken, userId } = useAuth();
  const { user } = useUser();
  const email = user?.primaryEmailAddress?.emailAddress ?? "";
  return <CustomerBookDeliveryBody getToken={getToken} userId={userId} email={email} />;
}

function CustomerBookDeliveryBody({
  getToken,
  userId,
  email,
}: {
  getToken: () => Promise<string | null>;
  userId: string | null | undefined;
  email: string;
}) {
  const searchParams = useSearchParams();
  const handoffQuoteId = searchParams.get("quote_id");
  const wantsRebook = searchParams.get("rebook") === "1";

  useEffect(() => {
    captureVisitorHandoff(searchParams);
    const requested = canonicalVehicle(searchParams.get("vehicle"));
    if (requested) setVehicleClass(requested);
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${publicEnv.porterchainApiUrl.replace(/\/$/, "")}/v1/booking-catalog`)
      .then((res) => (res.ok ? res.json() : null))
      .then((body: { vehicles?: BookingVehicle[]; presets?: BookingPreset[] } | null) => {
        if (cancelled || !body) return;
        if (Array.isArray(body.vehicles) && body.vehicles.length) setVehicles(body.vehicles);
        if (Array.isArray(body.presets) && body.presets.length) setPresets(body.presets);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const [step, setStep] = useState<Step>("details");
  const [pickup, setPickup] = useState<BookingAddress>({ formatted: "" });
  const [dropoff, setDropoff] = useState<BookingAddress>({ formatted: "" });
  const [vehicles, setVehicles] = useState<BookingVehicle[]>(FALLBACK_VEHICLES);
  const [presets, setPresets] = useState<BookingPreset[]>(FALLBACK_PRESETS);
  const [vehicleClass, setVehicleClass] = useState("sedan_suv");
  const [bookingMode, setBookingMode] = useState<"parcels" | "vehicle">("parcels");
  const [parcels, setParcels] = useState<ParcelDraft[]>([blankParcel()]);
  const [declared, setDeclared] = useState("");
  const [instructions, setInstructions] = useState("");
  const [extraStop, setExtraStop] = useState<BookingAddress>({ formatted: "" });
  const [promo, setPromo] = useState("");
  const [scheduleMode, setScheduleMode] = useState<"now" | "later">("now");
  const [scheduledAt, setScheduledAt] = useState(defaultScheduledAt);
  const [phone, setPhone] = useState("");
  const [terms, setTerms] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [dangerous, setDangerous] = useState(false);
  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [liveFare, setLiveFare] = useState<{
    amount_display: string;
    distance_km?: number | null;
  } | null>(null);
  const [trackingNumber, setTrackingNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!wantsRebook || handoffQuoteId) return;
    try {
      const raw = sessionStorage.getItem(REBOOK_STORAGE_KEY);
      if (!raw) return;
      sessionStorage.removeItem(REBOOK_STORAGE_KEY);
      const payload = JSON.parse(raw) as {
        pickup?: { formatted?: string; lat?: number; lng?: number; place_id?: string };
        dropoff?: { formatted?: string; lat?: number; lng?: number; place_id?: string };
        vehicle_class?: string | null;
        booking_mode?: "parcels" | "vehicle" | null;
        parcels?: Array<Record<string, unknown>> | null;
        declared_value_cents?: number | null;
      };
      if (payload.pickup?.formatted) {
        setPickup({
          formatted: String(payload.pickup.formatted),
          lat: payload.pickup.lat,
          lng: payload.pickup.lng,
          placeId: payload.pickup.place_id,
        });
      }
      if (payload.dropoff?.formatted) {
        setDropoff({
          formatted: String(payload.dropoff.formatted),
          lat: payload.dropoff.lat,
          lng: payload.dropoff.lng,
          placeId: payload.dropoff.place_id,
        });
      }
      if (payload.vehicle_class) setVehicleClass(canonicalVehicle(payload.vehicle_class));
      if (payload.booking_mode === "vehicle" || payload.booking_mode === "parcels") {
        setBookingMode(payload.booking_mode);
      }
      if (payload.parcels?.length) setParcels(draftsFromSaved(payload.parcels));
      if (payload.declared_value_cents)
        setDeclared((payload.declared_value_cents / 100).toFixed(2));
    } catch {
      /* ignore bad rebook payload */
    }
  }, [wantsRebook, handoffQuoteId]);

  useEffect(() => {
    if (!handoffQuoteId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const resumed = await getQuote(handoffQuoteId);
        if (cancelled) return;
        if (resumed.pickup?.formatted) {
          setPickup({
            formatted: resumed.pickup.formatted,
            lat: resumed.pickup.lat,
            lng: resumed.pickup.lng,
            placeId: resumed.pickup.place_id,
          });
        }
        if (resumed.dropoff?.formatted) {
          setDropoff({
            formatted: resumed.dropoff.formatted,
            lat: resumed.dropoff.lat,
            lng: resumed.dropoff.lng,
            placeId: resumed.dropoff.place_id,
          });
        }
        if (resumed.vehicle_class) setVehicleClass(canonicalVehicle(resumed.vehicle_class));
        if (resumed.booking_mode === "vehicle" || resumed.booking_mode === "parcels") {
          setBookingMode(resumed.booking_mode);
        }
        if (resumed.parcels?.length) setParcels(draftsFromSaved(resumed.parcels));
        if (resumed.declared_value_cents)
          setDeclared((resumed.declared_value_cents / 100).toFixed(2));
        setQuote({
          quote_id: resumed.quote_id,
          state: resumed.state,
          amount_cents: resumed.amount_cents,
          amount_display: resumed.amount_display,
          expires_at: resumed.expires_at,
          distance_km: resumed.distance_km,
          pricing_breakdown: resumed.pricing_breakdown,
        });
        setStep("quote");
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not resume quote");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [handoffQuoteId]);

  const quotePayload = useMemo(
    () => ({
      pickup: toPayload(pickup),
      dropoff: toPayload(dropoff),
      vehicle_class: vehicleClass,
      booking_mode: bookingMode,
      parcels:
        bookingMode === "vehicle"
          ? undefined
          : parcels.map((parcel) => ({
              preset_id: parcel.preset_id,
              quantity: parcel.quantity,
              instructions: parcel.instructions.trim() || undefined,
              length_in: parcel.length_in ? Number(parcel.length_in) : undefined,
              width_in: parcel.width_in ? Number(parcel.width_in) : undefined,
              height_in: parcel.height_in ? Number(parcel.height_in) : undefined,
              weight_lb: parcel.weight_lb ? Number(parcel.weight_lb) : undefined,
            })),
      declared_value_cents: parseDeclaredCents(declared),
      special_instructions: instructions.trim() || undefined,
      additional_stops: extraStop.formatted.trim() ? [toPayload(extraStop)] : undefined,
      promo_code: promo.trim() || undefined,
      scheduled_at:
        scheduleMode === "now" ? new Date().toISOString() : new Date(scheduledAt).toISOString(),
      schedule_mode: scheduleMode,
      anonymous_session_id: getVisitorSessionId() ?? undefined,
      visitor_session_id: getVisitorSessionId() ?? undefined,
      tracking: getVisitorTrackingPayload(),
    }),
    [
      pickup,
      dropoff,
      extraStop,
      vehicleClass,
      bookingMode,
      parcels,
      declared,
      instructions,
      promo,
      scheduleMode,
      scheduledAt,
    ]
  );

  useEffect(() => {
    if (step !== "details") return;
    const mapsOn = Boolean(publicEnv.googleMapsApiKey);
    if (!placeChosen(pickup, mapsOn) || !placeChosen(dropoff, mapsOn)) {
      setLiveFare(null);
      return;
    }
    if (extraStop.formatted.trim() && !placeChosen(extraStop, mapsOn)) {
      setLiveFare(null);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      previewQuote(quotePayload)
        .then((fare) => {
          if (!cancelled)
            setLiveFare({ amount_display: fare.amount_display, distance_km: fare.distance_km });
        })
        .catch(() => {
          if (!cancelled) setLiveFare(null);
        });
    }, 450);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [quotePayload, step, pickup, dropoff, extraStop]);

  async function onGetQuote() {
    const mapsOn = Boolean(publicEnv.googleMapsApiKey);
    if (!placeChosen(pickup, mapsOn)) {
      setError("Choose the pickup address from the Google suggestions.");
      return;
    }
    if (!placeChosen(dropoff, mapsOn)) {
      setError("Choose the drop-off address from the Google suggestions.");
      return;
    }
    if (extraStop.formatted.trim() && !placeChosen(extraStop, mapsOn)) {
      setError("Choose the extra stop from the Google suggestions, or clear it.");
      return;
    }
    if (scheduleMode === "later" && Number.isNaN(new Date(scheduledAt).getTime())) {
      setError("Pick a pickup time between 6:00 and 22:00.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await createQuote(quotePayload);
      setQuote(result);
      setStep("quote");
    } catch (err) {
      setError(humanQuoteError(err instanceof Error ? err.message : "Could not get quote"));
    } finally {
      setLoading(false);
    }
  }

  async function onConfirmAndPay() {
    if (!quote || !userId || !email) {
      setError("Sign in with a verified email to continue.");
      return;
    }
    if (!terms || !privacy || !dangerous) {
      setError("Accept all declarations to continue.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("missing_token");
      const booking = await startBooking(token, {
        quote_id: quote.quote_id,
        email,
        phone: phone.trim(),
        clerk_user_id: userId,
        terms_accepted: terms,
        privacy_accepted: privacy,
        dangerous_goods_confirmed: dangerous,
        consent_at: new Date().toISOString(),
        anonymous_session_id: getVisitorSessionId() ?? undefined,
      });
      if (booking.checkout_url) {
        window.location.href = booking.checkout_url;
        return;
      }
      if (booking.mock_checkout) {
        const confirmation = await mockCompleteCheckout(quote.quote_id);
        setTrackingNumber(confirmation.tracking_number);
        setStep("confirmed");
        return;
      }
      throw new Error("payment_unavailable");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Booking failed");
    } finally {
      setLoading(false);
    }
  }

  if (step === "confirmed") {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-white p-8 text-center shadow-sm">
        <CustomerMotion name="shipment" size={150} />
        <h1 className="text-2xl font-bold text-primary">Booking confirmed</h1>
        <p className="mt-2 text-sm text-muted">
          Your delivery is booked and will appear on your dashboard.
        </p>
        <p className="mt-6 font-mono text-lg font-semibold text-secondary">{trackingNumber}</p>
        <p className="mt-1 text-xs text-muted">Tracking number</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            href={`/track/${trackingNumber}`}
            className="rounded-xl border border-primary/10 px-5 py-3 text-sm font-semibold text-primary"
          >
            Track shipment
          </Link>
          <Link
            href="/dashboard"
            className="rounded-xl bg-secondary px-5 py-3 text-sm font-semibold text-white hover:bg-secondary/90"
          >
            Back to dashboard
          </Link>
          <button
            type="button"
            onClick={() => {
              setStep("details");
              setQuote(null);
              setTrackingNumber("");
              setPickup({ formatted: "" });
              setDropoff({ formatted: "" });
            }}
            className="rounded-xl border border-primary/10 px-5 py-3 text-sm font-semibold text-primary"
          >
            Book another
          </button>
        </div>
      </div>
    );
  }

  return (
    <GoogleMapsProvider apiKey={publicEnv.googleMapsApiKey}>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-primary">Book a delivery</h1>
        <p className="mt-1 text-sm text-muted">
          Get an instant quote and pay — all without leaving your customer portal.
        </p>
      </div>

      <ol className="mb-8 flex gap-2 text-xs font-medium" aria-label="Booking steps">
        {(["details", "quote", "checkout"] as const).map((s, i) => (
          <li
            key={s}
            aria-current={step === s ? "step" : undefined}
            className={cn(
              "rounded-full px-3 py-1 capitalize",
              step === s ? "bg-secondary text-white" : "bg-white text-muted"
            )}
          >
            {i + 1}. {s}
          </li>
        ))}
      </ol>

      {error && (
        <div
          className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
          aria-live="polite"
        >
          {error}
        </div>
      )}

      {step === "details" && (
        <section className="space-y-6 rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Pickup</span>
              <AddressAutocompleteInput
                id="customer-pickup"
                value={pickup.formatted}
                onChange={(v) => {
                  setPickup((p) => editAddress(p, v));
                  setQuote(null);
                }}
                onPlaceSelect={(next) => {
                  setPickup(next);
                  setQuote(null);
                }}
                placeholder="Pickup address"
                apiKey={publicEnv.googleMapsApiKey}
              />
              {pickup.postal ? (
                <p className="mt-1 text-xs text-muted">Google · {pickup.postal}</p>
              ) : null}
            </label>
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Drop-off</span>
              <AddressAutocompleteInput
                id="customer-dropoff"
                value={dropoff.formatted}
                onChange={(v) => {
                  setDropoff((p) => editAddress(p, v));
                  setQuote(null);
                }}
                onPlaceSelect={(next) => {
                  setDropoff(next);
                  setQuote(null);
                }}
                placeholder="Delivery address"
                apiKey={publicEnv.googleMapsApiKey}
              />
              {dropoff.postal ? (
                <p className="mt-1 text-xs text-muted">Google · {dropoff.postal}</p>
              ) : null}
            </label>
          </div>

          <label className="block text-sm">
            <span className="mb-2 block font-medium text-primary">Extra stop (optional)</span>
            <AddressAutocompleteInput
              id="customer-extra-stop"
              value={extraStop.formatted}
              onChange={(v) => {
                setExtraStop((p) => editAddress(p, v));
                setQuote(null);
              }}
              onPlaceSelect={(next) => {
                setExtraStop(next);
                setQuote(null);
              }}
              placeholder="Stop between pickup and drop-off"
              apiKey={publicEnv.googleMapsApiKey}
            />
            {extraStop.postal ? (
              <p className="mt-1 text-xs text-muted">Google · {extraStop.postal}</p>
            ) : null}
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label htmlFor="customer-vehicle" className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Vehicle</span>
              <select
                id="customer-vehicle"
                value={vehicleClass}
                onChange={(e) => {
                  setVehicleClass(e.target.value);
                  setQuote(null);
                }}
                className={`w-full rounded-xl border border-primary/10 px-4 py-3 ${FOCUS_RING}`}
              >
                {vehicles.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                    {v.included_km ? ` · includes ${v.included_km} km` : ""}
                  </option>
                ))}
              </select>
            </label>
            <div className="block text-sm">
              <span className="mb-2 block font-medium text-primary">What are we moving</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={`flex-1 rounded-xl border px-3 py-3 text-sm ${bookingMode === "parcels" ? "border-secondary bg-secondary/10" : "border-primary/10"}`}
                  onClick={() => {
                    setBookingMode("parcels");
                    setQuote(null);
                  }}
                >
                  Parcels
                </button>
                <button
                  type="button"
                  className={`flex-1 rounded-xl border px-3 py-3 text-sm ${bookingMode === "vehicle" ? "border-secondary bg-secondary/10" : "border-primary/10"}`}
                  onClick={() => {
                    setBookingMode("vehicle");
                    setQuote(null);
                  }}
                >
                  Whole vehicle
                </button>
              </div>
            </div>
          </div>

          {bookingMode === "parcels" &&
            (() => {
              const current = vehicles.find((item) => item.id === vehicleClass);
              const fitsHere =
                !current ||
                parcels.every((draft) =>
                  pieceFits(
                    current,
                    draft,
                    presets.find((preset) => preset.id === draft.preset_id)
                  )
                );
              const next = fitsHere
                ? null
                : nextFittingVehicle(
                    vehicles.filter((item) => item.id !== vehicleClass),
                    parcels,
                    presets
                  );
              if (!next) return null;
              return (
                <p className="text-sm text-primary">
                  This piece fits{" "}
                  <button
                    type="button"
                    className="font-semibold text-secondary underline"
                    onClick={() => {
                      setVehicleClass(next.id);
                      setQuote(null);
                    }}
                  >
                    {next.label}
                  </button>
                  .
                </p>
              );
            })()}

          {bookingMode === "parcels" && (
            <ParcelEditor
              parcels={parcels}
              presets={presets.filter((preset) => {
                const vehicle = vehicles.find((item) => item.id === vehicleClass);
                const allowed = vehicle?.allowed_presets;
                return !allowed?.length || allowed.includes(preset.id);
              })}
              onChange={(next) => {
                setParcels(next);
                setQuote(null);
              }}
            />
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Schedule</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  aria-pressed={scheduleMode === "now"}
                  onClick={() => setScheduleMode("now")}
                  className={cn(
                    "flex-1 rounded-xl border px-3 py-3 text-sm font-medium",
                    FOCUS_RING,
                    scheduleMode === "now"
                      ? "border-secondary bg-secondary/10 text-secondary"
                      : "border-primary/10"
                  )}
                >
                  ASAP
                </button>
                <button
                  type="button"
                  aria-pressed={scheduleMode === "later"}
                  onClick={() => setScheduleMode("later")}
                  className={cn(
                    "flex-1 rounded-xl border px-3 py-3 text-sm font-medium",
                    FOCUS_RING,
                    scheduleMode === "later"
                      ? "border-secondary bg-secondary/10 text-secondary"
                      : "border-primary/10"
                  )}
                >
                  Schedule
                </button>
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">
                Declared value for the whole booking, CAD (optional)
              </span>
              <input
                inputMode="decimal"
                value={declared}
                onChange={(e) => setDeclared(e.target.value)}
                className="w-full rounded-xl border border-primary/10 px-4 py-3"
                placeholder="Or type dollars"
              />
              <FieldSuggestions value={declared} onChange={setDeclared} options={VALUE_OPTIONS} />
            </label>
          </div>

          <label className="block text-sm">
            <span className="mb-2 block font-medium text-primary">
              Instructions for the driver (optional)
            </span>
            <input
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              className="w-full rounded-xl border border-primary/10 px-4 py-3"
              placeholder="Or type your own note"
            />
            <FieldSuggestions
              value={instructions}
              onChange={setInstructions}
              options={INSTRUCTION_OPTIONS}
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Phone</span>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(formatCanadianPhone(e.target.value))}
                className="w-full rounded-xl border border-primary/10 px-4 py-3"
                placeholder="+1 xxx-xxx-xxxx"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Promo code (optional)</span>
              <input
                value={promo}
                onChange={(e) => setPromo(e.target.value.toUpperCase())}
                className="w-full rounded-xl border border-primary/10 px-4 py-3"
                placeholder="Promo code"
                autoCapitalize="characters"
              />
            </label>
          </div>

          {scheduleMode === "later" && (
            <div className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Pickup date & time</span>
              <DateTimePickerSeparateField
                value={scheduledAt}
                onChange={setScheduledAt}
                hourFormat={12}
                timeInterval={30}
                minDate={new Date()}
                minTime="06:00"
                maxTime="22:00"
                datePlaceholder="Pick a date"
                timePlaceholder="Pick time"
              />
            </div>
          )}

          {liveFare ? (
            <p className="text-sm font-medium text-primary">
              Estimated fare {liveFare.amount_display}
              {liveFare.distance_km != null ? ` · ${liveFare.distance_km} km` : ""}. Save the quote
              before paying.
            </p>
          ) : null}

          <button
            type="button"
            disabled={loading}
            onClick={() => void onGetQuote()}
            className={`w-full rounded-xl bg-secondary py-3 text-sm font-semibold text-white disabled:opacity-60 sm:w-auto sm:px-8 ${FOCUS_RING}`}
          >
            {loading ? "Getting quote…" : "Get instant quote"}
          </button>
        </section>
      )}

      {step === "quote" && quote && (
        <section className="rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-primary">Your quote</h2>
          <p className="mt-4 text-3xl font-bold text-secondary">
            {quote.amount_display || formatCents(quote.amount_cents)}
          </p>
          {quote.distance_km != null && (
            <p className="mt-1 text-sm text-muted">≈ {quote.distance_km} km quoted</p>
          )}
          <ul className="mt-4 space-y-2 text-sm text-muted">
            <li>From: {pickup.formatted}</li>
            <li>To: {dropoff.formatted}</li>
            {extraStop.formatted ? <li>Stop: {extraStop.formatted}</li> : null}
          </ul>
          {quote.pricing_breakdown && quote.pricing_breakdown.length > 0 && (
            <ul className="mt-4 space-y-1 border-t border-primary/10 pt-4 text-sm">
              {quote.pricing_breakdown.map((line) => (
                <li key={line.code} className="flex justify-between">
                  <span className="text-muted">{line.label}</span>
                  <span>{formatCents(line.amount_cents)}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setStep("checkout")}
              className={`rounded-xl bg-secondary px-6 py-3 text-sm font-semibold text-white ${FOCUS_RING}`}
            >
              Continue to payment
            </button>
            <button
              type="button"
              onClick={() => {
                setQuote(null);
                setStep("details");
              }}
              className="rounded-xl border border-primary/10 px-6 py-3 text-sm font-medium"
            >
              Edit details
            </button>
          </div>
        </section>
      )}

      {step === "checkout" && quote && (
        <section className="rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-primary">Confirm & pay</h2>
          <p className="mt-2 text-sm text-muted">
            Total: <strong>{quote.amount_display || formatCents(quote.amount_cents)}</strong>
          </p>
          <p className="mt-1 text-sm text-muted">Signed in as {email}</p>
          <p className="mt-1 text-sm text-muted">{phone || "No phone on this booking"}</p>

          <fieldset className="mt-6 space-y-3 text-sm">
            <legend className="sr-only">Required declarations</legend>
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={terms}
                onChange={(e) => setTerms(e.target.checked)}
                className={FOCUS_RING}
              />
              <span>I agree to the Porterchain Terms of Service.</span>
            </label>
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={privacy}
                onChange={(e) => setPrivacy(e.target.checked)}
                className={FOCUS_RING}
              />
              <span>I agree to the Privacy Policy.</span>
            </label>
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={dangerous}
                onChange={(e) => setDangerous(e.target.checked)}
                className={FOCUS_RING}
              />
              <span>I confirm this shipment does not contain undeclared dangerous goods.</span>
            </label>
          </fieldset>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => void onConfirmAndPay()}
              className="rounded-xl bg-secondary px-6 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              {loading ? "Processing…" : "Confirm & pay"}
            </button>
            <button
              type="button"
              onClick={() => setStep("quote")}
              className="rounded-xl border border-primary/10 px-6 py-3 text-sm font-medium"
            >
              Back
            </button>
          </div>
        </section>
      )}
    </GoogleMapsProvider>
  );
}
