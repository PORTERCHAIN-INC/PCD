"use client";

import MarketingConsentCheckbox from "@/components/forms/MarketingConsentCheckbox";
import { useEffect, useRef, useState } from "react";
import { Link } from "@/i18n/navigation";
import {
  CALCULATOR_INDUSTRIES,
  CALCULATOR_VEHICLES,
  EMPTY_LEAD_FORM,
  MONTHLY_VOLUMES,
  buildLeadPayload,
  formatCad,
  isCalculatorIndustry,
  isCalculatorVehicle,
  normalizeFsa,
  validateLeadForm,
  type CalculatorVehicle,
  type LeadErrors,
  type LeadForm,
} from "@/lib/marketing/calculator-lead";
import { CONVERSION_EVENTS, trackConversion } from "@/lib/marketing/conversion";
import { getStoredAttribution } from "@/lib/seo/attribution";
import { getOrCreateVisitorId } from "@/lib/visitor-tracking";

type Estimate = {
  amount_cents: number;
  subtotal_cents: number;
  tax_cents: number;
  distance_km?: number | null;
  included_km?: number | null;
  vehicle_class: string;
  pickup_fsa: string;
  dropoff_fsa: string;
  lines: Array<{ code: string; label: string; amount_cents: number }>;
  disclaimer: string;
};

const ERROR_COPY: Record<string, string> = {
  pickup_outside_service_area: "That pickup postal code is outside our GTA coverage.",
  dropoff_outside_service_area: "That drop-off postal code is outside our GTA coverage.",
  vehicle_class_not_available: "That vehicle is not available for instant pricing.",
  rate_limited: "Too many price checks in a minute — please wait a moment and try again.",
  calculator_disabled: "Instant pricing is paused right now. Please contact us for a quote.",
};

const inputClass =
  "mt-1 block w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-base text-primary outline-none focus:border-secondary";

