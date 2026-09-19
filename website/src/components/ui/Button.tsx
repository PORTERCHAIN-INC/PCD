"use client";

import { cn } from "@/lib/utils";
import { type ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  shape?: "rounded" | "pill";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", shape = "rounded", children, ...props }, ref) => {
    const variants = {
      primary:
        "bg-secondary text-white hover:bg-[#1d4ed8] shadow-lg shadow-secondary/25 hover:shadow-secondary/40 hover:scale-[1.02] active:scale-[0.98]",
      secondary: "bg-primary text-white hover:bg-[#152238] shadow-lg shadow-primary/20",
      outline: "border-2 border-white/30 text-white hover:bg-white/10 backdrop-blur-sm",
      ghost: "text-primary hover:bg-gray-bg",
    };

    const sizes = {
      sm: "px-4 py-2 type-button text-sm",
      md: "px-6 py-3 type-button",
      lg: "px-8 py-4 type-button text-base",
    };

    const shapes = {
      rounded: "rounded-2xl",
      pill: "rounded-full",
    };

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed",
          variants[variant],
          sizes[size],
          shapes[shape],
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
export default Button;
