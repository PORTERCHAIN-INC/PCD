"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface MagicCardProps {
  children: React.ReactNode;
  className?: string;
  gradientSize?: number;
}

export default function MagicCard({ children, className, gradientSize = 280 }: MagicCardProps) {
  return (
    <motion.div
      whileHover={{ y: -3 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-primary/8 bg-white shadow-premium",
        "transition-shadow duration-300 hover:shadow-[0_20px_50px_-12px_rgba(10,22,40,0.15)]",
        className
      )}
      style={{ "--magic-size": `${gradientSize}px` } as React.CSSProperties}
    >
      <div
        className="magic-card-spotlight pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        aria-hidden
      />
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
