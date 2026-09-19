"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Check, Star } from "lucide-react";
import Container from "@/components/ui/Container";
import { BUSINESS_BILLING_KEYS } from "@/data/business";
import { quoteSignUpPath } from "@/data/portal-links";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

const FACTOR_KEYS = ["vehicle", "route", "proof"] as const;
const INCLUDED_CHECKLIST_KEYS = [
  "vehicleDriver",
  "tracking",
  "pod",
  "dispatch",
  "writtenQuote",
] as const;
const PROGRAM_COMPARE_KEYS = ["overflow", "dedicated", "recurring"] as const;

export default function BillingOptions() {
  const t = useTranslations("businessPage.billing");

  return (
    <section id="pricing" className="biz-section bg-[#f7f8fa]">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mb-10 max-w-2xl text-center"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2563eb]">
            {t("label")}
          </span>
          <h2 className="biz-heading mt-3 tracking-tight text-[#0b1220]">{t("title")}</h2>
          <p className="mt-4 leading-relaxed text-[#64748b]">{t("subtitle")}</p>
        </motion.div>

        <div className="mx-auto mb-12 grid max-w-4xl gap-6 sm:grid-cols-3">
          {FACTOR_KEYS.map((key, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="border-l-2 border-[#2563eb]/25 pl-4"
            >
              <h3 className="text-sm font-semibold text-[#0b1220]">{t(`factors.${key}.title`)}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-[#64748b]">
                {t(`factors.${key}.body`)}
              </p>
            </motion.div>
          ))}
        </div>

        <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-3">
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
                    ? "bg-[#0b1220] text-white biz-shadow-lg md:scale-[1.02]"
                    : "border border-[#0b1220]/8 bg-white biz-shadow"
                )}
              >
                {isFeatured && (
                  <div className="absolute -top-3 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-[#2563eb] px-3 py-1 text-xs font-semibold text-white">
                    <Star className="h-3 w-3" />
                    {t("recommended")}
                  </div>
                )}
                <h3
                  className={cn("text-xl font-bold", isFeatured ? "text-white" : "text-[#0b1220]")}
                >
                  {t(`plans.${key}.name`)}
                </h3>
                <p
                  className={cn(
                    "mt-1 text-sm font-medium",
                    isFeatured ? "text-[#93c5fd]" : "text-[#2563eb]"
                  )}
                >
                  {t(`plans.${key}.price`)}
                </p>
                <p
                  className={cn(
                    "mt-2 text-sm leading-relaxed",
                    isFeatured ? "text-white/60" : "text-[#64748b]"
                  )}
                >
                  {t(`plans.${key}.description`)}
                </p>
                <ul className="mt-6 space-y-3">
                  {features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#2563eb]" />
                      <span className={isFeatured ? "text-white/80" : "text-[#0b1220]/80"}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>
                <Link
                  href={quoteSignUpPath({ from: "business" })}
                  className={cn(
                    "mt-8 block rounded-xl px-5 py-3 text-center text-sm font-semibold transition-all",
                    isFeatured
                      ? "bg-[#2563eb] text-white hover:bg-[#1d4ed8] biz-shadow-glow"
                      : "bg-[#0b1220] text-white hover:bg-[#1e293b]"
                  )}
                >
                  {t("cta")}
                </Link>
              </motion.div>
            );
          })}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mt-14 max-w-3xl"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2563eb]">
            {t("includedChecklist.label")}
          </span>
          <h3 className="mt-2 text-xl font-bold tracking-tight text-[#0b1220]">
            {t("includedChecklist.title")}
          </h3>
          <ul className="mt-5 space-y-3">
            {INCLUDED_CHECKLIST_KEYS.map((key) => (
              <li
                key={key}
                className="flex items-start gap-2.5 text-sm leading-relaxed text-[#0b1220]/85"
              >
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#2563eb]" aria-hidden />
                <span>{t(`includedChecklist.items.${key}`)}</span>
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mx-auto mt-14 max-w-5xl"
        >
          <div className="mx-auto mb-8 max-w-2xl text-center">
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2563eb]">
              {t("programCompare.label")}
            </span>
            <h3 className="mt-2 text-xl font-bold tracking-tight text-[#0b1220]">
              {t("programCompare.title")}
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-[#64748b]">
              {t("programCompare.subtitle")}
            </p>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {PROGRAM_COMPARE_KEYS.map((key, i) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="border border-[#0b1220]/8 bg-white p-6 biz-shadow"
              >
                <h4 className="text-base font-semibold text-[#0b1220]">
                  {t(`programCompare.columns.${key}.title`)}
                </h4>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-[#2563eb]">
                  {t(`programCompare.columns.${key}.bestFor`)}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-[#64748b]">
                  {t(`programCompare.columns.${key}.body`)}
                </p>
              </motion.div>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-[#64748b]">{t("programCompare.footnote")}</p>
        </motion.div>

        <p className="mt-8 text-center text-xs text-[#64748b]">{t("footnote")}</p>
      </Container>
    </section>
  );
}
