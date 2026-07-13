"use client";

import { motion, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";

interface BlurFadeProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  duration?: number;
  yOffset?: number;
  inView?: boolean;
}

const variants: Variants = {
  hidden: { opacity: 0, y: 12, filter: "blur(6px)" },
  visible: { opacity: 1, y: 0, filter: "blur(0px)" },
};

export default function BlurFade({
  children,
  className,
  delay = 0,
  duration = 0.45,
  yOffset = 12,
  inView = false,
}: BlurFadeProps) {
  if (inView) {
    return (
      <motion.div
        initial={{ opacity: 0, y: yOffset, filter: "blur(6px)" }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, margin: "-40px" }}
        transition={{ duration, delay, ease: [0.21, 0.47, 0.32, 0.98] }}
        className={cn(className)}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={{
        hidden: { ...variants.hidden, y: yOffset },
        visible: {
          ...variants.visible,
          transition: { duration, delay, ease: [0.21, 0.47, 0.32, 0.98] },
        },
      }}
      initial="hidden"
      animate="visible"
      className={cn(className)}
    >
      {children}
    </motion.div>
  );
}
