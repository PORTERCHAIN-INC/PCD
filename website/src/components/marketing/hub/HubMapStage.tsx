"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOutQuart, springSnappy, staggerFast, fadeUp } from "@/lib/motion";

type Props = {
  title: string;
  subtitle?: string;
  className?: string;
  children?: React.ReactNode;
};

export default function HubMapStage({ title, subtitle, className, children }: Props) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-primary/8 bg-white shadow-sm",
        className
      )}
      initial={reduce ? false : { opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.65, ease: easeOutQuart }}
    >
      <div
        className="absolute inset-0 bg-gradient-to-br from-[#E8EEF9] via-white to-[#F8FAFC]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-50"
        aria-hidden
        style={{
          backgroundImage:
            "linear-gradient(90deg, rgba(37,99,235,0.08) 1px, transparent 1px), linear-gradient(rgba(37,99,235,0.08) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
      {!reduce ? (
        <motion.div
          className="pointer-events-none absolute left-[12%] top-[42%] h-2 w-2 rounded-full bg-secondary"
          animate={{ scale: [1, 1.8, 1], opacity: [0.9, 0.35, 0.9] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          aria-hidden
        />
      ) : null}
      <div className="relative z-10 flex min-h-[220px] flex-col justify-between p-5 sm:min-h-[280px] sm:p-7">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-secondary">{title}</p>
          {subtitle ? <p className="mt-1 max-w-md text-sm text-muted">{subtitle}</p> : null}
        </div>
        {children}
        <motion.div
          className="mt-6 h-24 origin-left rounded-xl bg-gradient-to-r from-secondary/20 via-secondary/40 to-accent/20"
          initial={reduce ? false : { scaleX: 0.4, opacity: 0.5 }}
          whileInView={{ scaleX: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ ...springSnappy, delay: 0.15 }}
        />
      </div>
    </motion.div>
  );
}
