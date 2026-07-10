"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import InquiryForm from "@/components/business/InquiryForm";

export default function BusinessHero() {
  const t = useTranslations("businessPage.hero");

  return (
    <section className="relative overflow-hidden bg-white">
      <div className="absolute inset-0 grid-pattern opacity-50 pointer-events-none" aria-hidden />
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(37,99,235,0.08) 0%, transparent 55%)",
        }}
      />

      <Container className="relative z-10 py-24 sm:py-28 lg:py-32">
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-start">
          <div className="max-w-xl">
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="pc-eyebrow"
            >
              {t("badge")}
            </motion.p>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.06 }}
              className="pc-display mt-4 text-primary text-balance"
            >
              {t("titleLine1")}
              <span className="block text-primary/90">{t("titleLine2")}</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.12 }}
              className="mt-6 text-lg text-muted leading-relaxed"
            >
              {t("subtitle")}
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.18 }}
              className="mt-8 flex flex-col sm:flex-row flex-wrap gap-3"
            >
              <LinkButton
                href="/contact?intent=quote&from=business"
                size="lg"
                trackSource="business-hero"
              >
                {t("ctaPrimary")}
              </LinkButton>
              <LinkButton href="#fleet" variant="outline" size="lg" trackSource="business-hero">
                {t("ctaSecondary")}
              </LinkButton>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.22 }}
            className="relative"
          >
            <div className="rounded-3xl border border-primary/8 bg-white p-1 shadow-premium">
              <InquiryForm id="inquiry" variant="hero" />
            </div>
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
