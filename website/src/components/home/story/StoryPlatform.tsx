"use client";

import { useTranslations } from "next-intl";
import {
  BarChart3,
  Camera,
  CreditCard,
  LayoutDashboard,
  MapPin,
  Radio,
  type LucideIcon,
} from "lucide-react";
import LinkButton from "@/components/corporate/ui/LinkButton";
import MagicCard from "@/components/magic/magic-card";
import BlurFade from "@/components/magic/blur-fade";
import StorySection from "./StorySection";

const KEYS = ["portal", "tracking", "dispatch", "pod", "billing", "analytics"] as const;
const ICONS: Record<(typeof KEYS)[number], LucideIcon> = {
  portal: LayoutDashboard,
  tracking: MapPin,
  dispatch: Radio,
  pod: Camera,
  billing: CreditCard,
  analytics: BarChart3,
};

export default function StoryPlatform() {
  const t = useTranslations("corporate.home.story.platform");

  return (
    <StorySection id="platform" label={t("label")} title={t("title")} subtitle={t("subtitle")}>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {KEYS.map((key, i) => {
          const Icon = ICONS[key];
          return (
            <BlurFade key={key} delay={i * 0.05} inView>
              <MagicCard className="h-full p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10">
                  <Icon className="h-5 w-5 text-secondary" aria-hidden />
                </div>
                <h3 className="mt-4 text-base font-semibold text-primary">
                  {t(`items.${key}.title`)}
                </h3>
                <p className="mt-2 text-sm text-muted leading-relaxed">
                  {t(`items.${key}.description`)}
                </p>
              </MagicCard>
            </BlurFade>
          );
        })}
      </div>
      <BlurFade inView className="mt-10">
        <LinkButton href="/platform" variant="secondary" showArrow trackSource="home-platform">
          {t("cta")}
        </LinkButton>
      </BlurFade>
    </StorySection>
  );
}
