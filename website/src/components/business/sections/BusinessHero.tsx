"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Calendar, ArrowRight } from "lucide-react";
import Container from "@/components/ui/Container";
import InquiryForm from "@/components/business/InquiryForm";
import BusinessHeroBg from "@/components/business/illustrations/BusinessHeroBg";
import SiteImage from "@/components/ui/SiteImage";
import { siteImages } from "@/data/site-images";

export default function BusinessHero() {
  const t = useTranslations("businessPage.hero");

  const scrollToInquiry = () => {
    document.getElementById("inquiry")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative min-h-[100svh] flex items-center overflow-hidden bg-[#091b1c]">
      <SiteImage
        image={siteImages.hero.business}
        fill
        className="object-cover opacity-35"
        sizes="100vw"
        priority
      />
      <BusinessHeroBg className="absolute inset-0 w-full h-full object-cover opacity-60" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#091b1c]/40 via-transparent to-[#091b1c]/90" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_20%,rgba(255,122,0,0.12)_0%,transparent_50%)]" />

      <Container className="relative z-10 pt-24 pb-12 sm:pt-28 sm:pb-16 lg:pt-32 lg:pb-24">
        <div className="grid lg:grid-cols-2 gap-8 sm:gap-10 lg:gap-16 items-start lg:items-center">
          <div>
            <motion.span
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/8 border border-white/12 text-white/90 text-xs font-semibold uppercase tracking-wider mb-6"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-[#ff7a00] animate-pulse" />
              {t("badge")}
            </motion.span>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 }}
              className="biz-heading lg:text-[3.25rem] text-white leading-[1.1] tracking-tight"
            >
              {t("titleLine1")}
              <span className="block mt-1 biz-gradient-text">{t("titleLine2")}</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.14 }}
              className="mt-6 text-lg text-white/70 leading-relaxed max-w-xl"
            >
              {t("subtitle")}
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mt-8 flex flex-wrap gap-3"
            >
              <button
                onClick={scrollToInquiry}
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl bg-[#ff7a00] text-white font-semibold text-sm hover:bg-[#e66e00] transition-all biz-shadow-glow"
              >
                {t("ctaPrimary")}
                <ArrowRight className="w-4 h-4" />
              </button>
              <a
                href="#onboarding"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl border border-white/20 text-white font-medium text-sm hover:bg-white/10 transition-colors"
              >
                <Calendar className="w-4 h-4" />
                {t("ctaSecondary")}
              </a>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 32, rotate: 0 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.7 }}
            className="relative"
          >
            <div className="absolute -inset-4 bg-[#ff7a00]/10 rounded-3xl blur-2xl" />
            <div className="relative animate-float">
              <InquiryForm id="inquiry" variant="hero" />
            </div>
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
