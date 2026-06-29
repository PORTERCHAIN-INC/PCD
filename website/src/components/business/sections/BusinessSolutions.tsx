"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_SOLUTION_KEYS } from "@/data/business";
import {
  Repeat,
  Route,
  Zap,
  MapPinned,
  Boxes,
  Container as ContainerIcon,
  Truck,
  Sofa,
  HardHat,
  HeartPulse,
  Store,
  RotateCcw,
} from "lucide-react";

const ICONS = [
  Repeat,
  Route,
  Zap,
  MapPinned,
  Boxes,
  ContainerIcon,
  Truck,
  Sofa,
  HardHat,
  HeartPulse,
  Store,
  RotateCcw,
];

export default function BusinessSolutions() {
  const t = useTranslations("businessPage.solutions");

  return (
    <section id="solutions" className="biz-section bg-[#091b1c]">
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
          <h2 className="mt-3 biz-heading text-white tracking-tight">
            {t("title")}
          </h2>
          <p className="mt-4 text-white/60 leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {BUSINESS_SOLUTION_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.04 }}
                whileHover={{ y: -4 }}
                className="group p-6 rounded-2xl bg-white/5 border border-white/8 hover:border-[#ff7a00]/30 hover:bg-white/8 transition-all cursor-default"
              >
                <div className="w-10 h-10 rounded-xl bg-[#ff7a00]/15 flex items-center justify-center text-[#ff7a00] mb-4 group-hover:bg-[#ff7a00]/25 transition-colors">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-white mb-2">{t(`items.${key}`)}</h3>
                <p className="text-sm text-white/50 leading-relaxed">
                  {t(`descriptions.${key}`)}
                </p>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
