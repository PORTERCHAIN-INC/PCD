"use client";

import { motion } from "framer-motion";
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
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="rounded-2xl border border-primary/6 bg-white p-6 shadow-premium"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10">
                <Icon className="h-5 w-5 text-secondary" aria-hidden />
              </div>
              <h3 className="mt-4 text-base font-semibold text-primary">
                {t(`items.${key}.title`)}
              </h3>
              <p className="mt-2 text-sm text-muted leading-relaxed">
                {t(`items.${key}.description`)}
              </p>
            </motion.div>
          );
        })}
      </div>
      <div className="mt-10">
        <LinkButton href="/platform" variant="secondary" showArrow trackSource="home-platform">
          {t("cta")}
        </LinkButton>
      </div>
    </StorySection>
  );
}
