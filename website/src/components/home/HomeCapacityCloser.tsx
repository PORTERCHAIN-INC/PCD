"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import {
  BarChart3,
  Building2,
  Camera,
  LayoutDashboard,
  MapPin,
  Radio,
  Receipt,
  Smartphone,
  type LucideIcon,
} from "lucide-react";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { industries } from "@/data/industries";
import { cn } from "@/lib/utils";

const CUSTOMER_INDUSTRY_IDS = [
  "construction",
  "pharmacy",
  "manufacturing",
  "wholesale",
  "medical",
  "electrical",
] as const;

const CAPABILITY_KEYS = ["portal", "driver", "tower", "tracking", "pod", "billing"] as const;

const CAPABILITY_ICONS: Record<(typeof CAPABILITY_KEYS)[number], LucideIcon> = {
  portal: LayoutDashboard,
  driver: Smartphone,
  tower: Radio,
  tracking: MapPin,
  pod: Camera,
  billing: Receipt,
};

const STAT_KEYS = ["onTime", "visibility", "exceptions", "audit"] as const;

export default function HomeCapacityCloser() {
  const t = useTranslations("corporate.home");
  const tIndustries = useTranslations("industries");

  const industryCards = CUSTOMER_INDUSTRY_IDS.map((id) => {
    const industry = industries.find((item) => item.id === id);
    return {
      id,
      icon: industry?.icon ?? Building2,
      name: tIndustries(`items.${id}.name`),
    };
  });

  return (
    <section aria-labelledby="home-capacity-closer" className="relative overflow-hidden">
      {/* Customer proof */}
      <div className="site-section bg-white relative">
        <div
          className="absolute inset-0 pointer-events-none opacity-[0.35]"
          aria-hidden
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, rgba(37,99,235,0.08) 0%, transparent 42%), radial-gradient(circle at 80% 0%, rgba(56,189,248,0.06) 0%, transparent 38%)",
          }}
        />
        <Container className="relative">
          <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] gap-10 lg:gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5 }}
            >
              <span className="inline-flex items-center gap-2 rounded-full border border-secondary/20 bg-secondary/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-secondary">
                {t("caseStudy.label")}
              </span>
              <h2
                id="home-capacity-closer"
                className="mt-4 text-3xl sm:text-4xl lg:text-[2.6rem] font-semibold tracking-tight text-primary text-balance leading-[1.08]"
              >
                {t("caseStudy.title")}
              </h2>
              <p className="mt-4 text-base sm:text-lg text-muted leading-relaxed max-w-xl">
                {t("caseStudy.subtitle")}
              </p>
              <div className="mt-8 flex flex-col sm:flex-row flex-wrap gap-3">
                <LinkButton
                  href={t("caseStudy.href")}
                  size="lg"
                  showArrow
                  trackSource="home-case-study"
                  trackLabel={t("caseStudy.cta")}
                >
                  {t("caseStudy.cta")}
                </LinkButton>
                <LinkButton
                  href="/business#fleet"
                  variant="outline"
                  size="lg"
                  trackSource="home-case-study"
                  trackLabel={t("hero.secondaryCta")}
                >
                  {t("hero.secondaryCta")}
                </LinkButton>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.55, delay: 0.08 }}
              className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4"
            >
              {industryCards.map((industry, i) => {
                const Icon = industry.icon;
                return (
                  <motion.div
                    key={industry.id}
                    initial={{ opacity: 0, scale: 0.96 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.35, delay: i * 0.05 }}
                    className={cn(
                      "group relative overflow-hidden rounded-2xl border bg-white p-4 sm:p-5 shadow-premium transition-all duration-300",
                      "border-primary/[0.06] hover:border-secondary/25 hover:-translate-y-0.5 hover:shadow-glow-blue",
                      i === 0 &&
                        "sm:col-span-2 sm:row-span-1 bg-gradient-to-br from-primary to-[#152238] text-white border-transparent"
                    )}
                  >
                    <div
                      className={cn(
                        "mb-3 flex h-10 w-10 items-center justify-center rounded-xl",
                        i === 0 ? "bg-white/10" : "bg-secondary/10"
                      )}
                    >
                      <Icon
                        className={cn("h-5 w-5", i === 0 ? "text-white" : "text-secondary")}
                        aria-hidden
                      />
                    </div>
                    <p
                      className={cn(
                        "text-sm font-semibold tracking-tight",
                        i === 0 ? "text-white" : "text-primary"
                      )}
                    >
                      {industry.name}
                    </p>
                    {i === 0 && (
                      <p className="mt-1 text-xs text-white/65 leading-relaxed">
                        {tIndustries("featuredLabel")}
                      </p>
                    )}
                  </motion.div>
                );
              })}
            </motion.div>
          </div>
        </Container>
      </div>

      {/* Operations layer */}
      <div className="site-section bg-gray-bg py-12 sm:py-16 lg:py-20">
        <Container>
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            className="rounded-[2rem] border border-primary/[0.06] bg-white p-6 sm:p-8 lg:p-10 shadow-premium"
          >
            <div className="grid lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-8 lg:gap-12 items-start">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-primary/[0.04] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">
                  <BarChart3 className="h-3.5 w-3.5 text-secondary" aria-hidden />
                  Operations
                </div>
                <h3 className="mt-4 text-2xl sm:text-3xl font-semibold tracking-tight text-primary text-balance">
                  {t("developerStrip.title")}
                </h3>
                <p className="mt-3 text-muted leading-relaxed">{t("developerStrip.subtitle")}</p>
                <div className="mt-6">
                  <LinkButton
                    href={t("developerStrip.href")}
                    variant="secondary"
                    showArrow
                    trackSource="home-developers"
                    trackLabel={t("developerStrip.primary")}
                  >
                    {t("developerStrip.primary")}
                  </LinkButton>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {CAPABILITY_KEYS.map((key, i) => {
                  const Icon = CAPABILITY_ICONS[key];
                  return (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0, y: 12 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.35, delay: i * 0.04 }}
                      className="group rounded-2xl border border-primary/[0.06] bg-gray-bg/80 p-4 transition-all duration-300 hover:border-secondary/20 hover:bg-white hover:shadow-premium"
                    >
                      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-white border border-primary/[0.05] group-hover:border-secondary/15 transition-colors">
                        <Icon className="h-4 w-4 text-secondary" aria-hidden />
                      </div>
                      <p className="text-sm font-semibold text-primary leading-snug">
                        {t(`developerStrip.capabilities.${key}`)}
                      </p>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        </Container>
      </div>

      {/* Final quote CTA */}
      <div className="relative overflow-hidden bg-primary">
        <div className="absolute inset-0 pointer-events-none" aria-hidden>
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_15%_0%,rgba(37,99,235,0.22)_0%,transparent_52%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_85%_100%,rgba(56,189,248,0.14)_0%,transparent_48%)]" />
          <div className="absolute inset-0 dot-pattern opacity-30" />
        </div>

        <Container className="relative site-section py-14 sm:py-16 lg:py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            className="max-w-3xl mx-auto text-center"
          >
            <h3 className="text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight text-white text-balance">
              {t("cta.title")}
            </h3>
            <p className="mt-4 text-base sm:text-lg text-white/70 leading-relaxed max-w-2xl mx-auto">
              {t("cta.subtitle")}
            </p>

            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <LinkButton
                href="/sign-up?intent=quote&from=home-cta"
                size="lg"
                showArrow
                trackSource="home-cta"
                trackLabel={t("cta.primary")}
              >
                {t("cta.primary")}
              </LinkButton>
              <LinkButton
                href="/business"
                variant="outlineOnDark"
                size="lg"
                trackSource="home-cta"
                trackLabel={t("cta.secondary")}
              >
                {t("cta.secondary")}
              </LinkButton>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ delay: 0.1 }}
            className="mt-10 sm:mt-12 grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 max-w-5xl mx-auto"
          >
            {STAT_KEYS.map((key) => (
              <div
                key={key}
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 sm:px-5 sm:py-5 backdrop-blur-sm"
              >
                <p className="text-lg sm:text-xl font-semibold text-white tracking-tight">
                  {t(`stats.${key}.value`)}
                </p>
                <p className="mt-1 text-xs sm:text-sm text-white/60 leading-snug">
                  {t(`stats.${key}.label`)}
                </p>
              </div>
            ))}
          </motion.div>
        </Container>
      </div>
    </section>
  );
}
