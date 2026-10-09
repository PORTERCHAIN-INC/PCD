"use client";

import { cn } from "@/lib/utils";
import { type ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
}

const VARIANTS = {
  primary: "bg-secondary text-white hover:bg-[#1a47bf] shadow-md",
  secondary: "bg-primary text-white hover:bg-[#152238]",
  outline: "border-2 border-primary/20 text-primary hover:bg-gray-bg",
  ghost: "text-primary hover:bg-gray-bg",
} as const;
const SIZES = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-5 py-2.5 text-sm font-medium",
  lg: "px-6 py-3 text-base font-medium",
} as const;

/** Button styling for links (avoids nesting a <button> inside an <a>). */
export function buttonClasses(
  variant: NonNullable<ButtonProps["variant"]> = "primary",
  size: NonNullable<ButtonProps["size"]> = "md",
  className?: string
) {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-xl transition-all disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
    className
  );
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, ...props }, ref) => {
    return (
      <button ref={ref} className={buttonClasses(variant, size, className)} {...props}>
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
export default Button;
