"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  ClipboardList,
  UserCheck,
  PackageCheck,
  MapPin,
  FileCheck,
  Receipt,
} from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";
import LogisticsPattern from "@/components/illustrations/LogisticsPattern";

const STEP_KEYS = ["book", "assigned", "pickup", "tracking", "proof", "invoice"] as const;
const STEP_ICONS = [ClipboardList, UserCheck, PackageCheck, MapPin, FileCheck, Receipt];

export default function HowItWorks() {
  const t = useTranslations("howItWorks");

  return (
    <section className="site-section bg-gray-bg relative overflow-hidden">
      <LogisticsPattern className="absolute top-0 right-0 w-1/2 h-full opacity-30 pointer-events-none hidden lg:block" />
      <Container className="relative">
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="relative">
          <div className="hidden lg:block absolute top-12 left-0 right-0 h-0.5 bg-gradient-to-r from-secondary/20 via-secondary to-secondary/20" />

          <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-6 gap-5 sm:gap-6 lg:gap-4">
            {STEP_KEYS.map((key, i) => {
              const Icon = STEP_ICONS[i];
              return (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  className="relative text-center group"
                >
                  <div className="relative inline-flex flex-col items-center">
                    <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-white border border-gray-200/80 shadow-premium flex items-center justify-center group-hover:border-secondary/30 group-hover:shadow-glow transition-all duration-300 relative z-10">
                      <Icon className="w-8 h-8 text-secondary" />
                      <span className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-secondary text-white text-xs font-bold flex items-center justify-center shadow-lg">
                        {i + 1}
                      </span>
                    </div>
                  </div>
                  <h3 className="mt-5 type-body font-semibold text-primary">
                    {t(`steps.${key}.title`)}
                  </h3>
                  <p className="mt-2 type-small text-muted px-2">
                    {t(`steps.${key}.description`)}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </Container>
    </section>
  );
}
