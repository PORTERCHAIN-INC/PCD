"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import BookingWidget from "@/components/sections/BookingWidget";
import Container from "@/components/ui/Container";
import GtaSkyline from "@/components/illustrations/GtaSkyline";
import DeliveryVan from "@/components/illustrations/DeliveryVan";
import { useBooking } from "@/context/BookingContext";
import { cn } from "@/lib/utils";

const TAG_KEYS = [
  "looseParcels",
  "ltlFreight",
  "ftlLoads",
  "furniture",
  "construction",
  "medical",
  "food",
  "wholesale",
] as const;

export default function Hero() {
  const t = useTranslations("hero");
  const { bookingHighlight } = useBooking();

  return (
    <section className="relative min-h-[100svh] flex flex-col overflow-hidden bg-primary">
      {/* Background */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a1628] via-[#0f2744] to-[#0a1628]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_15%,rgba(37,99,235,0.2)_0%,transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_15%_85%,rgba(56,189,248,0.08)_0%,transparent_45%)]" />
        <GtaSkyline className="absolute bottom-0 left-0 w-full h-[50%] sm:h-[55%] opacity-90" />
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-secondary/12 rounded-full blur-3xl animate-pulse-glow" />
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-[#0a1628] to-transparent" />
      </div>

      <div className="absolute bottom-10 right-[4%] hidden 2xl:block animate-float z-[1] pointer-events-none">
        <DeliveryVan className="w-[min(280px,22vw)] drop-shadow-2xl opacity-90" />
      </div>

      <Container className="relative z-10 flex-1 flex flex-col pt-24 pb-8 sm:pt-28 sm:pb-10 md:pt-32 lg:pt-36 lg:pb-14">
        {/* Hero copy — centered, compact */}
        <div className="text-center max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
          >
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 border border-accent/25 text-white type-small font-bold mb-5 sm:mb-6 backdrop-blur-sm">
              <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
              {t("badge")}
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.08 }}
            className="type-display text-white text-balance"
          >
            {t("titleLine1")}{" "}
            <span className="gradient-text block sm:inline">{t("titleLine2")}</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.14 }}
            className="mt-4 sm:mt-5 type-lead text-white/75 max-w-2xl mx-auto"
          >
            {t("subtitle")}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.2 }}
            className="mt-4 sm:mt-6 flex flex-wrap justify-center gap-1.5 sm:gap-2 max-w-xl sm:max-w-none mx-auto"
          >
            {TAG_KEYS.map((key, i) => (
              <span
                key={key}
                className={cn(
                  "px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/85 type-small font-semibold",
                  i >= 4 && "hidden sm:inline-flex"
                )}
              >
                {t(`tags.${key}`)}
              </span>
            ))}
          </motion.div>
        </div>

        {/* Horizontal booking — full width, hero focus */}
        <motion.div
          id="book"
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, delay: 0.28 }}
          className={cn(
            "mt-8 sm:mt-10 lg:mt-14 w-full scroll-mt-nav rounded-2xl sm:rounded-[1.75rem] md:rounded-[2rem] transition-shadow duration-500",
            bookingHighlight &&
              "ring-4 ring-secondary/50 shadow-[0_0_40px_rgba(37,99,235,0.35)]"
          )}
        >
          <BookingWidget />
        </motion.div>
      </Container>
    </section>
  );
}
