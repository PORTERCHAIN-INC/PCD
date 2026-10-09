"use client";

import { useEffect, useState } from "react";
import { assignHeroVariant, type HeroAbConfig } from "@/lib/marketing/calculator-lead";
import { CONVERSION_EVENTS, trackConversion } from "@/lib/marketing/conversion";
import { getOrCreateVisitorId } from "@/lib/visitor-tracking";

export const HERO_VARIANT_KEY = "pc_hero_variant";

/**
 * H1 with an optional A/B copy test. The server HTML always carries the control
 * copy; variant "b" is only swapped in when ops enable `marketing_site.hero_ab`.
 */
export default function HeroVariantTitle({
  control,
  variantB,
  suffix,
  className,
}: {
  control: string;
  variantB: string;
  suffix?: string;
  className?: string;
}) {
  const [variant, setVariant] = useState<"control" | "b">("control");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/marketing-config")
      .then((res) => (res.ok ? res.json() : null))
      .then((cfg: { hero_ab?: HeroAbConfig } | null) => {
        if (cancelled || !cfg?.hero_ab?.enabled) return;
        const next = assignHeroVariant(cfg.hero_ab, getOrCreateVisitorId());
        try {
          window.sessionStorage.setItem(HERO_VARIANT_KEY, `${cfg.hero_ab.experiment}:${next}`);
        } catch {
          /* private mode */
        }
        setVariant(next);
        trackConversion(CONVERSION_EVENTS.HERO_EXPOSURE, {
          experiment: cfg.hero_ab.experiment,
          variant: next,
        });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const text = variant === "b" ? variantB : control;
  return (
    <h1 className={className} data-hero-variant={variant}>
      {text}
      {suffix ? ` ${suffix}` : ""}
    </h1>
  );
}
