"use client";

import { cn } from "@/lib/utils";

interface AnimatedGradientTextProps {
  children: React.ReactNode;
  className?: string;
}

export default function AnimatedGradientText({ children, className }: AnimatedGradientTextProps) {
  return (
    <span
      className={cn(
        "inline bg-gradient-to-r from-secondary via-accent to-secondary bg-[length:200%_auto] bg-clip-text text-transparent animate-gradient-text",
        className
      )}
    >
      {children}
    </span>
  );
}
