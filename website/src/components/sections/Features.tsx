"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  Zap,
  Calendar,
  MapPin,
  Star,
  FileCheck,
  Camera,
  PenLine,
  ScanBarcode,
  Bell,
  CreditCard,
} from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";

const FEATURE_ICONS = [
  Zap,
  Calendar,
  MapPin,
  Star,
  FileCheck,
  Camera,
  PenLine,
  ScanBarcode,
  Bell,
  CreditCard,
];

export default function Features() {
  const t = useTranslations("features");
  const items = t.raw("items") as string[];

  return (
    <section id="resources" className="site-section bg-white">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="flex flex-wrap justify-center gap-2.5 sm:gap-3">
          {items.map((feature, i) => {
            const Icon = FEATURE_ICONS[i];
            return (
              <motion.div
                key={feature}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.03 }}
                whileHover={{ scale: 1.05 }}
                className="inline-flex items-center gap-2.5 px-5 py-3 rounded-full border border-gray-200/80 bg-white hover:border-secondary/30 hover:shadow-premium transition-all duration-200 cursor-default"
              >
                <Icon className="w-4 h-4 text-secondary" />
                <span className="type-small font-semibold text-primary">{feature}</span>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
