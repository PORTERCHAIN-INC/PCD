"use client";

import { cn } from "@/lib/utils";

interface MarqueeProps {
  children: React.ReactNode;
  className?: string;
  reverse?: boolean;
  pauseOnHover?: boolean;
  speed?: "slow" | "normal" | "fast";
}

export default function Marquee({
  children,
  className,
  reverse = false,
  pauseOnHover = true,
  speed = "normal",
}: MarqueeProps) {
  const duration =
    speed === "slow"
      ? "var(--marquee-duration-slow)"
      : speed === "fast"
        ? "var(--marquee-duration-fast)"
        : "var(--marquee-duration)";

  return (
    <div
      className={cn(
        "group flex overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]",
        pauseOnHover && "[&:hover_.marquee-track]:animation-play-state-paused",
        className
      )}
    >
      <div
        className={cn("marquee-track flex min-w-full shrink-0 gap-4", reverse && "marquee-reverse")}
        style={{ animationDuration: duration }}
      >
        {children}
        {children}
      </div>
    </div>
  );
}
