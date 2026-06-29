"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  Zap,
  MapPin,
  FileCheck,
  Route,
  DollarSign,
  Clock,
  Bell,
} from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";

const FEATURE_KEYS = [
  "simplicity",
  "tracking",
  "proof",
  "fleet",
  "pricing",
  "sameDay",
  "notifications",
] as const;

const FEATURE_ICONS = [
  Zap,
  MapPin,
  FileCheck,
  Route,
  DollarSign,
  Clock,
  Bell,
];

export default function WhyPorterchain() {
  const t = useTranslations("whyPorterchain");

  return (
    <section className="site-section bg-white">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {FEATURE_KEYS.map((key, i) => {
            const Icon = FEATURE_ICONS[i];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                className="group p-6 rounded-2xl border border-gray-200/80 bg-white hover:border-secondary/20 hover:shadow-premium transition-all duration-300"
              >
                <div className="w-11 h-11 rounded-xl bg-gray-bg group-hover:bg-secondary/10 flex items-center justify-center transition-colors mb-4">
                  <Icon className="w-5 h-5 text-primary group-hover:text-secondary transition-colors" />
                </div>
                <h3 className="font-bold text-primary type-small">
                  {t(`features.${key}.title`)}
                </h3>
                <p className="text-muted type-small mt-1">
                  {t(`features.${key}.description`)}
                </p>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
