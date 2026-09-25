"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOutQuart, fadeUp, staggerFast } from "@/lib/motion";

export type HubTimelineStep = {
  id: string;
  label: string;
  detail: string;
};

type Props = {
  steps: HubTimelineStep[];
  className?: string;
};

export default function HubTimeline({ steps, className }: Props) {
  const reduce = useReducedMotion();

  return (
    <motion.ol
      className={cn("space-y-0", className)}
      initial={reduce ? false : "hidden"}
      whileInView="visible"
      viewport={{ once: true, margin: "-40px" }}
      variants={staggerFast}
    >
      {steps.map((step, i) => (
        <motion.li
          key={step.id}
          variants={fadeUp}
          transition={{ duration: 0.5, ease: easeOutQuart }}
          className="relative flex gap-4 pb-6 last:pb-0"
        >
          <div className="flex flex-col items-center">
            <motion.span
              className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-bold text-white"
              whileInView={reduce ? undefined : { scale: [0.7, 1.12, 1] }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.08 }}
            >
              {i + 1}
            </motion.span>
            {i < steps.length - 1 ? (
              <motion.span
                className="mt-1 w-px flex-1 origin-top bg-primary/10"
                initial={reduce ? false : { scaleY: 0 }}
                whileInView={{ scaleY: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.1 + i * 0.08, ease: easeOutQuart }}
                aria-hidden
              />
            ) : null}
          </div>
          <div className="min-w-0 pt-1">
            <p className="text-sm font-semibold text-primary">{step.label}</p>
            <p className="mt-0.5 text-xs text-muted">{step.detail}</p>
          </div>
        </motion.li>
      ))}
    </motion.ol>
  );
}
