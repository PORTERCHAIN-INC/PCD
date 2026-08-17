"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_ONBOARDING_STEPS } from "@/data/business";
import { quoteSignUpPath } from "@/data/portal-links";
import { Link } from "@/i18n/navigation";
import { ChevronRight } from "lucide-react";

export default function EnterpriseOnboarding() {
  const t = useTranslations("businessPage.onboarding");

  return (
    <section id="onboarding" className="biz-section bg-[#f7f8fa] overflow-hidden">
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

        {/* Desktop horizontal timeline */}
        <div className="hidden lg:block relative">
          <div className="absolute top-8 left-0 right-0 h-0.5 biz-timeline-line rounded-full" />
          <div className="grid grid-cols-6 gap-4">
            {BUSINESS_ONBOARDING_STEPS.map((step, i) => (
              <motion.div
                key={step}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="relative text-center"
              >
                <div className="w-16 h-16 mx-auto rounded-2xl bg-[#0b1220] text-white flex items-center justify-center text-xl font-bold relative z-10 biz-shadow">
                  {i + 1}
                </div>
                <h3 className="mt-4 font-semibold text-[#0b1220] text-sm">
                  {t(`steps.${step}.title`)}
                </h3>
                <p className="mt-1 text-xs text-[#64748b] leading-relaxed px-1">
                  {t(`steps.${step}.description`)}
                </p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Mobile vertical timeline */}
        <div className="lg:hidden space-y-0">
          {BUSINESS_ONBOARDING_STEPS.map((step, i) => (
            <motion.div
              key={step}
              initial={{ opacity: 0, x: -16 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="flex gap-4"
            >
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-[#0b1220] text-white flex items-center justify-center font-bold shrink-0">
                  {i + 1}
                </div>
                {i < BUSINESS_ONBOARDING_STEPS.length - 1 && (
                  <div className="w-0.5 flex-1 min-h-[2rem] bg-gradient-to-b from-[#2563eb] to-[#2563eb]/20 my-1" />
                )}
              </div>
              <div className="pb-8">
                <h3 className="font-semibold text-[#0b1220]">{t(`steps.${step}.title`)}</h3>
                <p className="mt-1 text-sm text-[#64748b]">{t(`steps.${step}.description`)}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mt-12 text-center"
        >
          <Link
            href={quoteSignUpPath({ from: "business" })}
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#2563eb] hover:text-[#1d4ed8] transition-colors"
          >
            {t("cta")}
            <ChevronRight className="w-4 h-4" />
          </Link>
        </motion.div>
      </Container>
    </section>
  );
}
