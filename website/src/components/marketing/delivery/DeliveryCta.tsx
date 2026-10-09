"use client";

import { Link } from "@/i18n/navigation";
import { CONVERSION_EVENTS, trackConversion } from "@/lib/marketing/conversion";

/** Per-vertical CTA pair: live price (primary) + business account (secondary). */
export default function DeliveryCta({
  label,
  pitch,
  industry,
  area,
  pickupFsa,
  from,
  tone = "light",
}: {
  label: string;
  pitch: string;
  industry?: string;
  area?: string;
  pickupFsa?: string;
  from: string;
  /** "dark" for use inside the navy DeliveryHero. */
  tone?: "light" | "dark";
}) {
  const dark = tone === "dark";
  const params = new URLSearchParams({ from });
  if (industry) params.set("industry", industry);
  if (pickupFsa) params.set("pickup", pickupFsa);
  const calculatorHref = `/delivery-cost-calculator?${params.toString()}`;
  const signUpHref = `/sign-up?intent=merchant&from=${encodeURIComponent(from)}`;
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
      <Link
        href={calculatorHref}
        onClick={() =>
          trackConversion(CONVERSION_EVENTS.DELIVERY_CTA_CLICK, {
            cta: "calculator",
            industry,
            area,
          })
        }
        className={`inline-flex min-h-[var(--touch-min)] items-center justify-center rounded-full bg-secondary px-6 py-3 text-base font-semibold text-white shadow-lg shadow-secondary/25 transition-[background-color,transform] hover:bg-[#1d4ed8] motion-safe:hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 ${
          dark
            ? "focus-visible:ring-white focus-visible:ring-offset-primary"
            : "focus-visible:ring-secondary"
        }`}
      >
        {label}
      </Link>
      <Link
        href={signUpHref}
        onClick={() =>
          trackConversion(CONVERSION_EVENTS.DELIVERY_CTA_CLICK, { cta: "signup", industry, area })
        }
        className={`inline-flex min-h-[var(--touch-min)] items-center justify-center rounded-full border px-6 py-3 text-base font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 ${
          dark
            ? "border-white/30 text-white hover:border-white/60 hover:bg-white/10 focus-visible:ring-white"
            : "border-primary/15 bg-white text-primary hover:border-secondary/40 focus-visible:ring-secondary"
        }`}
      >
        Open a business account
      </Link>
      <span className={`text-sm ${dark ? "text-white/70" : "text-muted"}`}>{pitch}</span>
    </div>
  );
}
