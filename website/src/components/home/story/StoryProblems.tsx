"use client";

import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Building2,
  Clock,
  Package,
  Route,
  Stethoscope,
  Truck,
  Zap,
} from "lucide-react";
import LinkButton from "@/components/corporate/ui/LinkButton";
import MagicCard from "@/components/magic/magic-card";
import BlurFade from "@/components/magic/blur-fade";
import StorySection from "./StorySection";

const KEYS = ["0", "1", "2", "3", "4", "5", "6", "7"] as const;

const ICONS = [AlertTriangle, Truck, Route, Zap, Building2, Stethoscope, Package, Clock] as const;

export default function StoryProblems() {
  const t = useTranslations("corporate.home.story.problems");

  return (
    <StorySection
      id="problems"
      label={t("label")}
      title={t("title")}
      subtitle={t("subtitle")}
      className="bg-gray-bg grid-pattern relative overflow-hidden"
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 70% 50% at 50% 0%, rgba(37,99,235,0.06) 0%, transparent 70%)",
        }}
      />

      <div className="relative grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {KEYS.map((key, i) => {
          const Icon = ICONS[i];
          return (
            <BlurFade key={key} delay={i * 0.04} inView>
              <MagicCard className="h-full p-5 sm:p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
                  <Icon className="h-5 w-5" aria-hidden />
                </div>
                <p className="mt-4 text-sm sm:text-base font-semibold text-primary tracking-tight leading-snug">
                  {t(`items.${key}`)}
                </p>
                <p className="mt-2 text-xs sm:text-sm text-muted leading-relaxed">
                  {t(`descriptions.${key}`)}
                </p>
              </MagicCard>
            </BlurFade>
          );
        })}
      </div>

      <BlurFade inView className="mt-10">
        <LinkButton
          href="/sign-up?intent=quote&from=home-problems"
          size="lg"
          trackSource="home-problems"
        >
          {t("cta")}
        </LinkButton>
      </BlurFade>
    </StorySection>
  );
}
