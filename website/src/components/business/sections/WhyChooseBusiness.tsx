"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import { BUSINESS_WHY_KEYS } from "@/data/business";
import {
  MapPin,
  ClipboardCheck,
  Camera,
  PenLine,
  Code,
  FileSpreadsheet,
  LayoutDashboard,
  UserCheck,
  CreditCard,
  Route,
  Calculator,
  BarChart3,
} from "lucide-react";

const ICONS = [
  MapPin,
  ClipboardCheck,
  Camera,
  PenLine,
  Code,
  FileSpreadsheet,
  LayoutDashboard,
  UserCheck,
  CreditCard,
  Route,
  Calculator,
  BarChart3,
];

export default function WhyChooseBusiness() {
  const t = useTranslations("businessPage.whyChoose");

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

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {BUSINESS_WHY_KEYS.map((key, i) => {
            const Icon = ICONS[i];
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: (i % 4) * 0.06 }}
                whileHover={{ scale: 1.02 }}
                className="p-5 rounded-2xl bg-white border border-[#091b1c]/6 biz-shadow biz-card-hover"
              >
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-[#091b1c] flex items-center justify-center text-[#ff7a00] shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#091b1c] text-sm">{t(`items.${key}`)}</h3>
                    <p className="mt-1 text-xs text-[#5c6b6c] leading-relaxed">
                      {t(`descriptions.${key}`)}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
