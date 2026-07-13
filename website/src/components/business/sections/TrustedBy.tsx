"use client";

import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import Marquee from "@/components/magic/marquee";
import { BUSINESS_TRUSTED_KEYS } from "@/data/business";
import {
  Coffee,
  Stethoscope,
  Factory,
  ShoppingBag,
  HardHat,
  UtensilsCrossed,
  Package,
  Car,
  FlaskConical,
  Truck,
} from "lucide-react";

const ICONS = [
  Coffee,
  Stethoscope,
  Factory,
  ShoppingBag,
  HardHat,
  UtensilsCrossed,
  Package,
  Car,
  FlaskConical,
  Truck,
];

export default function TrustedBy() {
  const t = useTranslations("businessPage.trustedBy");

  const chips = BUSINESS_TRUSTED_KEYS.map((key, i) => {
    const Icon = ICONS[i];
    return (
      <div
        key={key}
        className="flex shrink-0 items-center gap-3 rounded-full border border-[#091b1c]/8 bg-white px-5 py-3 shadow-sm"
      >
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#f7f8fa] text-[#091b1c]">
          <Icon className="h-4 w-4" strokeWidth={1.5} aria-hidden />
        </div>
        <span className="text-sm font-semibold text-[#091b1c] whitespace-nowrap">
          {t(`items.${key}`)}
        </span>
      </div>
    );
  });

  return (
    <section className="biz-section overflow-hidden border-b border-[#091b1c]/5 bg-white">
      <Container>
        <p className="mb-8 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[#5c6b6c]">
          {t("label")}
        </p>
      </Container>
      <Marquee speed="slow" className="py-1">
        <div className="flex gap-4 px-2">{chips}</div>
      </Marquee>
    </section>
  );
}
