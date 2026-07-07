"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import InquiryForm from "@/components/business/InquiryForm";

export default function FinalCta() {
  const t = useTranslations("businessPage.finalCta");

  return (
    <section className="relative biz-section bg-[#091b1c] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(255,122,0,0.12)_0%,transparent_60%)]" />
      <Container className="relative">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center max-w-2xl mx-auto mb-12"
        >
          <h2 className="biz-heading lg:text-5xl text-white tracking-tight">{t("title")}</h2>
          <p className="mt-5 text-lg text-white/60 leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <InquiryForm id="inquiry-final" variant="final" />
      </Container>
    </section>
  );
}
