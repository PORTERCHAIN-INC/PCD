"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import SiteImage from "@/components/ui/SiteImage";
import { TORONTO_GTA_SKYLINE } from "@/data/site-images";
import { cn } from "@/lib/utils";

type Stop = { id: string; label: string; x: number; y: number; active?: boolean };

/** Stylized GTA stops (viewBox 0 0 400 260 — Lake Ontario south). */
const GTA_STOPS: Stop[] = [
  { id: "toronto", label: "Toronto", x: 218, y: 118, active: true },
  { id: "mississauga", label: "Mississauga", x: 148, y: 132 },
  { id: "brampton", label: "Brampton", x: 108, y: 88 },
  { id: "vaughan", label: "Vaughan", x: 188, y: 72 },
  { id: "markham", label: "Markham", x: 268, y: 92 },
  { id: "scarborough", label: "Scarborough", x: 292, y: 128 },
];

const ROUTE_PATH = "M 108 88 L 148 132 L 188 72 L 218 118 L 268 92 L 292 128";

type Props = {
  caption: string;
  aiLabel: string;
  regionLabel: string;
  statsLabel: string;
  className?: string;
};

export default function GtaAiRouteVisual({
  caption,
  aiLabel,
  regionLabel,
  statsLabel,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "relative aspect-[16/10] sm:aspect-[5/3] lg:aspect-[4/3] overflow-hidden rounded-3xl",
        "bg-[#0a1628] shadow-premium ring-1 ring-primary/[0.06]",
        className
      )}
      role="img"
    >
      <div className="absolute inset-0 opacity-[0.22]">
        <SiteImage
          image={TORONTO_GTA_SKYLINE}
          fill
          className="object-cover object-[center_35%] scale-110"
          sizes="(max-width: 1024px) 100vw, 44vw"
        />
      </div>

      <div
        className="absolute inset-0 bg-gradient-to-br from-[#0a1628]/95 via-[#0f2847]/88 to-[#0a1628]/92"
        aria-hidden
      />

      <div className="absolute inset-0 grid-pattern opacity-[0.12]" aria-hidden />

      <div className="relative z-10 flex h-full flex-col p-4 sm:p-5 lg:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/90 backdrop-blur-sm">
            <Sparkles className="h-3 w-3 text-accent" aria-hidden />
            {aiLabel}
          </span>
          <span className="rounded-full border border-secondary/30 bg-secondary/15 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-secondary">
            {regionLabel}
          </span>
        </div>

        <div className="relative mt-3 flex-1 min-h-[140px] rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm overflow-hidden">
          <svg viewBox="0 0 400 260" className="absolute inset-0 h-full w-full" aria-hidden>
            <ellipse
              cx="220"
              cy="200"
              rx="170"
              ry="48"
              fill="none"
              stroke="rgba(96,165,250,0.15)"
              strokeWidth="1.5"
            />
            <path
              d={ROUTE_PATH}
              fill="none"
              stroke="url(#gtaRouteGradient)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="8 6"
              className="motion-safe:animate-[route-dash_2.4s_linear_infinite]"
            />
            <defs>
              <linearGradient id="gtaRouteGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#60a5fa" />
                <stop offset="50%" stopColor="#2563eb" />
                <stop offset="100%" stopColor="#38bdf8" />
              </linearGradient>
            </defs>
            {GTA_STOPS.map((stop, i) => (
              <g key={stop.id}>
                <motion.circle
                  cx={stop.x}
                  cy={stop.y}
                  r={stop.active ? 10 : 7}
                  fill={stop.active ? "#2563eb" : "#1e3a5f"}
                  stroke={stop.active ? "#93c5fd" : "#60a5fa"}
                  strokeWidth="2"
                  initial={{ opacity: 0, scale: 0.6 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.15 + i * 0.06, duration: 0.35 }}
                />
                <circle cx={stop.x} cy={stop.y} r="2.5" fill="#fff" />
              </g>
            ))}
          </svg>

          <div className="absolute bottom-3 left-3 right-3 flex flex-wrap gap-1.5">
            {GTA_STOPS.map((stop) => (
              <span
                key={stop.id}
                className={cn(
                  "rounded-md border px-2 py-1 text-[9px] font-medium backdrop-blur-sm",
                  stop.active
                    ? "border-secondary/40 bg-secondary/20 text-white"
                    : "border-white/10 bg-white/5 text-white/70"
                )}
              >
                {stop.label}
              </span>
            ))}
          </div>
        </div>

        <p className="mt-3 text-xs sm:text-sm font-medium text-white/75">{statsLabel}</p>
      </div>

      <span className="absolute bottom-4 left-4 z-20 inline-flex items-center gap-2 rounded-full border border-white/20 bg-primary/80 px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-white backdrop-blur-md">
        {caption}
      </span>
    </div>
  );
}
