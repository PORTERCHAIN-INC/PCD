"use client";

import { cn } from "@/lib/utils";

interface BorderBeamProps {
  className?: string;
  size?: number;
  duration?: number;
  colorFrom?: string;
  colorTo?: string;
}

export default function BorderBeam({
  className,
  size = 200,
  duration = 12,
  colorFrom = "#2563eb",
  colorTo = "#38bdf8",
}: BorderBeamProps) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 rounded-[inherit] overflow-hidden",
        className
      )}
      aria-hidden
    >
      <div
        className="absolute inset-0 rounded-[inherit] border-beam-spin opacity-80"
        style={
          {
            "--beam-size": `${size}px`,
            "--beam-duration": `${duration}s`,
            "--beam-from": colorFrom,
            "--beam-to": colorTo,
          } as React.CSSProperties
        }
      />
    </div>
  );
}
