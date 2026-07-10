"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";
import StorySection from "./StorySection";

const GtaAiRouteVisual = dynamic(() => import("@/components/home/story/GtaAiRouteVisual"), {
  loading: () => (
    <div
      className="min-h-[280px] sm:min-h-[320px] rounded-3xl border border-primary/8 bg-white animate-pulse"
      aria-hidden
    />
  ),
  ssr: false,
});

export default function StoryAi() {
  const t = useTranslations("corporate.home.story.ai");

  return (
    <StorySection
      id="vision"
      label={t("label")}
      title={t("title")}
      subtitle={t("subtitle")}
      className="bg-gray-bg"
    >
      <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.08fr)] gap-8 lg:gap-12 xl:gap-14 items-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5 }}
          className="order-2 lg:order-1 rounded-3xl border border-primary/6 bg-white p-6 sm:p-8 lg:p-10 shadow-premium"
        >
          <Sparkles className="h-8 w-8 text-secondary/60" aria-hidden />
          <p className="mt-5 sm:mt-6 text-base sm:text-lg text-primary leading-relaxed font-medium">
            {t("body")}
          </p>
          <p className="mt-4 text-sm text-muted leading-relaxed">{t("note")}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.55, delay: 0.08 }}
          className="order-1 lg:order-2"
          aria-label={t("imageAlt")}
        >
          <GtaAiRouteVisual
            caption={t("imageCaption")}
            aiLabel={t("aiBadge")}
            regionLabel={t("regionBadge")}
            statsLabel={t("statsLabel")}
          />
        </motion.div>
      </div>
    </StorySection>
  );
}