export default function PriceCalculator() {
  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [vehicle, setVehicle] = useState<CalculatorVehicle>("sedan_suv");
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [pricing, setPricing] = useState(false);
  const [priceError, setPriceError] = useState<string | null>(null);

  const [form, setForm] = useState<LeadForm>(EMPTY_LEAD_FORM);
  const [errors, setErrors] = useState<LeadErrors>({});
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const formShownAt = useRef<number>(0);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const p = normalizeFsa(q.get("pickup"));
    const d = normalizeFsa(q.get("dropoff"));
    const v = q.get("vehicle");
    const industry = q.get("industry");
    if (p) setPickup(p);
    if (d) setDropoff(d);
    if (isCalculatorVehicle(v)) setVehicle(v);
    if (industry && isCalculatorIndustry(industry)) {
      setForm((f) => ({ ...f, industry }));
    }
  }, []);

  useEffect(() => {
    // Spam signal: humans need a few seconds between page load and submit.
    formShownAt.current = Date.now();
  }, []);

  async function getPrice(event: React.FormEvent) {
    event.preventDefault();
    setPriceError(null);
    const p = normalizeFsa(pickup);
    const d = normalizeFsa(dropoff);
    if (!p || !d) {
      setPriceError("Enter a valid postal code (for example M5V 2T6) for both ends.");
      return;
    }
    setPricing(true);
    try {
      const res = await fetch("/api/estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pickup_postal: p, dropoff_postal: d, vehicle_class: vehicle }),
      });
      const data = await res.json();
      if (!res.ok) {
        setEstimate(null);
        setPriceError(ERROR_COPY[data.error] ?? "We could not price that trip. Please try again.");
        return;
      }
      setEstimate(data as Estimate);
      trackConversion(CONVERSION_EVENTS.CALCULATOR_ESTIMATE, {
        vehicle,
        pickup_fsa: p,
        dropoff_fsa: d,
        amount_cents: data.amount_cents,
      });
    } catch {
      setPriceError("We could not reach the pricing service. Please try again.");
    } finally {
      setPricing(false);
    }
  }

  async function sendLead(event: React.FormEvent) {
    event.preventDefault();
    setSendError(null);
    const found = validateLeadForm(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    setSending(true);
    let heroVariant: string | undefined;
    try {
      heroVariant = window.sessionStorage.getItem("pc_hero_variant") ?? undefined;
    } catch {
      heroVariant = undefined;
    }
    const payload = buildLeadPayload({
      form,
      attribution: getStoredAttribution(),
      estimate: estimate
        ? {
            pickupFsa: estimate.pickup_fsa,
            dropoffFsa: estimate.dropoff_fsa,
            vehicle: estimate.vehicle_class,
            amountCents: estimate.amount_cents,
          }
        : null,
      visitorId: getOrCreateVisitorId(),
      heroVariant,
      formElapsedMs: formShownAt.current ? Date.now() - formShownAt.current : 0,
    });
    try {
      const res = await fetch("/api/calculator-lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setSendError(
          data.error === "rate_limited"
            ? ERROR_COPY.rate_limited
            : "Please check the form and try again."
        );
        return;
      }
      setSent(true);
      trackConversion(CONVERSION_EVENTS.CALCULATOR_LEAD, {
        industry: form.industry,
        monthly_volume: form.monthlyVolume,
        marketing_consent: form.marketingConsent,
      });
    } catch {
      setSendError("We could not send the form. Please try again.");
    } finally {
      setSending(false);
    }
  }

  const set = <K extends keyof LeadForm>(key: K, value: LeadForm[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <form
        onSubmit={getPrice}
        className="rounded-3xl border border-primary/10 bg-white p-6 shadow-sm"
        aria-labelledby="calc-title"
      >
        <h2 id="calc-title" className="text-xl font-semibold text-primary">
          1. Get an instant price
        </h2>
        <p className="mt-1 text-sm text-muted">No sign-up or contact details needed.</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium text-primary">
            Pickup postal code
            <input
              className={inputClass}
              value={pickup}
              onChange={(e) => setPickup(e.target.value)}
              placeholder="M5V 2T6"
              autoComplete="off"
              maxLength={7}
              required
            />
          </label>
          <label className="text-sm font-medium text-primary">
            Drop-off postal code
            <input
              className={inputClass}
              value={dropoff}
              onChange={(e) => setDropoff(e.target.value)}
              placeholder="L5T 1A1"
              autoComplete="off"
              maxLength={7}
              required
            />
          </label>
        </div>
        <fieldset className="mt-5">
          <legend className="text-sm font-medium text-primary">Vehicle</legend>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            {CALCULATOR_VEHICLES.map((v) => (
              <label
                key={v.id}
                className={`cursor-pointer rounded-xl border p-3 text-sm ${
                  vehicle === v.id ? "border-secondary bg-secondary/5" : "border-primary/15"
                }`}
              >
                <input
                  type="radio"
                  name="vehicle"
                  value={v.id}
                  checked={vehicle === v.id}
                  onChange={() => setVehicle(v.id)}
                  className="sr-only"
                />
                <span className="block font-semibold text-primary">{v.label}</span>
                <span className="block text-xs text-muted">{v.hint}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <button
          type="submit"
          disabled={pricing}
          className="mt-6 w-full rounded-xl bg-secondary px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8] disabled:opacity-60"
        >
          {pricing ? "Calculating…" : "Show my price"}
        </button>
        {priceError ? (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {priceError}
          </p>
        ) : null}

        {estimate ? (
          <div className="mt-6 rounded-2xl bg-slate-50 p-5" aria-live="polite">
            <p className="text-sm text-muted">
              {estimate.pickup_fsa} → {estimate.dropoff_fsa}
              {estimate.distance_km ? ` · ${estimate.distance_km} km` : ""}
            </p>
            <p className="mt-1 text-4xl font-bold text-primary" data-testid="calculator-price">
              {formatCad(estimate.amount_cents)}{" "}
              <span className="text-base font-medium text-muted">CAD incl. HST</span>
            </p>
            <ul className="mt-3 space-y-1 text-sm text-primary/90">
              {estimate.lines.map((line) => (
                <li key={line.code} className="flex justify-between gap-4">
                  <span>{line.label}</span>
                  <span>{formatCad(line.amount_cents)}</span>
                </li>
              ))}
              <li className="flex justify-between gap-4 text-muted">
                <span>HST (13%)</span>
                <span>{formatCad(estimate.tax_cents)}</span>
              </li>
            </ul>
            <p className="mt-3 text-xs text-muted">{estimate.disclaimer}</p>
          </div>
        ) : null}
      </form>

      <div className="rounded-3xl border border-primary/10 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-primary">
          2. Lock in this rate for regular runs
        </h2>
        <p className="mt-1 text-sm text-muted">
          Tell us about your deliveries and our team will call you back with account pricing.
        </p>
        {sent ? (
          <div
            className="mt-6 rounded-2xl bg-emerald-50 p-5 text-sm text-emerald-900"
            role="status"
          >
            Thanks — your request is in. Our team will contact you about account pricing.{" "}
            <Link
              href="/sign-up?intent=merchant&from=calculator"
              className="font-semibold underline"
            >
              Open a business account now
            </Link>
            .
          </div>
        ) : (
          <form onSubmit={sendLead} noValidate className="mt-5 grid gap-4">
            <label className="text-sm font-medium text-primary">
              Business name
              <input
                className={inputClass}
                value={form.businessName}
                onChange={(e) => set("businessName", e.target.value)}
                autoComplete="organization"
              />
              {errors.businessName ? (
                <span className="text-xs text-red-700">{errors.businessName}</span>
              ) : null}
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium text-primary">
                Work email
                <input
                  type="email"
                  className={inputClass}
                  value={form.email}
                  onChange={(e) => set("email", e.target.value)}
                  autoComplete="email"
                />
                {errors.email ? <span className="text-xs text-red-700">{errors.email}</span> : null}
              </label>
              <label className="text-sm font-medium text-primary">
                Phone
                <input
                  type="tel"
                  className={inputClass}
                  value={form.phone}
                  onChange={(e) => set("phone", e.target.value)}
                  autoComplete="tel"
                />
                {errors.phone ? <span className="text-xs text-red-700">{errors.phone}</span> : null}
              </label>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium text-primary">
                Industry
                <select
                  className={inputClass}
                  value={form.industry}
                  onChange={(e) => set("industry", e.target.value)}
                >
                  <option value="">Choose…</option>
                  {CALCULATOR_INDUSTRIES.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.label}
                    </option>
                  ))}
                </select>
                {errors.industry ? (
                  <span className="text-xs text-red-700">{errors.industry}</span>
                ) : null}
              </label>
              <label className="text-sm font-medium text-primary">
                Deliveries per month
                <select
                  className={inputClass}
                  value={form.monthlyVolume}
                  onChange={(e) => set("monthlyVolume", e.target.value)}
                >
                  <option value="">Choose…</option>
                  {MONTHLY_VOLUMES.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
                {errors.monthlyVolume ? (
                  <span className="text-xs text-red-700">{errors.monthlyVolume}</span>
                ) : null}
              </label>
            </div>
            {/* Honeypot: hidden from people and assistive tech; bots fill it. */}
            <div aria-hidden="true" className="absolute -left-[10000px] h-px w-px overflow-hidden">
              <label>
                Website
                <input
                  tabIndex={-1}
                  autoComplete="off"
                  value={form.website}
                  onChange={(e) => set("website", e.target.value)}
                  name="website"
                />
              </label>
            </div>
            <MarketingConsentCheckbox
              id="calculator-marketing-consent"
              checked={form.marketingConsent}
              onChange={(v) => set("marketingConsent", v)}
            />
            <p className="text-xs text-muted">
              We use these details to reply to this request. See our{" "}
              <Link href="/privacy" className="underline">
                privacy policy
              </Link>
              .
            </p>
            <button
              type="submit"
              disabled={sending}
              className="rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              {sending ? "Sending…" : "Request a call back"}
            </button>
            {sendError ? (
              <p role="alert" className="text-sm text-red-700">
                {sendError}
              </p>
            ) : null}
          </form>
        )}
      </div>
    </div>
  );
}
