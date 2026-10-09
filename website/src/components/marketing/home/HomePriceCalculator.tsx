"use client";

import { useId, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ArrowRight, Loader2 } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { quoteSignUpPath } from "@/data/portal-links";
import {
  CALCULATOR_VEHICLES,
  normalizeFsa,
  type CalculatorVehicle,
} from "@/lib/marketing/calculator-lead";
import { CONVERSION_EVENTS, trackConversion } from "@/lib/marketing/conversion";
import { HOME_PRICE_ANCHOR_ID } from "@/lib/marketing/price-bar";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";
import { cn } from "@/lib/utils";

type Estimate = {
  amount_cents: number;
  tax_cents: number;
  distance_km?: number | null;
  vehicle_class: string;
  pickup_fsa: string;
  dropoff_fsa: string;
  disclaimer?: string;
};

const KNOWN_ERRORS = new Set([
  "pickup_outside_service_area",
  "dropoff_outside_service_area",
  "vehicle_class_not_available",
  "rate_limited",
  "calculator_disabled",
]);

const inputClass =
  "mt-1.5 block w-full rounded-xl border border-primary/20 bg-white px-3.5 py-3 text-base uppercase tracking-wide text-primary placeholder:normal-case placeholder:tracking-normal placeholder:text-muted/70 outline-none transition-colors focus-visible:border-secondary focus-visible:ring-2 focus-visible:ring-secondary/30";

/**
 * Homepage hero calculator (the only client island above the fold).
 * Two postal codes + vehicle → instant price from the existing estimate API (/api/estimate).
 * No PII is collected here; "Book" hands off to sign-up, "See full breakdown" to the
 * calculator page with the trip prefilled.
 */
