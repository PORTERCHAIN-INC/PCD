"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

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
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5 }}
      className={cn(
        "mb-8 sm:mb-10 md:mb-12 lg:mb-14",
        align === "center" && "text-center mx-auto max-w-3xl",
        className
      )}
    >
      {label && (
        <span className="inline-block type-caption font-bold text-secondary mb-3">{label}</span>
      )}
      <h2 className={cn("type-h2 text-balance", dark ? "text-white" : "text-primary")}>{title}</h2>
      {subtitle && (
        <p
          className={cn(
            "mt-4 type-lead max-w-2xl",
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
