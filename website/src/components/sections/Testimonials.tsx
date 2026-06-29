"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Star, Quote } from "lucide-react";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";

const TESTIMONIAL_KEYS = ["coffee", "medical", "restaurant", "electrical"] as const;

export default function Testimonials() {
  const t = useTranslations("testimonials");

  return (
    <section className="site-section bg-gray-bg">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="grid md:grid-cols-2 gap-5 sm:gap-6">
          {TESTIMONIAL_KEYS.map((key, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="relative p-6 sm:p-8 rounded-2xl bg-white border border-gray-200/80 shadow-premium hover:shadow-lg transition-shadow"
            >
              <Quote className="w-8 h-8 text-secondary/20 absolute top-6 right-6" />

              <div className="flex gap-1 mb-4">
                {Array.from({ length: 5 }).map((_, j) => (
                  <Star key={j} className="w-4 h-4 fill-secondary text-secondary" />
                ))}
              </div>

              <p className="text-primary/80 type-body leading-relaxed">
                &ldquo;{t(`items.${key}.quote`)}&rdquo;
              </p>

              <div className="mt-6 flex items-center gap-4">
                <div className="w-11 h-11 rounded-full bg-primary flex items-center justify-center text-white font-bold text-sm">
                  {t(`items.${key}.author`)
                    .split(" ")
                    .map((n) => n[0])
                    .join("")}
                </div>
                <div>
                  <p className="font-bold text-primary type-small">{t(`items.${key}.author`)}</p>
                  <p className="text-muted type-caption normal-case tracking-normal">
                    {t(`items.${key}.role`)}, {t(`items.${key}.company`)}
                  </p>
                </div>
                <span className="ml-auto type-caption font-bold normal-case tracking-normal text-secondary bg-secondary/10 px-3 py-1 rounded-full">
                  {t(`items.${key}.industry`)}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  );
}
