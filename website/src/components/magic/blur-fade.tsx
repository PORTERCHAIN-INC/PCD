"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOutQuart } from "@/lib/motion";

interface BlurFadeProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  duration?: number;
  yOffset?: number;
  inView?: boolean;
}

export default function BlurFade({
  children,
  className,
  delay = 0,
  duration = 0.5,
  yOffset = 14,
  inView = false,
}: BlurFadeProps) {
  const reduce = useReducedMotion();

  if (reduce) {
    return <div className={cn(className)}>{children}</div>;
  }

  if (inView) {
    return (
      <motion.div
        initial={{ opacity: 0, y: yOffset, filter: "blur(8px)" }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, margin: "-40px" }}
        transition={{ duration, delay, ease: easeOutQuart }}
        className={cn(className)}
      >
        {children}
      </motion.div>
    );
  }

  const variants: Variants = {
    hidden: { opacity: 0, y: yOffset, filter: "blur(8px)" },
    visible: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: { duration, delay, ease: easeOutQuart },
    },
  };

  return (
    <motion.div variants={variants} initial="hidden" animate="visible" className={cn(className)}>
      {children}
    </motion.div>
  );
}
