"use client";

import { motion, useReducedMotion } from "framer-motion";
import { MessageCircle, ShieldCheck, Clock3 } from "lucide-react";
import Container from "@/components/ui/Container";
import { easeOutExpo, staggerContainer, fadeUp } from "@/lib/motion";
import { cn } from "@/lib/utils";

interface ContactHeroProps {
  badge: string;
  title: string;
  subtitle: string;
  variant?: "default" | "quote";
  trustItems?: string[];
}

export default function ContactHero({
  badge,
  title,
  subtitle,
  variant = "default",
  trustItems,
}: ContactHeroProps) {
  const reduce = useReducedMotion();
  const isQuote = variant === "quote";

  return (
    <section
      className={cn(
        "relative overflow-hidden bg-primary",
        isQuote ? "pt-24 pb-16 md:pt-28 md:pb-20" : "pt-24 pb-12 md:pt-32 md:pb-16"
      )}
    >
      <div className="absolute inset-0" aria-hidden>
        <div className="absolute inset-0 bg-gradient-to-br from-primary via-[#0d1a2e] to-primary" />
        <div className="absolute -right-24 top-0 h-[28rem] w-[28rem] rounded-full bg-secondary/20 blur-3xl" />
        <div className="absolute -left-16 bottom-0 h-64 w-64 rounded-full bg-accent/15 blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.12]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.35) 1px, transparent 0)",
            backgroundSize: "28px 28px",
          }}
        />
      </div>

      <Container className="relative z-10">
        <motion.div
          className={cn(isQuote ? "mx-auto max-w-3xl text-center" : "max-w-2xl")}
          initial={reduce ? false : "hidden"}
          animate="visible"
          variants={staggerContainer}
        >
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.6, ease: easeOutExpo }}
            className="pc-eyebrow text-accent"
          >
            {badge}
          </motion.p>
          <motion.h1
            variants={fadeUp}
            transition={{ duration: 0.7, ease: easeOutExpo }}
            className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl lg:text-[2.75rem] lg:leading-[1.1]"
          >
            {title}
          </motion.h1>
          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.65, ease: easeOutExpo }}
            className={cn(
              "mt-4 text-base leading-relaxed text-white/70 sm:text-lg",
              isQuote ? "mx-auto max-w-2xl" : "max-w-xl"
            )}
          >
            {subtitle}
          </motion.p>

          {isQuote && trustItems && trustItems.length > 0 ? (
            <motion.ul
              variants={fadeUp}
              transition={{ duration: 0.6, ease: easeOutExpo }}
              className="mt-8 flex flex-wrap items-center justify-center gap-3"
            >
              {trustItems.map((item, i) => {
                const Icon = i === 0 ? Clock3 : i === 1 ? ShieldCheck : MessageCircle;
                return (
                  <li
                    key={item}
                    className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.06] px-3.5 py-2 text-xs font-semibold text-white/80 backdrop-blur-sm"
                  >
                    <Icon className="h-3.5 w-3.5 text-accent" aria-hidden />
                    {item}
                  </li>
                );
              })}
            </motion.ul>
          ) : null}
        </motion.div>
      </Container>
    </section>
  );
}
