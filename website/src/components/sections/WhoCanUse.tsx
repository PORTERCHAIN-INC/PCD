"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { User, Building2, Check, ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";

export default function WhoCanUse() {
  const t = useTranslations("whoCanUse");
  const individualItems = t.raw("individuals.items") as string[];

  return (
    <section className="site-section bg-white">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="grid md:grid-cols-2 gap-5 sm:gap-6 lg:gap-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="rounded-3xl border border-gray-200/80 bg-gray-bg overflow-hidden hover:shadow-premium transition-shadow"
          >
            <HeroPhoto
              image={siteImages.sections.individuals}
              aspect="card"
              className="rounded-none shadow-none ring-0"
            />
            <div className="p-6 sm:p-8 md:p-10">
              <div className="flex items-center gap-4 mb-8">
                <div className="w-14 h-14 rounded-2xl bg-secondary/10 flex items-center justify-center">
                  <User className="w-7 h-7 text-secondary" />
                </div>
                <div>
                  <h3 className="type-h3 font-bold text-primary">{t("individuals.title")}</h3>
                  <p className="text-muted type-small mt-1">{t("individuals.subtitle")}</p>
                </div>
              </div>
              <ul className="space-y-3">
                {individualItems.map((item) => (
                  <li key={item} className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-secondary/10 flex items-center justify-center shrink-0">
                      <Check className="w-3 h-3 text-secondary" />
                    </div>
                    <span className="text-primary/80 type-small">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="rounded-3xl border border-primary/10 bg-primary overflow-hidden hover:shadow-lg hover:shadow-primary/20 transition-shadow flex flex-col"
          >
            <HeroPhoto
              image={siteImages.sections.business}
              aspect="card"
              className="rounded-none shadow-none ring-0"
            />
            <div className="p-6 sm:p-8 md:p-10 text-white flex flex-col flex-1">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-2xl bg-secondary flex items-center justify-center">
                  <Building2 className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h3 className="type-h3 font-bold">{t("businessCta.title")}</h3>
                  <p className="text-white/60 type-small mt-1">{t("businessCta.subtitle")}</p>
                </div>
              </div>
              <p className="text-white/75 type-small leading-relaxed flex-1">
                {t("businessCta.description")}
              </p>
              <Link
                href="/business"
                className="mt-8 inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-secondary text-white font-semibold type-small hover:bg-[#1d4ed8] transition-colors"
              >
                {t("businessCta.cta")}
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
