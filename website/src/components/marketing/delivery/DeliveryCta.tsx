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
}: {
  label: string;
  pitch: string;
  industry?: string;
  area?: string;
  pickupFsa?: string;
  from: string;
}) {
  const params = new URLSearchParams({ from });
  if (industry) params.set("industry", industry);
  if (pickupFsa) params.set("pickup", pickupFsa);
  const calculatorHref = `/delivery-cost-calculator?${params.toString()}`;
  const signUpHref = `/sign-up?intent=merchant&from=${encodeURIComponent(from)}`;
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <Link
        href={calculatorHref}
        onClick={() =>
          trackConversion(CONVERSION_EVENTS.DELIVERY_CTA_CLICK, {
            cta: "calculator",
            industry,
            area,
          })
        }
        className="inline-flex justify-center rounded-xl bg-secondary px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8]"
      >
        {label}
      </Link>
      <Link
        href={signUpHref}
        onClick={() =>
          trackConversion(CONVERSION_EVENTS.DELIVERY_CTA_CLICK, { cta: "signup", industry, area })
        }
        className="inline-flex justify-center rounded-xl border border-primary/15 bg-white px-5 py-3 text-sm font-semibold text-primary transition-colors hover:border-secondary/40"
      >
        Open a business account
      </Link>
      <span className="text-sm text-muted">{pitch}</span>
    </div>
  );
}
