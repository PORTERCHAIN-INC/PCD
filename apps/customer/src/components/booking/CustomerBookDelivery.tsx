"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  AddressAutocompleteInput,
  GoogleMapsProvider,
  type BookingAddress,
} from "@porterchain/maps";
import {
  createQuote,
  formatCents,
  mockCompleteCheckout,
  startBooking,
  type QuoteResult,
} from "@/lib/booking";
import { publicEnv } from "@/lib/env";
import { cn } from "@/lib/utils";

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
  const { getToken, userId } = useAuth();
  const { user } = useUser();
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

  const email = user?.primaryEmailAddress?.emailAddress ?? "";

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
      const result = await createQuote({
        pickup: toPayload(pickup),
        dropoff: toPayload(dropoff),
        vehicle_class: vehicleClass,
        package_type: packageType,
        weight_kg: weightKg ? Number(weightKg) : undefined,
        scheduled_at: scheduled,
        schedule_mode: scheduleMode,
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
        <p className="mt-2 text-sm text-muted">Your delivery is booked and will appear on your dashboard.</p>
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

      <ol className="mb-8 flex gap-2 text-xs font-medium">
        {(["details", "quote", "checkout"] as const).map((s, i) => (
          <li
            key={s}
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
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Vehicle</span>
              <select
                value={vehicleClass}
                onChange={(e) => setVehicleClass(e.target.value)}
                className="w-full rounded-xl border border-primary/10 px-4 py-3"
              >
                {VEHICLES.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-2 block font-medium text-primary">Package type</span>
              <select
                value={packageType}
                onChange={(e) => setPackageType(e.target.value)}
                className="w-full rounded-xl border border-primary/10 px-4 py-3"
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
                  onClick={() => setScheduleMode("now")}
                  className={cn(
                    "flex-1 rounded-xl border px-3 py-3 text-sm font-medium",
                    scheduleMode === "now"
                      ? "border-secondary bg-secondary/10 text-secondary"
                      : "border-primary/10"
                  )}
                >
                  ASAP
                </button>
                <button
                  type="button"
                  onClick={() => setScheduleMode("later")}
                  className={cn(
                    "flex-1 rounded-xl border px-3 py-3 text-sm font-medium",
                    scheduleMode === "later"
                      ? "border-secondary bg-secondary/10 text-secondary"
                      : "border-primary/10"
                  )}
                >
                  Schedule
                </button>
              </div>
              {scheduleMode === "later" && (
                <input
                  type="datetime-local"
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-primary/10 px-4 py-3"
                />
              )}
            </div>
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={() => void onGetQuote()}
            className="w-full rounded-xl bg-secondary py-3 text-sm font-semibold text-white disabled:opacity-60 sm:w-auto sm:px-8"
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
              className="rounded-xl bg-secondary px-6 py-3 text-sm font-semibold text-white"
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

          <div className="mt-6 space-y-3 text-sm">
            <label className="flex items-start gap-3">
              <input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} />
              <span>I agree to the Porterchain Terms of Service.</span>
            </label>
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={privacy}
                onChange={(e) => setPrivacy(e.target.checked)}
              />
              <span>I agree to the Privacy Policy.</span>
            </label>
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={dangerous}
                onChange={(e) => setDangerous(e.target.checked)}
              />
              <span>I confirm this shipment does not contain undeclared dangerous goods.</span>
            </label>
          </div>

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
