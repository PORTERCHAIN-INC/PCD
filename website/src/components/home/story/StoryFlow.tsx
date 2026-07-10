"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { ArrowDown, Building2, CheckCircle2, Network, Server } from "lucide-react";
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
      <div className="max-w-md mx-auto lg:max-w-none lg:grid lg:grid-cols-4 lg:gap-4">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          const isLast = i === STEPS.length - 1;
          return (
            <motion.div
              key={step.key}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative flex flex-col items-center text-center"
            >
              <div
                className={`flex h-14 w-14 items-center justify-center rounded-2xl border shadow-premium ${
                  isLast
                    ? "border-secondary/30 bg-secondary/10 text-secondary"
                    : "border-primary/8 bg-white text-primary"
                }`}
              >
                <Icon className="h-6 w-6" aria-hidden />
              </div>
              <p className="mt-4 text-base font-semibold text-primary tracking-tight">
                {t(`steps.${step.key}.title`)}
              </p>
              <p className="mt-1.5 text-sm text-muted leading-relaxed max-w-[200px]">
                {t(`steps.${step.key}.description`)}
              </p>
              {!isLast && (
                <ArrowDown className="my-4 h-5 w-5 text-secondary/40 lg:hidden" aria-hidden />
              )}
              {!isLast && (
                <div
                  className="hidden lg:block absolute top-7 left-[calc(50%+2rem)] w-[calc(100%-4rem)] h-px bg-gradient-to-r from-secondary/40 to-secondary/10"
                  aria-hidden
                />
              )}
            </motion.div>
          );
        })}
      </div>
    </StorySection>
  );
}
