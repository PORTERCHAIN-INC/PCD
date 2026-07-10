"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";

export default function StoryCta() {
  const t = useTranslations("corporate.home.story.cta");

  return (
    <section className="relative overflow-hidden bg-primary py-20 sm:py-24">
      <div className="absolute inset-0 pointer-events-none" aria-hidden>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(37,99,235,0.2)_0%,transparent_55%)]" />
        <div className="absolute inset-0 dot-pattern opacity-20" />
      </div>
      <Container className="relative">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-2xl mx-auto text-center"
        >
          <h2 className="pc-display text-white text-balance">{t("title")}</h2>
          <p className="mt-4 text-lg text-white/65 leading-relaxed">{t("subtitle")}</p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <LinkButton
              href="/contact?intent=quote&from=home-final"
              size="lg"
              showArrow
              trackSource="home-final"
            >
              {t("primary")}
            </LinkButton>
          </div>
        </motion.div>
      </Container>
    </section>
  );
}
