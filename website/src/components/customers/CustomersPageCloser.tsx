"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { ArrowRight, HardHat, MapPin, Quote, Route, TrendingDown, Truck } from "lucide-react";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import SiteImage from "@/components/ui/SiteImage";
import { siteImages } from "@/data/site-images";
import { Link } from "@/i18n/navigation";

const METRIC_KEYS = ["onTime", "cost", "volume"] as const;
const METRIC_ICONS = {
  onTime: Route,
  cost: TrendingDown,
  volume: Truck,
} as const;

const LANE_KEYS = ["0", "1", "2"] as const;

export default function CustomersPageCloser() {
  const t = useTranslations("corporate.customers");

  return (
    <section aria-labelledby="customers-page-closer" className="relative overflow-hidden">
      {/* Featured case study */}
      <div className="site-section bg-white relative">
        <div
          className="absolute inset-0 pointer-events-none opacity-40"
          aria-hidden
          style={{
            backgroundImage:
              "radial-gradient(circle at 0% 0%, rgba(37,99,235,0.07) 0%, transparent 45%), radial-gradient(circle at 100% 100%, rgba(56,189,248,0.06) 0%, transparent 40%)",
          }}
        />
        <Container className="relative">
          <div className="grid lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] gap-8 lg:gap-12 items-stretch">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5 }}
              className="relative overflow-hidden rounded-[1.75rem] border border-primary/[0.08] shadow-premium min-h-[320px] lg:min-h-full"
            >
              <SiteImage
                image={siteImages.industries.construction}
                fill
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 50vw"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a1628]/92 via-[#0a1628]/35 to-[#0a1628]/10" />
              <div className="absolute inset-0 p-6 sm:p-8 flex flex-col justify-end">
                <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white backdrop-blur-sm">
                  <HardHat className="h-3.5 w-3.5" aria-hidden />
                  {t("caseStudy.label")}
                </span>
                <p className="mt-4 text-2xl sm:text-3xl font-semibold tracking-tight text-white text-balance leading-tight">
                  {t("caseStudy.title")}
                </p>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.55, delay: 0.06 }}
              className="flex flex-col"
            >
              <h2 id="customers-page-closer" className="sr-only">
                {t("caseStudy.title")}
              </h2>
              <p className="text-base sm:text-lg text-muted leading-relaxed">
                {t("caseStudy.subtitle")}
              </p>

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
                {METRIC_KEYS.map((key, i) => {
                  const Icon = METRIC_ICONS[key];
                  return (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0, y: 10 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.35, delay: i * 0.05 }}
                      className="rounded-2xl border border-primary/[0.06] bg-gray-bg/80 px-4 py-4"
                    >
                      <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/10">
                        <Icon className="h-4 w-4 text-secondary" aria-hidden />
                      </div>
                      <p className="text-xl font-semibold tracking-tight text-primary">
                        {t(`caseStudy.metrics.${key}.value`)}
                      </p>
                      <p className="mt-1 text-xs text-muted leading-snug">
                        {t(`caseStudy.metrics.${key}.label`)}
                      </p>
                    </motion.div>
                  );
                })}
              </div>

              <blockquote className="mt-6 rounded-2xl border border-primary/[0.06] bg-white p-5 sm:p-6 shadow-premium">
                <Quote className="h-7 w-7 text-secondary/35 mb-3" aria-hidden />
                <p className="text-primary leading-relaxed font-medium">
                  &ldquo;{t("caseStudy.quote")}&rdquo;
                </p>
                <footer className="mt-4 text-sm text-muted">{t("caseStudy.quoteRole")}</footer>
              </blockquote>

              <div className="mt-6 flex flex-col sm:flex-row flex-wrap gap-3">
                <LinkButton
                  href={t("caseStudy.href")}
                  size="lg"
                  showArrow
                  trackSource="customers-case-study"
                  trackLabel={t("caseStudy.cta")}
                >
                  {t("caseStudy.cta")}
                </LinkButton>
                <Link
                  href={t("caseStudy.detailHref")}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-secondary hover:underline px-1 py-2"
                >
                  {t("caseStudy.detailCta")}
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              </div>
            </motion.div>
          </div>
        </Container>
      </div>

      {/* Lanes CTA */}
      <div className="relative overflow-hidden bg-primary">
        <div className="absolute inset-0 pointer-events-none" aria-hidden>
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,rgba(37,99,235,0.24)_0%,transparent_55%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_100%_100%,rgba(56,189,248,0.16)_0%,transparent_50%)]" />
          <div className="absolute inset-0 dot-pattern opacity-25" />
          <svg
            className="absolute inset-0 h-full w-full opacity-[0.14]"
            viewBox="0 0 1200 400"
            preserveAspectRatio="none"
            aria-hidden
          >
            <path
              d="M0 280 C180 220, 320 340, 520 260 S880 180, 1200 240"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-white"
              strokeDasharray="8 10"
            />
            <path
              d="M0 320 C220 260, 400 360, 640 300 S980 220, 1200 280"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="text-secondary"
              strokeDasharray="6 12"
            />
          </svg>
        </div>

        <Container className="relative site-section py-14 sm:py-16 lg:py-20">
          <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] gap-10 lg:gap-14 items-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              className="text-center lg:text-left"
            >
              <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white/80 backdrop-blur-sm">
                <MapPin className="h-3.5 w-3.5 text-secondary" aria-hidden />
                {t("cta.badge")}
              </span>
              <h3 className="mt-4 text-3xl sm:text-4xl lg:text-[2.75rem] font-semibold tracking-tight text-white text-balance leading-[1.08]">
                {t("cta.title")}
              </h3>
              <p className="mt-4 text-base sm:text-lg text-white/70 leading-relaxed max-w-xl mx-auto lg:mx-0">
                {t("cta.subtitle")}
              </p>

              <div className="mt-6 flex flex-wrap justify-center lg:justify-start gap-2">
                {LANE_KEYS.map((key) => (
                  <span
                    key={key}
                    className="inline-flex items-center rounded-full border border-white/12 bg-white/[0.06] px-3 py-1.5 text-xs font-medium text-white/80 backdrop-blur-sm"
                  >
                    {t(`cta.lanes.${key}`)}
                  </span>
                ))}
              </div>

              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3">
                <LinkButton
                  href="/sign-up?intent=quote&from=customers-cta"
                  size="lg"
                  showArrow
                  trackSource="customers-cta"
                  trackLabel={t("cta.primary")}
                >
                  {t("cta.primary")}
                </LinkButton>
                <LinkButton
                  href="/business#pricing"
                  variant="outlineOnDark"
                  size="lg"
                  trackSource="customers-cta"
                  trackLabel={t("cta.secondary")}
                >
                  {t("cta.secondary")}
                </LinkButton>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: 0.08 }}
              className="rounded-[1.75rem] border border-white/10 bg-white/[0.05] p-6 sm:p-8 backdrop-blur-sm"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/50">
                {t("cta.panel.label")}
              </p>
              <ul className="mt-5 space-y-4">
                {(["shipments", "vehicles", "areas"] as const).map((key, i) => (
                  <li
                    key={key}
                    className="flex gap-4 rounded-2xl border border-white/8 bg-white/[0.04] p-4"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary/15 text-secondary font-semibold text-sm">
                      {i + 1}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {t(`cta.panel.${key}.title`)}
                      </p>
                      <p className="mt-1 text-sm text-white/60 leading-relaxed">
                        {t(`cta.panel.${key}.description`)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </motion.div>
          </div>
        </Container>
      </div>
    </section>
  );
}
