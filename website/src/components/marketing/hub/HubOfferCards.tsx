"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOutQuart, fadeUp, springSnappy, staggerFast } from "@/lib/motion";

export type HubOfferCard = {
  id: string;
  title: string;
  badge: string;
  meta: string;
  ctaLabel?: string;
};

type Props = {
  items: HubOfferCard[];
  className?: string;
  illustrativeNote?: string;
};

export default function HubOfferCards({ items, className, illustrativeNote }: Props) {
  const reduce = useReducedMotion();

  return (
    <div className={cn("space-y-3", className)}>
      {illustrativeNote ? <p className="text-xs text-muted">{illustrativeNote}</p> : null}
      <motion.ul
        className="space-y-3"
        initial={reduce ? false : "hidden"}
        whileInView="visible"
        viewport={{ once: true, margin: "-40px" }}
        variants={staggerFast}
      >
        {items.map((item) => (
          <motion.li
            key={item.id}
            variants={fadeUp}
            transition={{ duration: 0.5, ease: easeOutQuart }}
            whileHover={
              reduce ? undefined : { y: -3, boxShadow: "0 12px 32px rgba(15,23,42,0.08)" }
            }
            className="rounded-2xl border border-primary/8 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-primary">{item.title}</p>
                <p className="mt-1 text-xs text-muted">{item.meta}</p>
              </div>
              <motion.span
                className="shrink-0 rounded-lg bg-secondary/10 px-2 py-1 text-[11px] font-semibold text-secondary"
                whileHover={reduce ? undefined : { scale: 1.05 }}
                transition={springSnappy}
              >
                {item.badge}
              </motion.span>
            </div>
            {item.ctaLabel ? (
              <p className="mt-3 text-xs font-medium text-secondary">{item.ctaLabel}</p>
            ) : null}
          </motion.li>
        ))}
      </motion.ul>
    </div>
  );
}
