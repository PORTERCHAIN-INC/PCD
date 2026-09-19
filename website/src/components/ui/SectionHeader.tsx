"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOutExpo } from "@/lib/motion";

interface SectionHeaderProps {
  label?: string;
  title: string;
  subtitle?: string;
  align?: "left" | "center";
  dark?: boolean;
  className?: string;
}

export default function SectionHeader({
  label,
  title,
  subtitle,
  align = "center",
  dark = false,
  className,
}: SectionHeaderProps) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 24, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: reduce ? 0.2 : 0.65, ease: easeOutExpo }}
      className={cn(
        "mb-6 sm:mb-8 md:mb-9",
        align === "center" && "text-center mx-auto max-w-3xl",
        className
      )}
    >
      {label && (
        <span className="inline-block type-caption font-bold text-secondary mb-2">{label}</span>
      )}
      <h2 className={cn("type-h2 text-balance", dark ? "text-white" : "text-primary")}>{title}</h2>
      {subtitle && (
        <p
          className={cn(
            "mt-3 type-lead max-w-2xl",
            align === "center" && "mx-auto",
            dark ? "text-white/70" : "text-muted"
          )}
        >
          {subtitle}
        </p>
      )}
    </motion.div>
  );
}
