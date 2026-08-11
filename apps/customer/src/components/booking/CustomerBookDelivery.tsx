"use client";

import { useEffect, useState } from "react";
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
  mockCompleteCheckout,
  startBooking,
  type QuoteResult,
} from "@/lib/booking";
import { REBOOK_STORAGE_KEY } from "@/lib/api";
import { isClerkConfigured, publicEnv } from "@/lib/env";
import { cn } from "@/lib/utils";
import {
  captureVisitorHandoff,
  getVisitorSessionId,
  getVisitorTrackingPayload,
} from "@/lib/visitor-session";

const VEHICLES = [
  { id: "sedan", label: "Sedan" },
  { id: "suv", label: "SUV" },
  { id: "pickup", label: "Pickup" },
  { id: "cargoVan", label: "Cargo van" },
  { id: "highRoof", label: "High roof" },
  { id: "box16", label: "16' box truck" },
  { id: "box20", label: "20' box truck" },
];

const PACKAGES = [
  { id: "looseParcel", label: "Parcel" },
  { id: "documents", label: "Documents" },
  { id: "medical", label: "Medical" },
  { id: "furniture", label: "Furniture" },
  { id: "foodBeverage", label: "Food & beverage" },
];

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 focus-visible:ring-offset-2";

type Step = "details" | "quote" | "checkout" | "confirmed";

function toPayload(addr: BookingAddress) {
  return {
    formatted: addr.formatted,
    lat: addr.lat,
    lng: addr.lng,
    place_id: addr.placeId,
  };
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
  }, [searchParams]);

  const [step, setStep] = useState<Step>("details");
  const [pickup, setPickup] = useState<BookingAddress>({ formatted: "" });
  const [dropoff, setDropoff] = useState<BookingAddress>({ formatted: "" });
  const [vehicleClass, setVehicleClass] = useState("cargoVan");
  const [packageType, setPackageType] = useState("looseParcel");
  const [weightKg, setWeightKg] = useState("");
  const [scheduleMode, setScheduleMode] = useState<"now" | "later">("now");
  const [scheduledAt, setScheduledAt] = useState(defaultScheduledAt);
  const [phone, setPhone] = useState("");
  const [terms, setTerms] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [dangerous, setDangerous] = useState(false);
  const [quote, setQuote] = useState<QuoteResult | null>(null);
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
      if (payload.vehicle_class) setVehicleClass(payload.vehicle_class);
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
        if (resumed.vehicle_class) setVehicleClass(resumed.vehicle_class);
        if (resumed.package_type) setPackageType(resumed.package_type);
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

  async function onGetQuote() {
    if (!pickup.formatted || !dropoff.formatted) {
      setError("Enter pickup and drop-off addresses.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const scheduled =
        scheduleMode === "now" ? new Date().toISOString() : new Date(scheduledAt).toISOString();
      const sessionId = getVisitorSessionId() ?? undefined;
      const result = await createQuote({
        pickup: toPayload(pickup),
        dropoff: toPayload(dropoff),
        vehicle_class: vehicleClass,
        package_type: packageType,
        weight_kg: weightKg ? Number(weightKg) : undefined,
        scheduled_at: scheduled,
        schedule_mode: scheduleMode,
        anonymous_session_id: sessionId,
        visitor_session_id: sessionId,
        tracking: getVisitorTrackingPayload(),
      });
      setQuote(result);
      setStep("quote");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not get quote");
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
                onChange={(v) => setPickup((p) => ({ ...p, formatted: v }))}
                onPlaceSelect={setPickup}
                placeholder="Pickup address"
                apiKey={publicEnv.googleMapsApiKey}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Drop-off</span>
              <AddressAutocompleteInput
                id="customer-dropoff"
                value={dropoff.formatted}
                onChange={(v) => setDropoff((p) => ({ ...p, formatted: v }))}
                onPlaceSelect={setDropoff}
                placeholder="Delivery address"
                apiKey={publicEnv.googleMapsApiKey}
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label htmlFor="customer-vehicle" className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Vehicle</span>
              <select
                id="customer-vehicle"
                value={vehicleClass}
                onChange={(e) => setVehicleClass(e.target.value)}
                className={`w-full rounded-xl border border-primary/10 px-4 py-3 ${FOCUS_RING}`}
              >
                {VEHICLES.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
            </label>
            <label htmlFor="customer-package" className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Package type</span>
              <select
                id="customer-package"
                value={packageType}
                onChange={(e) => setPackageType(e.target.value)}
                className={`w-full rounded-xl border border-primary/10 px-4 py-3 ${FOCUS_RING}`}
              >
                {PACKAGES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Weight (kg, optional)</span>
              <input
                type="number"
                min="0"
                step="0.1"
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
                className="w-full rounded-xl border border-primary/10 px-4 py-3"
                placeholder="e.g. 5"
              />
            </label>
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
            <p className="mt-1 text-sm text-muted">≈ {quote.distance_km} km</p>
          )}
          <ul className="mt-4 space-y-2 text-sm text-muted">
            <li>From: {pickup.formatted}</li>
            <li>To: {dropoff.formatted}</li>
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
              onClick={() => setStep("details")}
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

          <label className="mt-6 block text-sm">
            <span className="mb-2 block font-medium text-primary">Phone (optional)</span>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-xl border border-primary/10 px-4 py-3"
              placeholder="+1 …"
            />
          </label>

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
