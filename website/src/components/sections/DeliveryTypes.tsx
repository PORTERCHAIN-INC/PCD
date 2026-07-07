"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";
import { deliveryTypes } from "@/data/delivery-types";
import { cn } from "@/lib/utils";

export default function DeliveryTypes() {
  const t = useTranslations("deliveryTypes");
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <section id="solutions" className="site-section bg-gray-bg">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-2.5 sm:gap-3 md:gap-4">
          {deliveryTypes.map((type, i) => {
            const Icon = type.icon;
            const isSelected = selected === type.id;
            return (
              <motion.button
                key={type.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.04 }}
                onClick={() => setSelected(isSelected ? null : type.id)}
                className={cn(
                  "group flex flex-col items-center gap-2.5 sm:gap-3 p-3 sm:p-4 md:p-5 min-h-[6.5rem] sm:min-h-[7.5rem] rounded-2xl border transition-all duration-200 cursor-pointer",
                  isSelected
                    ? "bg-primary text-white border-primary shadow-lg shadow-primary/20"
                    : "bg-white border-gray-200/80 hover:border-secondary/30 hover:shadow-premium"
                )}
              >
                <div
                  className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center transition-colors",
                    isSelected
                      ? "bg-secondary text-white"
                      : "bg-gray-bg text-primary group-hover:bg-secondary/10 group-hover:text-secondary"
                  )}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <span
                  className={cn(
                    "type-small text-center leading-tight",
                    isSelected ? "text-white font-bold" : "text-primary font-semibold"
                  )}
                >
                  {t(`items.${type.id}`)}
                </span>
              </motion.button>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
