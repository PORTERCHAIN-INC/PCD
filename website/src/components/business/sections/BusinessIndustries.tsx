"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_INDUSTRY_KEYS } from "@/data/business";
import {
  Coffee,
  Wine,
  UtensilsCrossed,
  ShoppingCart,
  Stethoscope,
  HardHat,
  Zap,
  Wind,
  Factory,
  Car,
  Store,
  Sofa,
  FlaskConical,
  ShoppingBag,
  Printer,
  Cog,
} from "lucide-react";

const ICONS = [
  Coffee,
  Wine,
  UtensilsCrossed,
  ShoppingCart,
  Stethoscope,
  HardHat,
  Zap,
  Wind,
  Factory,
  Car,
  Store,
  Sofa,
  FlaskConical,
  ShoppingBag,
  Printer,
  Cog,
];

export default function BusinessIndustries() {
  const t = useTranslations("businessPage.industries");

  return (
    <section id="industries" className="biz-section bg-white">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center max-w-2xl mx-auto mb-14"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#ff7a00]">
            {t("label")}
          </span>
          <h2 className="mt-3 biz-heading text-[#091b1c] tracking-tight">
            {t("title")}
          </h2>
          <p className="mt-4 text-[#5c6b6c] leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4">
          {BUSINESS_INDUSTRY_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.03 }}
                className="group flex flex-col items-center gap-3 p-5 sm:p-6 rounded-2xl bg-[#f7f8fa] border border-[#091b1c]/5 hover:border-[#ff7a00]/30 hover:bg-white biz-card-hover cursor-default text-center"
              >
                <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center text-[#091b1c] group-hover:text-[#ff7a00] group-hover:bg-[#ff7a00]/10 transition-all biz-shadow">
                  <Icon className="w-5 h-5" strokeWidth={1.5} />
                </div>
                <span className="text-sm font-semibold text-[#091b1c] leading-tight">
                  {t(`items.${key}`)}
                </span>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
