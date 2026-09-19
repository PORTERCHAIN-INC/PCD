"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_TECH_KEYS } from "@/data/business";

export default function Technology() {
  const t = useTranslations("businessPage.technology");

  return (
    <section id="technology" className="biz-section bg-white">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center max-w-2xl mx-auto mb-14"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2563eb]">
            {t("label")}
          </span>
          <h2 className="mt-3 biz-heading text-[#0b1220] tracking-tight">{t("title")}</h2>
          <p className="mt-4 text-[#64748b] leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
          {BUSINESS_TECH_KEYS.map((key, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.04 }}
              whileHover={{ y: -4 }}
              className="flex flex-col items-center gap-3 p-6 rounded-2xl bg-[#f7f8fa] border border-[#0b1220]/5 hover:border-[#2563eb]/25 transition-all"
            >
              <div className="w-14 h-14 rounded-2xl bg-white flex items-center justify-center biz-shadow text-lg font-bold text-[#0b1220]">
                {t(`items.${key}.abbr`)}
              </div>
              <span className="text-sm font-semibold text-[#0b1220] text-center">
                {t(`items.${key}.name`)}
              </span>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  );
}
