"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";
import { industries } from "@/data/industries";
import { HOME_INDUSTRY_TO_NICHE_SLUG } from "@/lib/seo/industry-home-links";
import { cn } from "@/lib/utils";
import { getIndustryImage } from "@/data/site-images";
import SiteImage from "@/components/ui/SiteImage";

export default function Industries() {
  const t = useTranslations("industries");

  return (
    <section id="industries" className="site-section bg-gray-bg">
      <Container>
        <SectionHeader label={t("label")} title={t("title")} subtitle={t("subtitle")} />

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          {industries.map((industry, i) => {
            const Icon = industry.icon;
            const nicheSlug = HOME_INDUSTRY_TO_NICHE_SLUG[industry.id];
            const href = nicheSlug ? `/industry/${nicheSlug}` : `#${industry.id}`;
            const isFeatured = industry.featured;
            const Card = nicheSlug ? Link : "a";

            return (
              <motion.div
                key={industry.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.04 }}
              >
                <Card
                  href={href}
                  className={cn(
                    "group flex flex-col overflow-hidden rounded-2xl bg-white border transition-all duration-300 h-full",
                    isFeatured
                      ? "border-secondary/30 ring-1 ring-secondary/10 hover:border-secondary/50 hover:shadow-premium"
                      : "border-gray-200/80 hover:border-secondary/20 hover:shadow-premium"
                  )}
                >
                  <div className="relative h-32 sm:h-36 overflow-hidden">
                    <SiteImage
                      image={getIndustryImage(industry.id)}
                      fill
                      className="object-cover group-hover:scale-[1.03] transition-transform duration-500"
                      sizes="(max-width: 640px) 50vw, 33vw"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                    <div
                      className={cn(
                        "absolute bottom-3 left-3 w-10 h-10 rounded-xl flex items-center justify-center",
                        isFeatured ? "bg-secondary" : "bg-primary"
                      )}
                    >
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                  </div>
                  <div className="flex-1 p-5 md:p-6 flex flex-col">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="type-h3 font-semibold text-primary group-hover:text-secondary group-hover:font-bold transition-all">
                        {t(`items.${industry.id}.name`)}
                      </h3>
                      {nicheSlug && (
                        <ArrowRight className="w-4 h-4 text-secondary opacity-0 group-hover:opacity-100 shrink-0 mt-1 transition-opacity" />
                      )}
                    </div>
                    <p className="text-muted type-small mt-1 leading-relaxed flex-1">
                      {t(`items.${industry.id}.description`)}
                    </p>
                    {isFeatured && nicheSlug && (
                      <span className="inline-block mt-2 text-xs font-semibold uppercase tracking-wide text-secondary">
                        {t("featuredLabel")}
                      </span>
                    )}
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-10 text-center">
          <Link
            href="/industry"
            className="inline-flex items-center gap-2 text-secondary font-semibold type-small hover:underline"
          >
            {t("viewAll")}
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Container>
    </section>
  );
}
