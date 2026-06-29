"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_CHALLENGE_KEYS } from "@/data/business";
import {
  DollarSign,
  Clock,
  CalendarX,
  EyeOff,
  Users,
  MapPinOff,
  FileText,
  TrendingDown,
} from "lucide-react";

const ICONS = [
  DollarSign,
  Clock,
  CalendarX,
  EyeOff,
  Users,
  MapPinOff,
  FileText,
  TrendingDown,
];

export default function BusinessChallenges() {
  const t = useTranslations("businessPage.challenges");

  return (
    <section className="biz-section bg-[#f7f8fa]">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center max-w-2xl mx-auto mb-14"
        >
          <h2 className="biz-heading text-[#091b1c] tracking-tight">
            {t("title")}
          </h2>
          <p className="mt-4 text-[#5c6b6c] leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          {BUSINESS_CHALLENGE_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="p-6 rounded-2xl bg-white border border-[#091b1c]/6 biz-shadow biz-card-hover"
              >
                <div className="w-10 h-10 rounded-xl bg-[#ff7a00]/10 flex items-center justify-center text-[#ff7a00] mb-4">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-[#091b1c] mb-2">{t(`items.${key}.title`)}</h3>
                <p className="text-sm text-[#5c6b6c] leading-relaxed">
                  {t(`items.${key}.description`)}
                </p>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
