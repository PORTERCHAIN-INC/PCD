"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  Coffee,
  Wine,
  UtensilsCrossed,
  ShoppingCart,
  Stethoscope,
  HardHat,
  Zap,
  Wind,
  Factory,
  Car,
  Store,
  Sofa,
  FlaskConical,
  ShoppingBag,
  Printer,
  Cog,
} from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import { BUSINESS_INDUSTRY_KEYS } from "@/data/business";
import { HOME_INDUSTRY_TO_NICHE_SLUG } from "@/lib/seo/industry-home-links";
import { solutionVerticalPath } from "@/lib/solutions-verticals";

const ICONS = [
  Coffee,
  Wine,
  UtensilsCrossed,
  ShoppingCart,
  Stethoscope,
  HardHat,
  Zap,
  Wind,
  Factory,
  Car,
  Store,
  Sofa,
  FlaskConical,
  ShoppingBag,
  Printer,
  Cog,
];

function playbookHref(key: (typeof BUSINESS_INDUSTRY_KEYS)[number]): string | undefined {
  if (key === "construction") return "/construction";
  if (key === "foodBeverage") return solutionVerticalPath("food-beverage");
  if (key === "medical") return solutionVerticalPath("medical");
  const niche = HOME_INDUSTRY_TO_NICHE_SLUG[key];
  return niche ? `/industry/${niche}` : undefined;
}

export default function BusinessIndustries() {
  const t = useTranslations("businessPage.industries");

  return (
    <section id="industries" className="biz-section bg-white">
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

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 md:grid-cols-4">
          {BUSINESS_INDUSTRY_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            const href = playbookHref(key);
            const label = t(`items.${key}`);
            const inner = (
              <>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-[#0b1220] transition-all biz-shadow group-hover:bg-[#2563eb]/10 group-hover:text-[#2563eb]">
                  <Icon className="h-5 w-5" strokeWidth={1.5} />
                </div>
                <span className="text-sm font-semibold leading-tight text-[#0b1220]">{label}</span>
              </>
            );

            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.03 }}
              >
                {href ? (
                  <Link
                    href={href}
                    className="group flex flex-col items-center gap-3 rounded-2xl border border-[#0b1220]/5 bg-[#f7f8fa] p-5 text-center transition-all hover:-translate-y-0.5 hover:border-[#2563eb]/30 hover:bg-white sm:p-6"
                  >
                    {inner}
                  </Link>
                ) : (
                  <div className="group flex cursor-default flex-col items-center gap-3 rounded-2xl border border-[#0b1220]/5 bg-[#f7f8fa] p-5 text-center sm:p-6">
                    {inner}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
        <p className="mt-8 text-center text-sm text-[#64748b]">{t("footnote")}</p>
      </Container>
    </section>
  );
}
