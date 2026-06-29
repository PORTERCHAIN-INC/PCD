"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_SUCCESS_KEYS } from "@/data/business";
import { Quote } from "lucide-react";

export default function CustomerSuccess() {
  const t = useTranslations("businessPage.success");

  return (
    <section className="biz-section bg-white">
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
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {BUSINESS_SUCCESS_KEYS.map((key, i) => (
            <motion.blockquote
              key={key}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative p-8 rounded-2xl bg-[#f7f8fa] border border-[#091b1c]/6 biz-card-hover"
            >
              <Quote className="w-8 h-8 text-[#ff7a00]/30 mb-4" />
              <p className="text-[#091b1c] leading-relaxed text-lg font-medium">
                &ldquo;{t(`items.${key}.quote`)}&rdquo;
              </p>
              <footer className="mt-6 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#091b1c] flex items-center justify-center text-white text-sm font-bold">
                  {t(`items.${key}.initials`)}
                </div>
                <div>
                  <p className="font-semibold text-[#091b1c] text-sm">
                    {t(`items.${key}.author`)}
                  </p>
                  <p className="text-xs text-[#5c6b6c]">{t(`items.${key}.role`)}</p>
                </div>
              </footer>
            </motion.blockquote>
          ))}
        </div>
      </Container>
    </section>
  );
}
