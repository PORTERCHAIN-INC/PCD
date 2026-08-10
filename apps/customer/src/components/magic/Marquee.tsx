"use client";

import { cn } from "@/lib/utils";

type Props = {
  children: React.ReactNode;
  className?: string;
  reverse?: boolean;
  pauseOnHover?: boolean;
};

export default function Marquee({
  children,
  className,
  reverse = false,
  pauseOnHover = true,
}: Props) {
  return (
    <div
      className={cn(
        "group flex overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]",
        pauseOnHover && "[&:hover_.customer-marquee-track]:[animation-play-state:paused]",
        className
      )}
    >
      <div
        className={cn(
          "customer-marquee-track flex min-w-full shrink-0 gap-3",
          reverse && "customer-marquee-reverse"
        )}
      >
        {children}
        {children}
      </div>
    </div>
  );
}
