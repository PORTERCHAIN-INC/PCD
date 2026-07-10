"use client";

import { motion } from "framer-motion";
import Container from "@/components/ui/Container";
import { cn } from "@/lib/utils";

interface StorySectionProps {
  id?: string;
  label?: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
  dark?: boolean;
  tight?: boolean;
  /** Fleet block: center in one viewport with minimal padding */
  fitViewport?: boolean;
}

export default function StorySection({
  id,
  label,
  title,
  subtitle,
  children,
  className,
  dark = false,
  tight = false,
  fitViewport = false,
}: StorySectionProps) {
  return (
    <section
      id={id}
      className={cn(
        fitViewport ? "pc-section-fleet" : tight ? "pc-section-tight" : "pc-section",
        dark ? "bg-primary text-white" : "bg-white",
        className
      )}
    >
      <Container className={cn(fitViewport && "pc-section-fleet__inner h-full")}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className={cn(fitViewport ? "max-w-none" : "max-w-3xl")}
        >
          {label && <p className={cn("pc-eyebrow", dark && "text-accent")}>{label}</p>}
          <h2
            className={cn(
              fitViewport ? "pc-headline text-xl sm:text-2xl lg:text-[1.75rem]" : "pc-headline",
              "mt-2 sm:mt-3 text-balance",
              dark ? "text-white" : "text-primary"
            )}
          >
            {title}
          </h2>
          {subtitle && (
            <p
              className={cn(
                "mt-2 sm:mt-3 text-sm sm:text-base leading-relaxed max-w-2xl",
                dark ? "text-white/65" : "text-muted"
              )}
            >
              {subtitle}
            </p>
          )}
        </motion.div>
        <div className={cn(fitViewport ? "mt-3 sm:mt-4 min-h-0" : "mt-8 sm:mt-10 lg:mt-12")}>
          {children}
        </div>
      </Container>
    </section>
  );
}
