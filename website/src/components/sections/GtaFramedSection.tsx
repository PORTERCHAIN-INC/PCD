"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { MapPin, ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import FramedPhoto from "@/components/ui/FramedPhoto";
import { siteImages } from "@/data/site-images";

export default function GtaFramedSection() {
  const t = useTranslations("gtaFrame");
  const cities = t.raw("cities") as string[];

  return (
    <section className="site-section bg-gray-bg overflow-hidden">
      <Container>
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-12 xl:gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="max-w-xl lg:max-w-none"
          >
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-secondary">
              <MapPin className="w-3.5 h-3.5" aria-hidden />
              {t("label")}
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl font-semibold text-primary tracking-tight text-balance leading-[1.12]">
              {t("title")}
            </h2>
            <p className="mt-4 text-muted leading-relaxed">{t("subtitle")}</p>
            <ul className="mt-6 flex flex-wrap gap-2">
              {cities.map((city) => (
                <li
                  key={city}
                  className="px-3 py-1.5 rounded-full bg-white border border-gray-200/80 text-primary/80 text-xs font-medium"
                >
                  {city}
                </li>
              ))}
            </ul>
            <Link
              href="/service-areas"
              className="mt-8 inline-flex items-center gap-2 text-secondary font-semibold text-sm hover:underline underline-offset-4"
            >
              {t("cta")}
              <ArrowRight className="w-4 h-4" />
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, delay: 0.1 }}
            className="flex justify-center lg:justify-center w-full py-4 lg:py-6"
          >
            <FramedPhoto
              image={siteImages.hero.gta}
              caption={t("caption")}
              size="lg"
              priority={false}
            />
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
