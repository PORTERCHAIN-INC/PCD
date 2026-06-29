"use client";

import { motion } from "framer-motion";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/corporate/ui/LinkButton";
import CareersHeroIllustration from "@/components/corporate/illustrations/CareersHeroIllustration";

interface CareersHeroProps {
  badge: string;
  title: string;
  subtitle: string;
  primaryCta: string;
  secondaryCta: string;
}

export default function CareersHero({
  badge,
  title,
  subtitle,
  primaryCta,
  secondaryCta,
}: CareersHeroProps) {
  return (
    <section className="relative min-h-[88vh] flex items-center pt-20 pb-16 overflow-hidden bg-primary">
      <div className="absolute inset-0 dot-pattern opacity-25 pointer-events-none" aria-hidden />
      <div
        className="absolute -top-24 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-secondary/15 blur-3xl pointer-events-none"
        aria-hidden
      />
      <Container className="relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 text-white/90 text-xs font-semibold tracking-wide uppercase border border-white/10">
              {badge}
            </span>
            <h1 className="mt-6 text-4xl sm:text-5xl lg:text-[3.75rem] font-semibold text-white tracking-tight text-balance leading-[1.05]">
              {title}
            </h1>
            <p className="mt-5 text-lg sm:text-xl text-white/65 leading-relaxed max-w-xl">{subtitle}</p>
            <div className="mt-9 flex flex-col sm:flex-row gap-3">
              <a
                href="#positions"
                className="inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-full bg-secondary text-white font-semibold text-base hover:bg-[#1d4ed8] shadow-lg shadow-secondary/30 transition-all hover:scale-[1.02]"
              >
                {primaryCta}
              </a>
              <LinkButton
                href="/company"
                variant="outline"
                size="lg"
                className="border-white/30 text-white hover:bg-white/10"
              >
                {secondaryCta}
              </LinkButton>
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
          >
            <CareersHeroIllustration />
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
