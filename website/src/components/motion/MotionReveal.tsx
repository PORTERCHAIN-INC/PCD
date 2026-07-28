"use client";

import { motion, useReducedMotion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOutQuart, fadeUp, viewportOnce } from "@/lib/motion";

type Props = HTMLMotionProps<"div"> & {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  y?: number;
};

/** Scroll-reveal with reduced-motion fallback. */
export default function MotionReveal({ children, className, delay = 0, y = 28, ...rest }: Props) {
  const reduce = useReducedMotion();

  if (reduce) {
    return <div className={cn(className)}>{children}</div>;
  }

  return (
    <motion.div
      className={cn(className)}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      variants={{
        hidden: { opacity: 0, y },
        visible: { opacity: 1, y: 0 },
      }}
      transition={{ duration: 0.65, delay, ease: easeOutQuart }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

export function MotionStagger({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={cn(className)}>{children}</div>;

  return (
    <motion.div
      className={cn(className)}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      variants={{
        hidden: {},
        visible: {
          transition: { staggerChildren: 0.1, delayChildren: delay },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

export function MotionStaggerItem({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={cn(className)}>{children}</div>;

  return (
    <motion.div
      className={cn(className)}
      variants={fadeUp}
      transition={{ duration: 0.55, ease: easeOutQuart }}
    >
      {children}
    </motion.div>
  );
}
