"use client";

import type { Transition, Variants } from "framer-motion";

/** Shared easing — modern soft deceleration (avoid bounce noise). */
export const easeOutExpo: [number, number, number, number] = [0.16, 1, 0.3, 1];
export const easeOutQuart: [number, number, number, number] = [0.22, 1, 0.36, 1];

export const springSnappy: Transition = {
  type: "spring",
  stiffness: 380,
  damping: 28,
  mass: 0.8,
};

export const springSoft: Transition = {
  type: "spring",
  stiffness: 220,
  damping: 26,
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0 },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.94 },
  visible: { opacity: 1, scale: 1 },
};

export const slideFromLeft: Variants = {
  hidden: { opacity: 0, x: -36 },
  visible: { opacity: 1, x: 0 },
};

export const slideFromRight: Variants = {
  hidden: { opacity: 0, x: 36 },
  visible: { opacity: 1, x: 0 },
};

export const staggerContainer: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.09, delayChildren: 0.06 },
  },
};

export const staggerFast: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06, delayChildren: 0.04 },
  },
};

export const cardHover = {
  rest: { y: 0, scale: 1 },
  hover: { y: -4, scale: 1.01 },
};

export const viewportOnce = { once: true, margin: "-80px" as const, amount: 0.25 };
