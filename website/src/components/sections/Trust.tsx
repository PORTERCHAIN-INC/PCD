"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import AnimatedCounter from "@/components/ui/AnimatedCounter";
import Container from "@/components/ui/Container";
import LogisticsPattern from "@/components/illustrations/LogisticsPattern";

const STATS = [
  { value: 1000, suffix: "+", labelKey: "customers" as const },
  { value: 50000, suffix: "+", labelKey: "deliveries" as const },
  { value: 98, suffix: "%", labelKey: "onTime" as const },
  { value: 24, suffix: "/7", labelKey: "support" as const },
];

export default function Trust() {
  const t = useTranslations("trust");

  return (
    <section className="relative py-12 sm:py-16 md:py-20 bg-primary overflow-hidden">
      <LogisticsPattern className="absolute inset-0 w-full h-full opacity-40 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-primary via-transparent to-primary" />
      <Container className="relative">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8 lg:gap-12">
          {STATS.map((stat, i) => (
            <motion.div
              key={stat.labelKey}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="text-center"
            >
              <p className="type-stat text-white">
                <AnimatedCounter value={stat.value} suffix={stat.suffix} />
              </p>
              <p className="mt-2 text-accent/80 type-caption font-bold">{t(stat.labelKey)}</p>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  );
}
