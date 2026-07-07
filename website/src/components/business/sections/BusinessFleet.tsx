"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Container from "@/components/ui/Container";
import VehicleIllustration from "@/components/illustrations/VehicleIllustration";
import { BUSINESS_FLEET_KEYS, FLEET_ILLUSTRATIONS } from "@/data/business";
import { Info } from "lucide-react";

export default function BusinessFleet() {
  const t = useTranslations("businessPage.fleet");

  return (
    <section className="biz-section bg-white">
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
          <h2 className="mt-3 biz-heading text-[#091b1c] tracking-tight">{t("title")}</h2>
          <p className="mt-4 text-[#5c6b6c] leading-relaxed">{t("subtitle")}</p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          {BUSINESS_FLEET_KEYS.map((key, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="group rounded-2xl bg-[#f7f8fa] border border-[#091b1c]/6 overflow-hidden biz-card-hover"
            >
              <div className="relative h-36 bg-gradient-to-br from-slate-800 to-[#091b1c] flex items-center justify-center overflow-hidden">
                <div className="absolute inset-0 opacity-[0.06]">
                  <div
                    className="absolute inset-0"
                    style={{
                      backgroundImage:
                        "linear-gradient(rgba(255,255,255,.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.2) 1px, transparent 1px)",
                      backgroundSize: "20px 20px",
                    }}
                  />
                </div>
                <VehicleIllustration
                  type={FLEET_ILLUSTRATIONS[key]}
                  id={`biz-${key}`}
                  variant="light"
                  className="w-[5.4rem] h-auto relative z-10 opacity-[0.97] group-hover:scale-[1.03] transition-transform duration-500"
                />
              </div>
              <div className="p-5">
                <h3 className="font-semibold text-[#091b1c]">{t(`items.${key}.name`)}</h3>
                <div className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#5c6b6c]">{t("payload")}</span>
                    <span className="font-medium text-[#091b1c]">{t(`items.${key}.payload`)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5c6b6c]">{t("cargoSpace")}</span>
                    <span className="font-medium text-[#091b1c]">{t(`items.${key}.cargo`)}</span>
                  </div>
                </div>
                <p className="mt-3 text-xs text-[#5c6b6c] leading-relaxed border-t border-[#091b1c]/6 pt-3">
                  {t(`items.${key}.useCase`)}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mt-10 flex items-start gap-3 p-5 rounded-2xl bg-[#ff7a00]/8 border border-[#ff7a00]/20 max-w-3xl mx-auto"
        >
          <Info className="w-5 h-5 text-[#ff7a00] shrink-0 mt-0.5" />
          <p className="text-sm text-[#091b1c] leading-relaxed">{t("licenceNote")}</p>
        </motion.div>
      </Container>
    </section>
  );
}
