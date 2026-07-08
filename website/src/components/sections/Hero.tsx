"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import BookingWidget from "@/components/sections/BookingWidget";
import Container from "@/components/ui/Container";
import SiteImage from "@/components/ui/SiteImage";
import { siteImages } from "@/data/site-images";
import { useBooking } from "@/context/BookingContext";
import { cn } from "@/lib/utils";

export default function Hero() {
  const t = useTranslations("hero");
  const { bookingHighlight } = useBooking();

  return (
    <section className="relative overflow-hidden bg-primary">
      {/* Background */}
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

      <Container className="relative z-10 pt-[4.5rem] pb-10 sm:pt-24 sm:pb-12 lg:pt-28 lg:pb-14">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(320px,400px)] xl:grid-cols-[minmax(0,1fr)_420px] gap-8 lg:gap-10 xl:gap-12 items-center">
          {/* Copy */}
          <div className="text-center lg:text-left max-w-xl mx-auto lg:mx-0">
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
              {t("titleLine1")}{" "}
              <span className="gradient-text block sm:inline">{t("titleLine2")}</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.1 }}
              className="mt-2 sm:mt-3 text-sm sm:text-base text-white/70 max-w-md mx-auto lg:mx-0"
            >
              {t("subtitle")}
            </motion.p>
          </div>

          {/* Booking card */}
          <motion.div
            id="book"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.14 }}
            className={cn(
              "w-full max-w-md mx-auto lg:max-w-none scroll-mt-nav",
              bookingHighlight &&
                "rounded-2xl ring-4 ring-secondary/50 shadow-[0_0_32px_rgba(37,99,235,0.35)]"
            )}
          >
            <BookingWidget variant="hero" />
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
