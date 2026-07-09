"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import SiteImage from "@/components/ui/SiteImage";
import LinkButton from "@/components/corporate/ui/LinkButton";
import { siteImages } from "@/data/site-images";
import { customerPortalBookUrl } from "@/data/portal-links";

export default function Hero() {
  const t = useTranslations("corporate.home.hero");

  return (
    <section className="relative overflow-hidden bg-primary">
      <div className="absolute inset-0 pointer-events-none">
        <SiteImage
          image={siteImages.hero.gta}
          fill
          className="object-cover object-[center_35%] opacity-40"
          sizes="100vw"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a1628]/88 via-[#0f2744]/82 to-[#0a1628]/92" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_15%,rgba(37,99,235,0.12)_0%,transparent_50%)]" />
        <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#0a1628] to-transparent" />
      </div>

      <Container className="relative z-10 pt-[4.5rem] pb-12 sm:pt-24 sm:pb-16 lg:pt-28 lg:pb-20">
        <div className="max-w-3xl mx-auto text-center lg:text-left lg:mx-0">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
          >
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/10 border border-accent/25 text-white text-[11px] sm:text-xs font-bold backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              {t("badge")}
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.06 }}
            className="mt-3 text-[1.65rem] leading-[1.12] sm:text-3xl lg:text-[2.35rem] xl:text-4xl font-bold tracking-tight text-white text-balance"
          >
            {t("title")}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
            className="mt-3 text-sm sm:text-base text-white/70 max-w-2xl mx-auto lg:mx-0"
          >
            {t("subtitle")}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.14 }}
            className="mt-8 flex flex-col sm:flex-row flex-wrap items-center justify-center lg:justify-start gap-3"
          >
            <LinkButton href="/contact" size="lg">
              {t("primaryCta")}
            </LinkButton>
            <LinkButton
              href="/platform"
              variant="outline"
              size="lg"
              className="border-white/30 text-white hover:bg-white/10"
            >
              {t("secondaryCta")}
            </LinkButton>
            <a
              href={customerPortalBookUrl}
              className="text-sm font-semibold text-white/85 hover:text-white underline underline-offset-4"
            >
              {t("bookDeliveryCta")}
            </a>
            <Link href="/track" className="text-sm font-medium text-white/70 hover:text-white">
              {t("trackCta")}
            </Link>
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
