"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import FadeIn from "@/components/marketing/corporate/motion/FadeIn";
import {
  resolveFeatureIcon,
  type FeatureIconName,
} from "@/components/marketing/corporate/icons/feature-icons";
import type { SiteImageRef } from "@/data/site-images";
import SiteImage from "@/components/ui/SiteImage";
import { springSnappy } from "@/lib/motion";

export interface FeatureItem {
  title: string;
  description: string;
  /** Serializable Lucide key — do not pass component functions from Server Components */
  icon?: FeatureIconName;
  image?: SiteImageRef;
}

interface FeatureSectionProps {
  label?: string;
  title: string;
  subtitle?: string;
  items: FeatureItem[];
  variant?: "grid" | "rows" | "pillars";
  className?: string;
  id?: string;
}

export default function FeatureSection({
  label,
  title,
  subtitle,
  items,
  variant = "grid",
  className,
  id,
}: FeatureSectionProps) {
  const reduce = useReducedMotion();

  if (variant === "rows") {
    return (
      <section id={id} className={cn("site-section bg-white", className)}>
        <Container>
          <SectionHeader
            label={label}
            title={title}
            subtitle={subtitle}
            align="left"
            className="max-w-2xl"
          />
          <div className="space-y-2 mt-8">
            {items.map((item, i) => (
              <FadeIn key={i} delay={i * 0.06}>
                <motion.div
                  className="grid md:grid-cols-[1fr_2fr] gap-3 md:gap-10 py-5 border-b border-primary/[0.06] last:border-0"
                  whileHover={reduce ? undefined : { x: 4 }}
                  transition={springSnappy}
                >
                  <h3 className="text-lg font-semibold text-primary tracking-tight">
                    {item.title}
                  </h3>
                  <p className="text-muted leading-relaxed">{item.description}</p>
                </motion.div>
              </FadeIn>
            ))}
          </div>
        </Container>
      </section>
    );
  }

  if (variant === "pillars") {
    return (
      <section id={id} className={cn("site-section bg-primary text-white", className)}>
        <Container>
          <SectionHeader label={label} title={title} subtitle={subtitle} dark />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {items.map((item, i) => {
              const Icon = resolveFeatureIcon(item.icon);
              return (
                <FadeIn key={i} delay={i * 0.08}>
                  <motion.div
                    className="p-6 rounded-2xl bg-white/[0.04] border border-white/[0.08] h-full"
                    whileHover={
                      reduce ? undefined : { y: -6, backgroundColor: "rgba(255,255,255,0.07)" }
                    }
                    transition={springSnappy}
                  >
                    {Icon ? <Icon className="w-5 h-5 text-secondary mb-4" aria-hidden /> : null}
                    <h3 className="text-base font-semibold tracking-tight">{item.title}</h3>
                    <p className="mt-2 text-sm text-white/60 leading-relaxed">{item.description}</p>
                  </motion.div>
                </FadeIn>
              );
            })}
          </div>
        </Container>
      </section>
    );
  }

  return (
    <section id={id} className={cn("site-section bg-white", className)}>
      <Container>
        <SectionHeader label={label} title={title} subtitle={subtitle} />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((item, i) => {
            const Icon = resolveFeatureIcon(item.icon);
            return (
              <FadeIn key={i} delay={i * 0.06}>
                <motion.div
                  className="card-surface overflow-hidden h-full flex flex-col"
                  whileHover={
                    reduce ? undefined : { y: -6, boxShadow: "0 18px 40px rgba(15,23,42,0.1)" }
                  }
                  transition={springSnappy}
                >
                  {item.image && (
                    <div className="relative h-40 sm:h-44 overflow-hidden">
                      <motion.div
                        className="absolute inset-0"
                        whileHover={reduce ? undefined : { scale: 1.05 }}
                        transition={{ duration: 0.5 }}
                      >
                        <SiteImage
                          image={item.image}
                          fill
                          className="object-cover"
                          sizes="(max-width: 640px) 100vw, 33vw"
                        />
                      </motion.div>
                    </div>
                  )}
                  <div className="p-5 flex flex-col flex-1">
                    {Icon ? (
                      <motion.div
                        className="w-9 h-9 rounded-xl bg-secondary/10 flex items-center justify-center mb-3"
                        whileHover={reduce ? undefined : { rotate: -8, scale: 1.08 }}
                        transition={springSnappy}
                      >
                        <Icon className="w-4 h-4 text-secondary" aria-hidden />
                      </motion.div>
                    ) : null}
                    <h3 className="text-base font-semibold text-primary tracking-tight">
                      {item.title}
                    </h3>
                    <p className="mt-1.5 text-sm text-muted leading-relaxed">{item.description}</p>
                  </div>
                </motion.div>
              </FadeIn>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
