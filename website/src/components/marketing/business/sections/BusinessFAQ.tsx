"use client";

import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import Container from "@/components/ui/Container";
import Accordion from "@/components/ui/Accordion";
import { BUSINESS_FAQ_KEYS } from "@/data/business";

export default function BusinessFAQ() {
  const t = useTranslations("businessPage.faq");

  const items = BUSINESS_FAQ_KEYS.map((key) => ({
    question: t(`items.${key}.question`),
    answer: t(`items.${key}.answer`),
  }));

  return (
    <section id="faq" className="biz-section bg-[#f7f8fa]">
      <Container size="narrow">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2563eb]">
            {t("label")}
          </span>
          <h2 className="mt-3 biz-heading text-[#0b1220] tracking-tight">{t("title")}</h2>
          <p className="mt-4 text-[#64748b]">{t("subtitle")}</p>
        </motion.div>

        <Accordion items={items} speakableCount={4} />
      </Container>
    </section>
  );
}
