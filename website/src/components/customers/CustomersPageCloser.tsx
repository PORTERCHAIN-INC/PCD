"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { MapPin } from "lucide-react";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";

const LANE_KEYS = ["0", "1", "2"] as const;

/** Capacity closer for /customers — no case-study theater until permissioned stories exist. */
export default function CustomersPageCloser() {
  const t = useTranslations("corporate.customers");

  return (
    <section aria-labelledby="customers-page-closer" className="relative overflow-hidden">
      <div className="relative overflow-hidden bg-primary">
        <div className="absolute inset-0 pointer-events-none" aria-hidden>
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,rgba(37,99,235,0.24)_0%,transparent_55%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_100%_100%,rgba(56,189,248,0.16)_0%,transparent_50%)]" />
          <div className="absolute inset-0 dot-pattern opacity-25" />
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
              <h2
                id="customers-page-closer"
                className="mt-4 text-3xl sm:text-4xl lg:text-[2.75rem] font-semibold tracking-tight text-white text-balance leading-[1.08]"
              >
                {t("cta.title")}
              </h2>
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
