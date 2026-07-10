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
}: StorySectionProps) {
  return (
    <section
      id={id}
      className={cn(
        tight ? "pc-section-tight" : "pc-section",
        dark ? "bg-primary text-white" : "bg-white",
        className
      )}
    >
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="max-w-3xl"
        >
          {label && <p className={cn("pc-eyebrow", dark && "text-accent")}>{label}</p>}
          <h2 className={cn("pc-headline mt-3 text-balance", dark ? "text-white" : "text-primary")}>
            {title}
          </h2>
          {subtitle && (
            <p
              className={cn(
                "mt-3 sm:mt-4 text-base sm:text-lg leading-relaxed max-w-2xl",
                dark ? "text-white/65" : "text-muted"
              )}
            >
              {subtitle}
            </p>
          )}
        </motion.div>
        <div className="mt-8 sm:mt-10 lg:mt-12">{children}</div>
      </Container>
    </section>
  );
}
