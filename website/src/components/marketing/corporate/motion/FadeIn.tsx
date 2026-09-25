"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";
import { easeOutExpo } from "@/lib/motion";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28, filter: "blur(8px)" },
  visible: { opacity: 1, y: 0, filter: "blur(0px)" },
};

const fadeUpReduced: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

interface FadeInProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  duration?: number;
  as?: "div" | "section" | "article" | "li";
}

/** Sitewide scroll reveal — used across corporate/footer pages. */
export default function FadeIn({
  children,
  className,
  delay = 0,
  duration = 0.6,
  as = "div",
}: FadeInProps) {
  const reduce = useReducedMotion();
  const Tag = motion[as];

  return (
    <Tag
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-70px", amount: 0.2 }}
      variants={reduce ? fadeUpReduced : fadeUp}
      transition={{
        duration: reduce ? 0.2 : duration,
        delay: reduce ? 0 : delay,
        ease: reduce ? "linear" : easeOutExpo,
      }}
      className={cn(className)}
    >
      {children}
    </Tag>
  );
}