export default function HomePriceCalculator() {
  const t = useTranslations("homePage.calculator");
  const locale = useLocale();
  const ids = useId();
  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [vehicle, setVehicle] = useState<CalculatorVehicle>("cargo_van");
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [pricing, setPricing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const money = (cents: number) =>
    new Intl.NumberFormat(locale === "fr" ? "fr-CA" : "en-CA", {
      style: "currency",
      currency: "CAD",
    }).format(cents / 100);

  async function getPrice(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const p = normalizeFsa(pickup);
    const d = normalizeFsa(dropoff);
    if (!p || !d) {
      setEstimate(null);
      setError(t("errors.invalidPostal"));
      return;
    }
    setPricing(true);
    try {
      const res = await fetch("/api/estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pickup_postal: p, dropoff_postal: d, vehicle_class: vehicle }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setEstimate(null);
        const code = typeof data.error === "string" ? data.error : "";
        setError(KNOWN_ERRORS.has(code) ? t(`errors.${code}`) : t("errors.generic"));
        return;
      }
      setEstimate(data as Estimate);
      trackConversion(CONVERSION_EVENTS.CALCULATOR_ESTIMATE, {
        vehicle,
        pickup_fsa: p,
        dropoff_fsa: d,
        amount_cents: data.amount_cents,
        source_section: "home-hero",
      });
    } catch {
      setEstimate(null);
      setError(t("errors.network"));
    } finally {
      setPricing(false);
    }
  }

  const vehicleLabel = (id: string) =>
    CALCULATOR_VEHICLES.some((v) => v.id === id) ? t(`vehicles.${id}.label`) : id;

  const detailsHref = estimate
    ? `/delivery-cost-calculator?pickup=${estimate.pickup_fsa}&dropoff=${estimate.dropoff_fsa}&vehicle=${estimate.vehicle_class}`
    : "/delivery-cost-calculator";

  return (
    <div
      id={HOME_PRICE_ANCHOR_ID}
      className="scroll-mt-[calc(var(--nav-height)+1rem)] rounded-3xl bg-white p-5 text-primary shadow-[0_24px_60px_rgba(2,8,23,0.35)] ring-1 ring-primary/5 sm:p-6"
    >
      <h2 className="text-xl font-semibold tracking-tight">{t("title")}</h2>
      <p className="mt-0.5 text-sm text-muted">{t("subtitle")}</p>

      <form onSubmit={getPrice} className="mt-4 space-y-4" noValidate data-testid="home-price-form">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor={`${ids}-pickup`} className="text-sm font-medium">
              {t("pickup")}
            </label>
            <input
              id={`${ids}-pickup`}
              name="pickup"
              value={pickup}
              onChange={(e) => setPickup(e.target.value)}
              placeholder={t("pickupPlaceholder")}
              autoComplete="postal-code"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={7}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor={`${ids}-dropoff`} className="text-sm font-medium">
              {t("dropoff")}
            </label>
            <input
              id={`${ids}-dropoff`}
              name="dropoff"
              value={dropoff}
              onChange={(e) => setDropoff(e.target.value)}
              placeholder={t("dropoffPlaceholder")}
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={7}
              className={inputClass}
            />
          </div>
        </div>

        <fieldset>
          <legend className="text-sm font-medium">{t("vehicle")}</legend>
          <div className="mt-1.5 grid grid-cols-3 gap-2">
            {CALCULATOR_VEHICLES.map((v) => (
              <label
                key={v.id}
                className={cn(
                  "flex min-h-[3.25rem] cursor-pointer flex-col justify-center rounded-xl border px-2.5 py-2 text-center transition-colors sm:text-left",
                  "border-primary/15 hover:border-secondary/40",
                  "has-[:checked]:border-secondary has-[:checked]:bg-secondary/[0.06] has-[:checked]:ring-1 has-[:checked]:ring-secondary",
                  "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-secondary/40"
                )}
              >
                <input
                  type="radio"
                  name="vehicle"
                  value={v.id}
                  checked={vehicle === v.id}
                  onChange={() => setVehicle(v.id)}
                  className="sr-only"
                />
                <span className="text-sm font-semibold leading-tight">
                  {t(`vehicles.${v.id}.label`)}
                </span>
                <span className="mt-0.5 hidden text-xs leading-snug text-muted sm:block">
                  {t(`vehicles.${v.id}.hint`)}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <button
          type="submit"
          disabled={pricing}
          className="inline-flex min-h-[3rem] w-full items-center justify-center gap-2 rounded-full bg-secondary px-6 text-base font-semibold text-white shadow-lg shadow-secondary/25 transition-colors hover:bg-[#1a47bf] disabled:cursor-wait disabled:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
        >
          {pricing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden />
              {t("pricing")}
            </>
          ) : (
            <>
              {t("submit")}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </>
          )}
        </button>
      </form>

      <div aria-live="polite">
        {error ? (
          <p role="alert" className="mt-4 rounded-xl bg-red-50 px-3.5 py-2.5 text-sm text-red-800">
            {error}
          </p>
        ) : null}
        {estimate ? (
          <div
            className="mt-4 rounded-xl border border-secondary/20 bg-secondary/[0.04] p-4"
            data-testid="home-price-result"
          >
            <p className="text-sm font-medium text-muted">{t("resultLabel")}</p>
            <p className="mt-0.5 text-3xl font-bold tracking-tight">
              {money(estimate.amount_cents)}
            </p>
            <p className="mt-1 text-sm text-muted">
              {t("resultMeta", {
                pickup: estimate.pickup_fsa,
                dropoff: estimate.dropoff_fsa,
                vehicle: vehicleLabel(estimate.vehicle_class),
              })}
              {typeof estimate.distance_km === "number"
                ? ` · ${t("distance", { km: Math.round(estimate.distance_km) })}`
                : ""}
              {" · "}
              {t("taxIncluded", { tax: money(estimate.tax_cents) })}
            </p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <Link
                href={quoteSignUpPath({ from: "home-price", vehicle: estimate.vehicle_class })}
                onClick={() =>
                  track(ANALYTICS_EVENTS.CTA_CLICK, {
                    source_section: "home-price",
                    cta_label: "book_this_delivery",
                  })
                }
                className="inline-flex min-h-[2.75rem] flex-1 items-center justify-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-white hover:bg-[#152238] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                {t("book")}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <Link
                href={detailsHref}
                className="inline-flex min-h-[2.75rem] flex-1 items-center justify-center rounded-full border border-primary/15 bg-white px-5 text-sm font-semibold text-primary hover:border-secondary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
              >
                {t("details")}
              </Link>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted">
              {locale === "en" && estimate.disclaimer
                ? estimate.disclaimer
                : t("disclaimerFallback")}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
