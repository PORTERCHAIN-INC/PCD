"use client";

import { motion } from "framer-motion";
import Container from "@/components/ui/Container";
import TorontoOfficeIllustration from "@/components/corporate/illustrations/TorontoOfficeIllustration";

interface ContactHeroProps {
  badge: string;
  title: string;
  subtitle: string;
}

export default function ContactHero({ badge, title, subtitle }: ContactHeroProps) {
  return (
    <section className="relative pt-24 pb-12 md:pt-32 md:pb-16 overflow-hidden bg-primary">
      <div className="absolute inset-0 dot-pattern opacity-20 pointer-events-none" aria-hidden />
      <div
        className="absolute top-0 right-0 w-[500px] h-[400px] rounded-full bg-secondary/10 blur-3xl pointer-events-none"
        aria-hidden
      />
      <Container className="relative z-10">
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 text-white/90 text-xs font-semibold tracking-wide uppercase border border-white/10">
              {badge}
            </span>
            <h1 className="mt-5 text-4xl sm:text-5xl lg:text-[3.5rem] font-semibold text-white tracking-tight text-balance leading-[1.06]">
              {title}
            </h1>
            <p className="mt-5 text-lg text-white/65 leading-relaxed max-w-xl">{subtitle}</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.75, delay: 0.1 }}
            className="hidden sm:block"
          >
            <TorontoOfficeIllustration />
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
