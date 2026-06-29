"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_BILLING_KEYS } from "@/data/business";
import { Check, Star } from "lucide-react";
import { cn } from "@/lib/utils";

export default function BillingOptions() {
  const t = useTranslations("businessPage.billing");

  return (
    <section id="pricing" className="biz-section bg-[#f7f8fa]">
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
          <p className="mt-4 text-[#5c6b6c] leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {BUSINESS_BILLING_KEYS.map((key, i) => {
            const isFeatured = key === "enterprise";
            const features = t.raw(`plans.${key}.features`) as string[];

            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className={cn(
                  "relative rounded-2xl p-7 biz-card-hover",
                  isFeatured
                    ? "bg-[#091b1c] text-white biz-shadow-lg md:scale-[1.02]"
                    : "bg-white border border-[#091b1c]/8 biz-shadow"
                )}
              >
                {isFeatured && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 flex items-center gap-1 px-3 py-1 rounded-full bg-[#ff7a00] text-white text-xs font-semibold">
                    <Star className="w-3 h-3" />
                    {t("recommended")}
                  </div>
                )}
                <h3
                  className={cn(
                    "text-xl font-bold",
                    isFeatured ? "text-white" : "text-[#091b1c]"
                  )}
                >
                  {t(`plans.${key}.name`)}
                </h3>
                <p
                  className={cn(
                    "mt-2 text-sm leading-relaxed",
                    isFeatured ? "text-white/60" : "text-[#5c6b6c]"
                  )}
                >
                  {t(`plans.${key}.description`)}
                </p>
                <ul className="mt-6 space-y-3">
                  {features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5 text-sm">
                      <Check
                        className={cn(
                          "w-4 h-4 shrink-0 mt-0.5",
                          isFeatured ? "text-[#ff7a00]" : "text-[#ff7a00]"
                        )}
                      />
                      <span className={isFeatured ? "text-white/80" : "text-[#091b1c]/80"}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>
                <a
                  href="#inquiry"
                  className={cn(
                    "mt-8 block text-center px-5 py-3 rounded-xl text-sm font-semibold transition-all",
                    isFeatured
                      ? "bg-[#ff7a00] text-white hover:bg-[#e66e00] biz-shadow-glow"
                      : "bg-[#091b1c] text-white hover:bg-[#143638]"
                  )}
                >
                  {t("cta")}
                </a>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
