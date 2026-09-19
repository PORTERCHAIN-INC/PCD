"use client";

import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export default function ShimmerButton({
  children,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode }) {
  return (
    <button
      type="button"
      className={cn(
        "shimmer-button relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-full bg-secondary px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-secondary/25 transition-colors hover:bg-[#1d4ed8] disabled:opacity-50",
        className
      )}
      {...props}
    >
      <span className="relative z-10">{children}</span>
      <span className="shimmer-button-glow absolute inset-0" aria-hidden />
    </button>
  );
}
