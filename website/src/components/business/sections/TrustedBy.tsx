"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_TRUSTED_KEYS } from "@/data/business";
import {
  Coffee,
  Stethoscope,
  Factory,
  ShoppingBag,
  HardHat,
  UtensilsCrossed,
  Package,
  Car,
  FlaskConical,
  Truck,
} from "lucide-react";

const ICONS = [
  Coffee,
  Stethoscope,
  Factory,
  ShoppingBag,
  HardHat,
  UtensilsCrossed,
  Package,
  Car,
  FlaskConical,
  Truck,
];

export default function TrustedBy() {
  const t = useTranslations("businessPage.trustedBy");

  return (
    <section className="biz-section bg-white border-b border-[#091b1c]/5">
      <Container>
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-[#5c6b6c] mb-10"
        >
          {t("label")}
        </motion.p>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 sm:gap-6">
          {BUSINESS_TRUSTED_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.04 }}
                className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-[#f7f8fa] border border-[#091b1c]/5 biz-card-hover"
              >
                <div className="w-11 h-11 rounded-xl bg-white flex items-center justify-center text-[#091b1c] biz-shadow">
                  <Icon className="w-5 h-5" strokeWidth={1.5} />
                </div>
                <span className="text-sm font-semibold text-[#091b1c] text-center leading-tight">
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
