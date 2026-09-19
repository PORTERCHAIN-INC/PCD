"use client";

import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";
import { track, ANALYTICS_EVENTS } from "@/lib/seo/analytics";

interface ShimmerButtonProps {
  href: string;
  children: React.ReactNode;
  className?: string;
  showArrow?: boolean;
  trackSource?: string;
  variant?: "primary" | "onDark";
}

export default function ShimmerButton({
  href,
  children,
  className,
  showArrow = false,
  trackSource,
  variant = "primary",
}: ShimmerButtonProps) {
  const base =
    variant === "onDark"
      ? "bg-white text-primary hover:bg-white/95"
      : "bg-secondary text-white hover:bg-[#1d4ed8]";

  return (
    <Link
      href={href}
      className={cn(
        "shimmer-button relative inline-flex min-h-[var(--touch-min)] items-center justify-center gap-2 overflow-hidden rounded-full px-6 py-3 sm:px-8 sm:py-3.5 text-sm sm:text-base font-semibold shadow-lg transition-all duration-300",
        variant === "onDark" ? "shadow-white/10" : "shadow-secondary/25 hover:shadow-secondary/40",
        base,
        className
      )}
      onClick={() => {
        track(ANALYTICS_EVENTS.CTA_CLICK, {
          cta_label: typeof children === "string" ? children : undefined,
          cta_source: trackSource,
          href,
        });
      }}
    >
      <span className="relative z-10 flex items-center gap-2">
        {children}
        {showArrow && <ArrowRight className="h-4 w-4" />}
      </span>
      <span className="shimmer-button-glow absolute inset-0" aria-hidden />
    </Link>
  );
}
