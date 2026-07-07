"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";
import { industries } from "@/data/industries";

export default function Industries() {
  const t = useTranslations("industries");

  return (
    <section id="industries" className="site-section bg-gray-bg">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          {industries.map((industry, i) => {
            const Icon = industry.icon;
            return (
              <motion.a
                key={industry.id}
                href={`#${industry.id}`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.04 }}
                className="group flex items-start gap-5 p-6 md:p-7 rounded-2xl bg-white border border-gray-200/80 hover:border-secondary/20 hover:shadow-premium transition-all duration-300"
              >
                <div className="w-12 h-12 rounded-xl bg-primary group-hover:bg-secondary flex items-center justify-center shrink-0 transition-colors duration-300">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="type-h3 font-semibold text-primary group-hover:text-secondary group-hover:font-bold transition-all">
                    {t(`items.${industry.id}.name`)}
                  </h3>
                  <p className="text-muted type-small mt-1 leading-relaxed">
                    {t(`items.${industry.id}.description`)}
                  </p>
                </div>
              </motion.a>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
