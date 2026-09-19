"use client";

import { cn } from "@/lib/utils";
import { useRef, type PointerEvent, type ReactNode } from "react";

export default function MagicCard({
  children,
  className,
  gradientSize = 280,
  clip = true,
}: {
  children: ReactNode;
  className?: string;
  gradientSize?: number;
  clip?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const node = ref.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    node.style.setProperty("--mouse-x", `${event.clientX - rect.left}px`);
    node.style.setProperty("--mouse-y", `${event.clientY - rect.top}px`);
  }

  return (
    <div
      ref={ref}
      onPointerMove={onPointerMove}
      className={cn(
        "group relative rounded-2xl border border-primary/10 bg-white shadow-sm",
        clip ? "overflow-hidden" : "overflow-visible",
        "transition-shadow duration-300 hover:shadow-[0_18px_40px_-16px_rgba(10,22,40,0.18)]",
        className
      )}
      style={{ "--magic-size": `${gradientSize}px` } as React.CSSProperties}
    >
      <div
        className="magic-card-spotlight pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        aria-hidden
      />
      <div className="relative z-10 min-w-0">{children}</div>
    </div>
  );
}
