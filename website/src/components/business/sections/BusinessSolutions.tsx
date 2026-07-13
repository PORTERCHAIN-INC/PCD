"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import ShimmerButton from "@/components/magic/shimmer-button";
import BlurFade from "@/components/magic/blur-fade";
import { BUSINESS_SOLUTION_KEYS } from "@/data/business";
import MagicCard from "@/components/magic/magic-card";
import {
  Repeat,
  Route,
  Zap,
  MapPinned,
  Boxes,
  Container as ContainerIcon,
  Truck,
  HardHat,
  HeartPulse,
  Store,
} from "lucide-react";

const ICONS = [
  Repeat,
  Route,
  Zap,
  MapPinned,
  Boxes,
  ContainerIcon,
  Truck,
  Zap,
  HardHat,
  HeartPulse,
  Boxes,
  Store,
];

export default function BusinessSolutions() {
  const t = useTranslations("businessPage.solutions");

  return (
    <section id="solutions" className="biz-section relative overflow-hidden bg-[#091b1c]">
      <div
        className="absolute inset-0 dot-pattern opacity-[0.12] pointer-events-none"
        aria-hidden
      />
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% -20%, rgba(255,122,0,0.15) 0%, transparent 55%)",
        }}
      />

      <Container className="relative z-10">
        <BlurFade inView className="text-center max-w-3xl mx-auto mb-14">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#ff7a00]">
            {t("label")}
          </span>
          <h2 className="mt-3 biz-heading text-white tracking-tight text-balance">{t("title")}</h2>
          <p className="mt-4 text-white/60 leading-relaxed text-base sm:text-lg">{t("subtitle")}</p>
        </BlurFade>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {BUSINESS_SOLUTION_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            return (
              <BlurFade key={key} delay={i * 0.03} inView>
                <MagicCard className="h-full border-white/10 bg-white/[0.04] p-6 hover:border-[#ff7a00]/35 hover:bg-white/[0.07]">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#ff7a00]/15 text-[#ff7a00]">
                    <Icon className="h-5 w-5" aria-hidden />
                  </div>
                  <h3 className="mt-4 font-semibold text-white mb-2 leading-snug">
                    {t(`items.${key}`)}
                  </h3>
                  <p className="text-sm text-white/55 leading-relaxed">
                    {t(`descriptions.${key}`)}
                  </p>
                </MagicCard>
              </BlurFade>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
