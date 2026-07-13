"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { ArrowRight, Building2, CheckCircle2, Network, Server } from "lucide-react";
import MagicCard from "@/components/magic/magic-card";
import BlurFade from "@/components/magic/blur-fade";
import StorySection from "./StorySection";

const STEPS = [
  { key: "business", icon: Building2 },
  { key: "platform", icon: Server },
  { key: "network", icon: Network },
  { key: "complete", icon: CheckCircle2 },
] as const;

export default function StoryFlow() {
  const t = useTranslations("corporate.home.story.flow");

  return (
    <StorySection id="how-it-works" label={t("label")} title={t("title")} subtitle={t("subtitle")}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          const isLast = i === STEPS.length - 1;
          return (
            <BlurFade key={step.key} delay={i * 0.08} inView>
              <MagicCard
                className={`relative h-full p-6 text-center ${
                  isLast ? "border-secondary/20 bg-secondary/[0.03]" : ""
                }`}
              >
                {i < STEPS.length - 1 && (
                  <ArrowRight
                    className="absolute -right-3 top-1/2 z-20 hidden h-5 w-5 -translate-y-1/2 text-secondary/30 lg:block"
                    aria-hidden
                  />
                )}
                <div
                  className={`mx-auto flex h-14 w-14 items-center justify-center rounded-2xl ${
                    isLast ? "bg-secondary/15 text-secondary" : "bg-primary/[0.04] text-primary"
                  }`}
                >
                  <Icon className="h-6 w-6" aria-hidden />
                </div>
                <p className="mt-4 text-base font-semibold text-primary tracking-tight">
                  {t(`steps.${step.key}.title`)}
                </p>
                <p className="mt-2 text-sm text-muted leading-relaxed">
                  {t(`steps.${step.key}.description`)}
                </p>
                <span className="mt-4 inline-flex h-7 w-7 items-center justify-center rounded-full bg-primary/[0.06] text-xs font-bold text-primary/70">
                  {i + 1}
                </span>
              </MagicCard>
            </BlurFade>
          );
        })}
      </div>
    </StorySection>
  );
}
