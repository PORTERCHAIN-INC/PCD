"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import LinkButton from "@/components/corporate/ui/LinkButton";
import StorySection from "./StorySection";

const KEYS = ["0", "1", "2", "3", "4", "5", "6"] as const;

export default function StoryProblems() {
  const t = useTranslations("corporate.home.story.problems");

  return (
    <StorySection
      id="problems"
      label={t("label")}
      title={t("title")}
      className="bg-gray-bg grid-pattern"
    >
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
        {KEYS.map((key, i) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.04 }}
            className="pc-glass rounded-2xl px-4 py-5 sm:px-5 sm:py-6 shadow-premium"
          >
            <p className="text-sm sm:text-base font-semibold text-primary tracking-tight leading-snug">
              {t(`items.${key}`)}
            </p>
          </motion.div>
        ))}
      </div>
      <div className="mt-10">
        <LinkButton
          href="/contact?intent=quote&from=home-problems"
          size="lg"
          trackSource="home-problems"
        >
          {t("cta")}
        </LinkButton>
      </div>
    </StorySection>
  );
}
