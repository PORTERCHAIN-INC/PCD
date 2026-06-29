"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import BookingWidget from "@/components/sections/BookingWidget";
import Container from "@/components/ui/Container";
import GtaSkyline from "@/components/illustrations/GtaSkyline";
import DeliveryVan from "@/components/illustrations/DeliveryVan";
import { useBooking } from "@/context/BookingContext";
import { cn } from "@/lib/utils";

export default function Hero() {
  const t = useTranslations("hero");
  const { bookingHighlight } = useBooking();

  return (
    <section className="relative h-[100svh] max-h-[100svh] flex flex-col overflow-hidden bg-primary">
      {/* Background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a1628] via-[#0f2744] to-[#0a1628]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_15%,rgba(37,99,235,0.2)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_15%_85%,rgba(56,189,248,0.08)_0%,transparent_45%)]" />
        <GtaSkyline className="absolute bottom-0 left-0 w-full h-[38%] sm:h-[42%] opacity-75" />
        <div className="absolute top-1/4 right-1/4 w-72 h-72 bg-secondary/10 rounded-full blur-3xl animate-pulse-glow" />
        <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#0a1628] to-transparent" />
      </div>

      <div className="absolute bottom-6 right-[3%] hidden xl:block animate-float z-[1] pointer-events-none">
        <DeliveryVan className="w-[min(200px,16vw)] drop-shadow-2xl opacity-80" />
      </div>

      <Container className="relative z-10 flex-1 flex flex-col min-h-0 pt-[4.25rem] pb-3 sm:pt-[4.5rem] sm:pb-4">
        <div className="flex-1 min-h-0 flex flex-col items-center justify-start mx-auto w-full max-w-4xl">
          {/* Hero copy — upper portion of booking area */}
          <div className="shrink-0 text-center mb-3 sm:mb-4 lg:mb-5">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
            >
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 border border-accent/25 text-white text-xs sm:text-sm font-bold mb-2 sm:mb-3 backdrop-blur-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                {t("badge")}
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.06 }}
              className="text-[1.75rem] leading-[1.1] sm:text-4xl lg:text-5xl font-bold tracking-tight text-white text-balance"
            >
              {t("titleLine1")}{" "}
              <span className="gradient-text block sm:inline">{t("titleLine2")}</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.1 }}
              className="mt-2 sm:mt-3 text-sm sm:text-base lg:text-lg text-white/75 max-w-xl mx-auto"
            >
              {t("subtitle")}
            </motion.p>
          </div>

          {/* Booking — fills remaining viewport height */}
          <motion.div
            id="book"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.18 }}
            className={cn(
              "w-full min-h-0 flex-1 flex flex-col scroll-mt-nav",
              bookingHighlight &&
                "rounded-2xl ring-4 ring-secondary/50 shadow-[0_0_40px_rgba(37,99,235,0.35)]"
            )}
          >
            <BookingWidget variant="compact" className="min-h-0 flex-1" />
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
